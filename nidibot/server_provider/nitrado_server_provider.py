#!/usr/bin/env python

import glob
import json
import logging
import os
import pathlib
import shutil
import subprocess
import tempfile
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List

import ftputil  # type: ignore
import requests  # type: ignore

from nidibot.bots.bot_base import BackupDescription
from nidibot.server_provider.game_server import GameServer
from nidibot.server_provider.server_provider_base import (
    ServerProviderBase,
    ServerProviderConfiguration,
    ServerStatus,
)


@dataclass
class NitradoService:
    id: str = ""
    short_name: str = ""
    available_until: str = ""


@dataclass
class NitradoFtpConfiguration:
    hostname: str = ""
    port: int = 21
    username: str = ""
    password: str = ""


@dataclass
class NitradoMysqlConfiguration:
    hostname: str = ""
    port: int = 21
    username: str = ""
    password: str = ""
    database: str = ""


@dataclass
class NitradoServerInformation:
    id: str = ""
    short_name: str = ""
    status: ServerStatus = field(default_factory=ServerStatus)
    ftp: NitradoFtpConfiguration = field(default_factory=NitradoFtpConfiguration)
    mysql: NitradoMysqlConfiguration = field(default_factory=NitradoMysqlConfiguration)


class NitradoServerProvider(ServerProviderBase):
    def __init__(
        self,
        configuration: ServerProviderConfiguration,
        backup_directory: str,
        notify_callback,
    ):
        super().__init__(
            configuration=configuration,
            backup_directory=backup_directory,
            notify_callback=notify_callback,
        )
        self.__servers: Dict[str, NitradoServerInformation] = {}

        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s:%(levelname)s:%(funcName)s %(message)s",
            handlers=[logging.StreamHandler()],
        )

        self.__verify_api_version()

        self.__data_received_event = threading.Event()
        self.__stopping_event = threading.Event()

        self.__polling_thread = threading.Thread(target=self._poll)
        self.__polling_thread.daemon = True
        self.__polling_thread.start()

        self.__data_received_event.wait()

    def __verify_api_version(self) -> None:
        response = requests.get(
            "https://api.nitrado.net/version",
            timeout=self._configuration.timeout_seconds,
        )

        logging.debug(
            "Response received, status code: %d, content: %s.",
            response.status_code,
            response.content.decode("utf-8"),
        )

        content_json = json.loads(response.content.decode("utf-8"))

        if response.status_code != 200:
            raise ValueError("Failed reading Nitrado API version!")

        if content_json["status"] != "success":
            raise ValueError("Failed reading Nitrado API version!")

        # Warning: Nitrado always changes last part of provided API version.
        expected_api_version = "nitrapi-1471"
        if expected_api_version not in content_json["message"]:
            logging.warning(
                "Nitrado API version was changed! Expected: %s, actual: %s.",
                expected_api_version,
                content_json["message"],
            )

    def __download_ftp_folder(
        self, ftp_server, local_path: str, remote_path: str, ignore_folders: list
    ):
        for root_path, folders, files in ftp_server.walk(top=remote_path, topdown=True):
            root_folder_name = os.path.basename(root_path)
            if root_folder_name in ignore_folders:
                return

            for filename in files:
                remote_filepath = ftp_server.path.join(root_path, filename)
                local_filepath = os.path.join(local_path, remote_filepath)
                local_parent_folder = pathlib.Path(local_filepath).parent.absolute()
                pathlib.Path(local_parent_folder).mkdir(parents=True, exist_ok=True)
                ftp_server.download(remote_filepath, local_filepath)
                logging.debug(
                    "Downloaded '%s' to '%s'.", remote_filepath, local_filepath
                )

            for folder_name in folders:
                self.__download_ftp_folder(
                    ftp_server=ftp_server,
                    local_path=local_path,
                    remote_path=os.path.join(root_path, folder_name),
                    ignore_folders=ignore_folders,
                )

            return

    def __upload_ftp_folder(
        self, ftp_server, local_path: str, remote_path: str, ignore_folders: list
    ):
        for root_path, folders, files in os.walk(top=local_path, topdown=True):
            root_folder_name = os.path.basename(root_path)
            if root_folder_name in ignore_folders:
                return

            for filename in files:
                local_filepath = os.path.join(root_path, filename)
                remote_filepath = ftp_server.path.join(remote_path, filename)

                if remote_path != ".":
                    ftp_server.makedirs(remote_path, exist_ok=True)

                ftp_server.upload(local_filepath, remote_filepath)
                logging.debug("Uploaded '%s' to '%s'.", local_filepath, remote_filepath)

            for folder_name in folders:
                self.__upload_ftp_folder(
                    ftp_server=ftp_server,
                    local_path=os.path.join(root_path, folder_name),
                    remote_path=os.path.join(remote_path, folder_name),
                    ignore_folders=ignore_folders,
                )

            return

    def __get_services(self) -> list:
        service_list = []

        try:
            headers = {"Authorization": self._configuration.token}
            response = requests.get(
                "https://api.nitrado.net/services",
                timeout=self._configuration.timeout_seconds,
                headers=headers,
            )

            logging.debug(
                "Response received, status code: %d.",
                response.status_code,
            )

            content_json = json.loads(response.content.decode("utf-8"))
            data_service_list = content_json["data"]["services"]
            for data_service in data_service_list:
                service: NitradoService = NitradoService()

                service.id = data_service["id"]
                service.short_name = data_service["details"]["folder_short"]
                service.available_until = str(data_service["suspend_date"]).replace(
                    "T", " "
                )

                service_list.append(service)

        except Exception as exception:
            logging.exception(exception)

        return service_list

    def _poll(self) -> None:
        logging.debug("Polling thread started.")

        while not self.__stopping_event.is_set():
            servers: Dict[str, NitradoServerInformation] = {}
            services = self.__get_services()
            for service in services:
                try:
                    headers = {"Authorization": self._configuration.token}
                    response = requests.get(
                        f"https://api.nitrado.net/services/{service.id}/gameservers",
                        timeout=self._configuration.timeout_seconds,
                        headers=headers,
                    )

                    logging.debug(
                        "Response received, status code: %d.",
                        response.status_code,
                    )

                    content_json = json.loads(response.content.decode("utf-8"))
                    gameserver_dict = content_json["data"]["gameserver"]
                    query_dict = gameserver_dict["query"]

                    server: NitradoServerInformation = NitradoServerInformation()
                    server.id = str(service.id)
                    server.short_name = service.short_name
                    server.status.game_name = gameserver_dict["game_human"]
                    server.status.update_available = (
                        gameserver_dict["game_specific"]["update_status"]
                        != "up_to_date"
                    )
                    server.status.available_until = service.available_until

                    if gameserver_dict["status"] == "started":
                        server.status.status = "online"
                    elif gameserver_dict["status"] == "stopped":
                        server.status.status = "offline"
                    else:
                        server.status.status = str(gameserver_dict["status"])

                    if len(query_dict) > 0:
                        server.status.version = gameserver_dict["query"]["version"]
                        server.status.address = gameserver_dict["query"]["connect_ip"]
                        server.status.players_limit = int(
                            gameserver_dict["query"]["player_max"]
                        )
                        server.status.players_connected = int(
                            gameserver_dict["query"]["player_current"]
                        )
                        server.status.player_names = gameserver_dict["query"]["players"]
                    else:
                        server.status.address = (
                            str(gameserver_dict["ip"])
                            + ":"
                            + str(gameserver_dict["query_port"])
                        )
                        server.status.players_limit = int(gameserver_dict["slots"])
                        server.status.player_names = []

                    ftp_dict = content_json["data"]["gameserver"]["credentials"]["ftp"]

                    server.ftp.hostname = ftp_dict["hostname"]
                    server.ftp.port = int(ftp_dict["port"])
                    server.ftp.username = ftp_dict["username"]
                    server.ftp.password = ftp_dict["password"]

                    mysql_dict = content_json["data"]["gameserver"]["credentials"][
                        "mysql"
                    ]

                    server.mysql.hostname = mysql_dict["hostname"]
                    server.mysql.port = int(mysql_dict["port"])
                    server.mysql.username = mysql_dict["username"]
                    server.mysql.password = mysql_dict["password"]
                    server.mysql.database = mysql_dict["database"]

                    servers[server.id] = server

                except Exception as exception:
                    logging.exception(exception)

            #
            # Check for changes in status and notify.
            #
            if len(self.__servers) > 0:
                for server_id, server in servers.items():
                    title = f"{server.status.game_name}"
                    if server.status.version:
                        title += f" ({server.status.version})"

                    title += f" - {server.status.address}"

                    if (
                        self._configuration.notifications.on_new_server
                        and server_id not in self.__servers
                    ):
                        self._notify_callback(
                            title, "New game server appeared, please configure it."
                        )

                    if (
                        self._configuration.notifications.on_status_change
                        and server.status.status
                        != self.__servers[server_id].status.status
                    ):
                        self._notify_callback(
                            title,
                            f"Status changed from '{self.__servers[server_id].status.status}' to "
                            f"'{server.status.status}'.",
                        )

                    if (
                        self._configuration.notifications.on_address_change
                        and server.status.address
                        != self.__servers[server_id].status.address
                    ):
                        self._notify_callback(
                            title,
                            f"Address from '{self.__servers[server_id].status.address}' to "
                            f"'{server.status.address}'.",
                        )

                    if (
                        self._configuration.notifications.on_version_change
                        and server.status.version
                        != self.__servers[server_id].status.version
                    ):
                        self._notify_callback(
                            title,
                            f"Version from '{self.__servers[server_id].status.version}' to "
                            f"'{server.status.version}'.",
                        )

                    if (
                        self._configuration.notifications.on_update_available_change
                        and server.status.update_available
                        != self.__servers[server_id].status.update_available
                    ):
                        self._notify_callback(
                            title,
                            "Update is available, please restart server.",
                        )

            self.__servers = servers

            self.__data_received_event.set()
            self.__stopping_event.wait(self._configuration.polling_seconds)

    def name(self) -> str:
        return "Nitrado"

    def get_servers(self) -> List[GameServer]:
        servers: List[GameServer] = []

        for key, value in self.__servers.items():
            name = f"{value.short_name}-{value.status.address}"
            servers.append(
                GameServer(server_provider=self, server_id=key, server_name=name)
            )

        return servers

    def status(self, server_id: str = "") -> ServerStatus:
        return self.__servers[server_id].status

    def start(self, server_id: str = "") -> bool:
        return self.restart(server_id)

    def stop(self, server_id: str = "") -> bool:
        try:
            headers = {"Authorization": self._configuration.token}
            response = requests.post(
                f"https://api.nitrado.net/services/{server_id}/gameservers/stop",
                timeout=self._configuration.timeout_seconds,
                headers=headers,
            )

            logging.debug(
                "Response received, status code: %d, content: %s.",
                response.status_code,
                response.content.decode("utf-8"),
            )

            content_json = json.loads(response.content.decode("utf-8"))

            return response.status_code == 200 and content_json["status"] == "success"

        except Exception as exception:
            logging.exception(exception)
            return False

    def restart(self, server_id: str = "") -> bool:
        try:
            headers = {"Authorization": self._configuration.token}
            response = requests.post(
                f"https://api.nitrado.net/services/{server_id}/gameservers/restart",
                timeout=self._configuration.timeout_seconds,
                headers=headers,
            )

            logging.debug(
                "Response received, status code: %d, content: %s.",
                response.status_code,
                response.content.decode("utf-8"),
            )

            content_json = json.loads(response.content.decode("utf-8"))

            return response.status_code == 200 and content_json["status"] == "success"

        except Exception as exception:
            logging.exception(exception)
            return False

    def create_backup(self, server_id: str = "") -> bool:
        try:
            start_time = time.time()
            with tempfile.TemporaryDirectory() as temp_folder_path:
                datetime_str = datetime.now().strftime("%Y%m%d_%H%M%S")
                local_path = os.path.join(temp_folder_path, datetime_str)
                pathlib.Path(local_path).mkdir(parents=True, exist_ok=True)

                #
                # Copy game server files via FTP to temporary folder.
                #
                files_path = os.path.join(local_path, "files")
                with ftputil.FTPHost(
                    self.__servers[server_id].ftp.hostname,
                    self.__servers[server_id].ftp.username,
                    self.__servers[server_id].ftp.password,
                ) as ftp:
                    self.__download_ftp_folder(
                        ftp_server=ftp,
                        local_path=files_path,
                        remote_path=".",
                        ignore_folders=["Crashes", "CrashReportClient"],
                    )

                #
                # Save MySQL database to temporary folder.
                #
                mysqldump_path = shutil.which("mysqldump")
                if mysqldump_path is not None:
                    database_name = self.__servers[server_id].mysql.database
                    mysql_folder_path = os.path.join(local_path, "mysql")
                    pathlib.Path(mysql_folder_path).mkdir(parents=True, exist_ok=True)
                    database_filepath = os.path.join(
                        mysql_folder_path, database_name + ".sql"
                    )

                    mysqldump_command = (
                        f"{mysqldump_path} --host {self.__servers[server_id].mysql.hostname} "
                        f"--port {str(self.__servers[server_id].mysql.port)} "
                        f"--user {self.__servers[server_id].mysql.username} "
                        f"-p{self.__servers[server_id].mysql.password} "
                        f"{database_name} > {database_filepath}"
                    )

                    # logging.debug("Executing: '%s'.", mysql_command)

                    with subprocess.Popen(
                        mysqldump_command,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        shell=True,
                        encoding="utf-8",
                        universal_newlines=True,
                        cwd=local_path,
                    ) as process:
                        for stdout_line in iter(process.stdout.readline, ""):  # type: ignore
                            logging.info(stdout_line.replace("\n", ""))
                        process.stdout.close()  # type: ignore
                        _ = process.wait()

                else:
                    logging.warning(
                        "No mysqldump is available in the system, please install it."
                    )

                #
                # Create ZIP archive.
                #
                backup_directory = self._get_backup_directory_path(
                    game_name=self.__servers[server_id].short_name, server_id=server_id
                )
                pathlib.Path(backup_directory).mkdir(parents=True, exist_ok=True)

                shutil.make_archive(
                    os.path.join(backup_directory, datetime_str), "zip", local_path
                )

                logging.debug(
                    "Created backup archive at path: '%s'.",
                    os.path.join(backup_directory, datetime_str),
                )

            end_time = time.time()
            logging.debug("Backup creation took %s.", end_time - start_time)

        except Exception as exception:
            logging.exception(exception)
            return False

        return True

    def restore_backup(self, server_id: str = "", filepath: str = "") -> bool:
        status = self.status(server_id=server_id)
        if status.status != "offline":
            if not self.stop(server_id=server_id):
                return False

        if not self._wait_for_status(
            server_id=server_id, required_status="offline", timeout_seconds=60
        ):
            return False

        start_time = time.time()
        with tempfile.TemporaryDirectory() as temp_folder_path:
            shutil.unpack_archive(filepath, temp_folder_path)

            #
            # Copy game server files via FTP to temporary folder.
            #
            files_path = os.path.join(temp_folder_path, "files")
            with ftputil.FTPHost(
                self.__servers[server_id].ftp.hostname,
                self.__servers[server_id].ftp.username,
                self.__servers[server_id].ftp.password,
            ) as ftp:
                self.__upload_ftp_folder(
                    ftp_server=ftp,
                    local_path=files_path,
                    remote_path=".",
                    ignore_folders=["Crashes", "CrashReportClient"],
                )

            #
            # Save MySQL database to temporary folder.
            #
            mysql_path = shutil.which("mysql")
            if mysql_path is not None:
                database_name = self.__servers[server_id].mysql.database
                database_filepath = os.path.join(
                    temp_folder_path, "mysql", database_name + ".sql"
                )

                if os.path.exists(database_filepath):
                    mysql_command = (
                        f"{mysql_path} --host={self.__servers[server_id].mysql.hostname} "
                        f"--port={str(self.__servers[server_id].mysql.port)} "
                        f"--user={self.__servers[server_id].mysql.username} "
                        f"--password={self.__servers[server_id].mysql.password} "
                        f"{database_name} < {database_filepath}"
                    )

                    # logging.debug("Executing: '%s'.", mysql_command)

                    with subprocess.Popen(
                        args=mysql_command,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        shell=True,
                        encoding="utf-8",
                        universal_newlines=True,
                        cwd=temp_folder_path,
                    ) as process:
                        for stdout_line in iter(process.stdout.readline, ""):  # type: ignore
                            logging.info(stdout_line.replace("\n", ""))
                        process.stdout.close()  # type: ignore
                        _ = process.wait()
                else:
                    logging.warning("No MySQL database file found, nothing to restore!")

            else:
                logging.warning(
                    "No mysql is available in the system, please install it."
                )

        # Start server back if it was online before restore.
        if status.status != "offline":
            self.start(server_id=server_id)

        end_time = time.time()
        logging.debug("Backup restoring took %s.", end_time - start_time)

        return True

    def list_backups(self, server_id: str = "") -> list:
        backup_directory = self._get_backup_directory_path(
            game_name=self.__servers[server_id].short_name, server_id=server_id
        )

        wildcard_path = os.path.join(backup_directory, "*")
        file_list = glob.glob(wildcard_path)

        backups: List[BackupDescription] = []
        for filepath in file_list:
            pathlib_filepath = pathlib.Path(filepath)
            extension = pathlib_filepath.suffix
            filename = pathlib_filepath.name.replace(extension, "")
            filename_parts = filename.split("_")
            if len(filename_parts) < 2:
                continue

            date_str = filename_parts[-2]
            time_str = filename_parts[-1]

            date_val = datetime.strptime(date_str, "%Y%m%d")
            time_val = datetime.strptime(time_str, "%H%M%S")

            backup_description: BackupDescription = BackupDescription()
            backup_description.filepath = filepath
            backup_description.readable_name = (
                f"{date_val.strftime('%Y-%m-%d')} {time_val.strftime('%H:%M:%S')}"
            )

            backups.append(backup_description)

        backups.sort()
        backups.reverse()

        return backups

#!/usr/bin/env python

import json
import logging
import os
import pathlib
import shutil
import tempfile
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List

import ftputil  # type: ignore
import requests  # type: ignore

from nidibot.server_provider.game_server import GameServer
from nidibot.server_provider.server_provider_interface import (
    ServerProviderConfiguration,
    ServerProviderInterface,
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
class NitradoServerInformation:
    id: str = ""
    short_name: str = ""
    status: ServerStatus = field(default_factory=ServerStatus)
    ftp: NitradoFtpConfiguration = field(default_factory=NitradoFtpConfiguration)


class NitradoServerProvider(ServerProviderInterface):
    def __init__(
        self,
        configuration: ServerProviderConfiguration,
        backup_directory: str,
        notify_callback,
    ):
        if not configuration.token:
            raise ValueError("API token value is required for nidibot start!")

        if not backup_directory:
            raise ValueError("Backup directory value is required for nidibot start!")

        self.__configuration = configuration
        self.__backup_directory = backup_directory
        self.__notify_callback = notify_callback

        self.__servers: Dict[str, NitradoServerInformation] = {}

        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s:%(levelname)s:%(funcName)s %(message)s",
            handlers=[logging.StreamHandler()],
        )

        self.__data_received_event = threading.Event()
        self.__stopping_event = threading.Event()

        self.__polling_thread = threading.Thread(target=self._poll)
        self.__polling_thread.daemon = True
        self.__polling_thread.start()

        self.__data_received_event.wait()

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
                logging.debug("Downloaded '%s'.", remote_filepath)

            for folder_name in folders:
                self.__download_ftp_folder(
                    ftp_server=ftp_server,
                    local_path=local_path,
                    remote_path=os.path.join(root_path, folder_name),
                    ignore_folders=ignore_folders,
                )

            return

    def __get_services(self) -> list:
        service_list = []

        try:
            headers = {"Authorization": self.__configuration.token}
            response = requests.get(
                "https://api.nitrado.net/services",
                timeout=self.__configuration.timeout_seconds,
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
                    headers = {"Authorization": self.__configuration.token}
                    response = requests.get(
                        f"https://api.nitrado.net/services/{service.id}/gameservers",
                        timeout=self.__configuration.timeout_seconds,
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
                    server.id = service.id
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
                        self.__configuration.notifications.on_new_server
                        and server_id not in self.__servers
                    ):
                        self.__notify_callback(
                            title, "New game server appeared, please configure it."
                        )

                    if (
                        self.__configuration.notifications.on_status_change
                        and server.status.status
                        != self.__servers[server_id].status.status
                    ):
                        self.__notify_callback(
                            title,
                            f"Status changed from '{self.__servers[server_id].status.status}' to "
                            f"'{server.status.status}'.",
                        )

                    if (
                        self.__configuration.notifications.on_address_change
                        and server.status.address
                        != self.__servers[server_id].status.address
                    ):
                        self.__notify_callback(
                            title,
                            f"Address from '{self.__servers[server_id].status.address}' to "
                            f"'{server.status.address}'.",
                        )

                    if (
                        self.__configuration.notifications.on_version_change
                        and server.status.version
                        != self.__servers[server_id].status.version
                    ):
                        self.__notify_callback(
                            title,
                            f"Version from '{self.__servers[server_id].status.version}' to "
                            f"'{server.status.version}'.",
                        )

                    if (
                        self.__configuration.notifications.on_update_available_change
                        and server.status.update_available
                        != self.__servers[server_id].status.update_available
                    ):
                        self.__notify_callback(
                            title,
                            "Update is available, please restart server.",
                        )

            self.__servers = servers

            self.__data_received_event.set()
            self.__stopping_event.wait(self.__configuration.polling_seconds)

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
            headers = {"Authorization": self.__configuration.token}
            response = requests.post(
                f"https://api.nitrado.net/services/{server_id}/gameservers/stop",
                timeout=self.__configuration.timeout_seconds,
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
            headers = {"Authorization": self.__configuration.token}
            response = requests.post(
                f"https://api.nitrado.net/services/{server_id}/gameservers/restart",
                timeout=self.__configuration.timeout_seconds,
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
                datetime_now = datetime.now()
                datetime_str = datetime_now.strftime("%Y%m%d_%H%M%S")
                backup_filename = (
                    f"{self.name().lower()}_{self.__servers[server_id].short_name}_"
                    f"id-{server_id}_{datetime_str}"
                )
                local_path = os.path.join(temp_folder_path, backup_filename)
                pathlib.Path(local_path).mkdir(parents=True, exist_ok=True)

                with ftputil.FTPHost(
                    self.__servers[server_id].ftp.hostname,
                    self.__servers[server_id].ftp.username,
                    self.__servers[server_id].ftp.password,
                ) as ftp:
                    self.__download_ftp_folder(
                        ftp_server=ftp,
                        local_path=local_path,
                        remote_path=".",
                        ignore_folders=["Crashes", "CrashReportClient"],
                    )

                shutil.make_archive(
                    os.path.join(self.__backup_directory, backup_filename),
                    "zip",
                    local_path,
                )

                logging.debug(
                    "Created backup archive at path: '%s'.",
                    os.path.join(self.__backup_directory, backup_filename),
                )

            end_time = time.time()
            logging.debug("FTP copy took %s.", end_time - start_time)

        except Exception as exception:
            logging.exception(exception)
            return False

        return True

    def restore_backup(self, server_id: str = "") -> bool:
        return False

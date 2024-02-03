#!/usr/bin/env python

from dataclasses import dataclass, field
from datetime import datetime
import json
import logging
import os
import pathlib
import shutil
import tempfile
import threading
import time
import ftputil

import requests
from .server_provider_interface import ServerProviderInterface, ServerStatus


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
    def __init__(self, api_token: str, backup_directory: str):
        if not api_token:
            raise ValueError("API token value is required for nidibot start!")

        if not backup_directory:
            raise ValueError("Backup directory value is required for nidibot start!")

        self.__api_token = api_token
        self.__backup_directory = backup_directory
        self.__default_timeout_seconds = 10
        self.__default_polling_seconds = 5

        self.__servers: list = []

        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s:%(levelname)s:%(funcName)s %(message)s",
            handlers=[logging.StreamHandler()],
        )

        self.__stopping_condition = threading.Event()
        self.__polling_thread = threading.Thread(target=self._poll)
        self.__polling_thread.daemon = True
        self.__polling_thread.start()

    def __get_services(self) -> list:
        service_list = []

        try:
            headers = {"Authorization": self.__api_token}
            response = requests.get(
                "https://api.nitrado.net/services",
                timeout=self.__default_timeout_seconds,
                headers=headers,
            )

            logging.debug(
                "Response received, status code: %d, content: '%s'.",
                response.status_code,
                response.content.decode("utf-8"),
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

    def _poll(self) -> None:
        logging.debug("Polling thread started.")

        while not self.__stopping_condition.is_set():
            servers: list = []
            services = self.__get_services()
            for service in services:
                try:
                    headers = {"Authorization": self.__api_token}
                    response = requests.get(
                        f"https://api.nitrado.net/services/{service.id}/gameservers",
                        timeout=self.__default_timeout_seconds,
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
                        server.status.game_version = gameserver_dict["query"]["version"]
                        server.status.server_address = gameserver_dict["query"][
                            "connect_ip"
                        ]
                        server.status.players_limit = int(
                            gameserver_dict["query"]["player_max"]
                        )
                        server.status.players_connected = int(
                            gameserver_dict["query"]["player_current"]
                        )
                        server.status.player_names = gameserver_dict["query"]["players"]
                    else:
                        server.status.server_address = (
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

                    servers.append(server)

                except Exception as exception:
                    logging.exception(exception)

            self.__servers = servers

            self.__stopping_condition.wait(self.__default_polling_seconds)

    def status(self, server_index: int = 0) -> ServerStatus:
        return self.__servers[server_index].status

    def start(self, server_index: int = 0) -> bool:
        return self.restart(server_index)

    def stop(self, server_index: int = 0) -> bool:
        try:
            headers = {"Authorization": self.__api_token}
            response = requests.post(
                f"https://api.nitrado.net/services/{self.__servers[server_index].id}/gameservers/stop",
                timeout=self.__default_timeout_seconds,
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

    def restart(self, server_index: int = 0) -> bool:
        try:
            headers = {"Authorization": self.__api_token}
            response = requests.post(
                f"https://api.nitrado.net/services/{self.__servers[server_index].id}/gameservers/restart",
                timeout=self.__default_timeout_seconds,
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

    def create_backup(self, server_index: int = 0) -> bool:
        try:
            start_time = time.time()
            with tempfile.TemporaryDirectory() as temp_folder_path:
                datetime_now = datetime.now()
                datetime_str = datetime_now.strftime("%Y%m%d_%H%M%S")
                backup_filename = "palworld_nitrado_backup_" + datetime_str
                local_path = os.path.join(temp_folder_path, backup_filename)
                pathlib.Path(local_path).mkdir(parents=True, exist_ok=True)

                with ftputil.FTPHost(
                    self.__servers[server_index].ftp.hostname,
                    self.__servers[server_index].ftp.username,
                    self.__servers[server_index].ftp.password,
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

            end_time = time.time()
            logging.debug("FTP copy took %s.", end_time - start_time)

        except Exception as exception:
            logging.exception(exception)
            return False

        return True

    def restore_backup(self, server_index: int = 0) -> bool:
        return False

#!/usr/bin/env python

from dataclasses import dataclass, field
import json
import logging
import requests


@dataclass
class NitradoService:
    id: str = ""
    short_name: str = ""
    available_until: str = ""


@dataclass
class NitradoServerStatus:
    game_name: str = ""
    game_version: str = ""
    server_address: str = ""
    status: str = ""
    available_until: str = ""
    update_available: bool = False
    players_limit: int = 0
    players_connected: int = 0
    player_names: list = field(default_factory=list)


@dataclass
class NitradoFtpConfiguration:
    hostname: str = ""
    port: int = 21
    username: str = ""
    password: str = ""


class Nitrado:
    def __init__(self, api_token: str):
        self.__api_token = api_token
        self.__default_timeout_seconds = 10

        self.__service_list = self.__get_service_list()
        self.__ftp_configuration = self.__get_ftp_configuration()

        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s:%(levelname)s:%(funcName)s %(message)s",
            handlers=[logging.StreamHandler()],
        )

    def __get_service_list(self) -> list:
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

    def __get_ftp_configuration(self) -> NitradoFtpConfiguration:
        ftp_configuration: NitradoFtpConfiguration = NitradoFtpConfiguration()

        try:
            headers = {"Authorization": self.__api_token}
            response = requests.get(
                f"https://api.nitrado.net/services/{self.__service_list[0].id}/gameservers",
                timeout=self.__default_timeout_seconds,
                headers=headers,
            )

            logging.debug(
                "Response received, status code: %d.",
                response.status_code,
            )

            content_json = json.loads(response.content.decode("utf-8"))
            ftp_dict = content_json["data"]["gameserver"]["credentials"]["ftp"]

            ftp_configuration.hostname = ftp_dict["hostname"]
            ftp_configuration.port = int(ftp_dict["port"])
            ftp_configuration.username = ftp_dict["username"]
            ftp_configuration.password = ftp_dict["password"]

        except Exception as exception:
            logging.exception(exception)

        return ftp_configuration

    def is_api_available(self) -> bool:
        try:
            response = requests.get(
                "https://api.nitrado.net/ping", timeout=self.__default_timeout_seconds
            )

            logging.debug(
                "Response received, status code: %d, content: '%s'.",
                response.status_code,
                response.content.decode("utf-8"),
            )

            return response.status_code == 200

        except Exception as exception:
            logging.exception(exception)
            return False

    def is_maintenance_ongoing(self) -> bool:
        try:
            response = requests.get(
                "https://api.nitrado.net/maintenance",
                timeout=self.__default_timeout_seconds,
            )

            logging.debug(
                "Response received, status code: %d, content: '%s'.",
                response.status_code,
                response.content.decode("utf-8"),
            )

            content_json = json.loads(response.content.decode("utf-8"))
            maintenance_dict = content_json["data"]["maintenance"]

            return response.status_code == 200 and (
                bool(maintenance_dict["cloud_backend"])
                or bool(maintenance_dict["domain_backend"])
                or bool(maintenance_dict["dns_backend"])
                or bool(maintenance_dict["pmacct_backend"])
            )

        except Exception as exception:
            logging.exception(exception)
            return True

    def get_status(self, server_index: int = 0) -> NitradoServerStatus:
        server_status: NitradoServerStatus = NitradoServerStatus()

        try:
            headers = {"Authorization": self.__api_token}
            response = requests.get(
                f"https://api.nitrado.net/services/{self.__service_list[server_index].id}/gameservers",
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

            server_status: NitradoServerStatus = NitradoServerStatus()
            server_status.game_name = gameserver_dict["game_human"]
            server_status.update_available = (
                gameserver_dict["game_specific"]["update_status"] != "up_to_date"
            )
            server_status.available_until = self.__service_list[
                server_index
            ].available_until

            if gameserver_dict["status"] == "started":
                server_status.status = "online"
            elif gameserver_dict["status"] == "stopped":
                server_status.status = "offline"
            elif gameserver_dict["status"] == "starting":
                server_status.status = "starting"

            if len(query_dict) > 0:
                server_status.game_version = gameserver_dict["query"]["version"]
                server_status.server_address = gameserver_dict["query"]["connect_ip"]
                server_status.players_limit = int(
                    gameserver_dict["query"]["player_max"]
                )
                server_status.players_connected = int(
                    gameserver_dict["query"]["player_current"]
                )
                server_status.player_names = gameserver_dict["query"]["players"]
            else:
                server_status.server_address = (
                    str(gameserver_dict["ip"])
                    + ":"
                    + str(gameserver_dict["query_port"])
                )
                server_status.players_limit = int(gameserver_dict["slots"])
                server_status.player_names = []

            return server_status

        except Exception as exception:
            logging.exception(exception)

        return NitradoServerStatus()

    def get_statuses(self) -> list:
        statuses = []

        counter = 0
        for _ in self.__service_list:
            statuses.append(self.get_status(counter))
            counter += 1

        return statuses

    def start(self, server_index: int = 0) -> bool:
        return self.restart(server_index)

    def stop(self, server_index: int = 0) -> bool:
        try:
            headers = {"Authorization": self.__api_token}
            response = requests.post(
                f"https://api.nitrado.net/services/{self.__service_list[server_index].id}/gameservers/stop",
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
                f"https://api.nitrado.net/services/{self.__service_list[server_index].id}/gameservers/restart",
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

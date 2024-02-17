#!/usr/bin/env python

from dataclasses import dataclass, field
import json
import logging
import os
import pathlib
import platform
import shutil
from logging.handlers import TimedRotatingFileHandler
from typing import List

from dacite import from_dict

from nidibot.bots.bot_factory import BotFactory
from nidibot.bots.bot_interface import BotConfiguration, BotInterface
from nidibot.server_provider.game_server import GameServer
from nidibot.server_provider.server_provider_factory import ServerProviderFactory
from nidibot.server_provider.server_provider_interface import (
    ServerProviderConfiguration,
    ServerProviderInterface,
)


@dataclass
class StorageConfiguration:
    type: str = ""
    token: str = ""


@dataclass
class NidibotConfiguration:
    bots: List[BotConfiguration] = field(default_factory=list)
    server_providers: List[ServerProviderConfiguration] = field(default_factory=list)
    storage: StorageConfiguration = field(default_factory=StorageConfiguration)


class Nidibot:
    def __init__(self, working_folder_path: str):
        if not working_folder_path:
            raise ValueError("Working directory value is required for nidibot start!")

        self.__working_folder_path = working_folder_path
        self.__configuration: NidibotConfiguration = NidibotConfiguration()

        self.__initialize_logging()

        root_backup_path = os.path.join(self.__working_folder_path, "backups")
        pathlib.Path(root_backup_path).mkdir(parents=True, exist_ok=True)

        self.__configuration = self.__parse_configuration_json_file()

        self.__server_providers: List[ServerProviderInterface] = (
            ServerProviderFactory.create_all(
                configuration_list=self.__configuration.server_providers,
                root_backup_path=root_backup_path,
            )
        )
        if len(self.__server_providers) == 0:
            raise ValueError("At least one server provider is required!")

        self.__game_servers: List[GameServer] = []
        for server_provider in self.__server_providers:
            self.__game_servers.extend(server_provider.get_servers())

        self.__bots: List[BotInterface] = BotFactory.create_all(
            configuration_list=self.__configuration.bots,
            game_servers=self.__game_servers,
        )
        if len(self.__bots) == 0:
            raise ValueError("At least one bot is required!")

    def __initialize_logging(self) -> None:
        #
        # Enable daily logging both to file and stdout.
        #
        log_directory = os.path.join(self.__working_folder_path, "logs")
        pathlib.Path(log_directory).mkdir(parents=True, exist_ok=True)

        filename = "nidibot.log"
        filepath = os.path.join(log_directory, filename)

        handler = TimedRotatingFileHandler(filepath, when="midnight", backupCount=60)
        handler.suffix = "%Y%m%d"

        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s:%(levelname)s:%(funcName)s(): %(message)s",
            handlers=[handler, logging.StreamHandler()],
        )

        logging.getLogger("hikari").setLevel(logging.WARNING)
        logging.getLogger("lightbulb").setLevel(logging.WARNING)
        logging.getLogger("requests").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)

    def __parse_configuration_json_file(self) -> NidibotConfiguration:
        configuration_filepath = os.path.join(
            self.__working_folder_path, "bot_configuration.json"
        )

        with open(configuration_filepath, "r", encoding="utf-8") as json_file:
            configuration_json = json.load(json_file)

        configuration = from_dict(
            data_class=NidibotConfiguration,
            data=configuration_json,
        )

        return configuration

    def start(self) -> None:
        for bot in self.__bots:
            bot.activate()

    @staticmethod
    def initialize_folder() -> None:
        """ """
        current_script_folder = os.path.dirname(os.path.realpath(__file__))
        current_working_folder = os.getcwd()
        shutil.copytree(
            os.path.join(current_script_folder, "templates", "common"),
            current_working_folder,
            dirs_exist_ok=True,
        )

        if platform.system() == "Linux":
            shutil.copytree(
                os.path.join(current_script_folder, "templates", "linux"),
                current_working_folder,
                dirs_exist_ok=True,
            )

            #
            # Modify path to working folder in "nidibot.service" file.
            #
            file_lines: list = []
            service_filepath = os.path.join(current_working_folder, "nidibot.service")
            with open(
                file=service_filepath, mode="r", encoding="utf-8"
            ) as service_file:
                file_lines = service_file.readlines()

            for line_index, line in enumerate(file_lines):
                if "ExecStart=/user/bin/python3 /home/nidibot/start_bot.py" in line:
                    script_filepath = os.path.join(current_working_folder, "start_bot.py")
                    edited_line = f"ExecStart=/user/bin/python3 {script_filepath}\n"
                    file_lines[line_index] = edited_line

            with open(
                file=service_filepath, mode="w", encoding="utf-8"
            ) as service_file:
                service_file.writelines(file_lines)

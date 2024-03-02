#!/usr/bin/env python

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from multiprocessing import Lock
from typing import Dict, List

from nidibot.server_provider.game_server import GameServer


@dataclass
class BotForwardMessage:
    title: str = ""
    message: str = ""


@dataclass
class BackupDescription:
    readable_name: str = ""
    filepath: str = ""

    def __lt__(self, other):
        return self.readable_name < other.readable_name


@dataclass
class BotConfiguration:
    type: str = ""
    token: str = ""
    privileged_users: list = field(default_factory=list)
    allowed_channels: list = field(default_factory=list)
    notify_polling_seconds: int = 5


class BotBase(ABC):
    def __init__(self, configuration: BotConfiguration, game_servers: List[GameServer]):
        self._configuration = configuration
        self._game_servers = game_servers

        self._backups: Dict[str, List[BackupDescription]] = {}
        self._game_server_names: list = []
        for game_server in self._game_servers:
            self._game_server_names.append(game_server.name())
            self._backups[game_server.name()] = game_server.list_backups()

        self._notify_mutex = Lock()
        self._notify_messages: List[BotForwardMessage] = []

    def _get_response_title(self, game_server: GameServer) -> str:
        server_status = game_server.status()

        title = f"{server_status.game_name}"
        if server_status.version:
            title += f" ({server_status.version})"

        title += f" - {server_status.address}"

        return title

    def _get_game_server(self, server_name: str = "") -> GameServer:
        if not server_name:
            game_server = self._game_servers[0]
        else:
            game_server = next(x for x in self._game_servers if x.name() == server_name)

        return game_server

    @abstractmethod
    def notify(self, title: str, message: str) -> None:
        pass

    @abstractmethod
    def start(self) -> None:
        pass

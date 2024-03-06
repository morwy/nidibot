#!/usr/bin/env python

"""
nidibot.bots.bot_base
~~~~~~~~~~~~~~~~~~~~~

Base components of bot instances.

"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from multiprocessing import Lock
from typing import Dict, List

from nidibot.server_provider.game_server import GameServer


@dataclass
class BotForwardMessage:
    """Class describing parameters of messages to be delivered to connected channels."""

    title: str = ""
    """The title of message."""

    message: str = ""
    """The body of message."""


@dataclass
class BackupDescription:
    """Class describing parameters of backup."""

    readable_name: str = ""
    """The readable name of the backup in format `YYYY-MM-DD HH:MM:SS`."""

    filepath: str = ""
    """The filepath to the backup file."""

    def __lt__(self, other):
        return self.readable_name < other.readable_name


@dataclass
class BotConfiguration:
    """Class describing general parameters of bot configuration."""

    type: str = ""
    """The type of the bot. Allowed values: `discord`, `telegram`."""

    token: str = ""
    """The authentication token required for the bot."""

    privileged_users: list = field(default_factory=list)
    """The list of privileged users that can call administrative commands."""

    allowed_channels: list = field(default_factory=list)
    """The list of allowed channels from where commands will be accepted and processed."""

    notify_polling_seconds: int = 5
    """The period in seconds for forwarding messages from queue to connected channels."""


class BotBase(ABC):
    """
    A base class for bot objects.
    """

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

        self._emoji_no_access = "\U0001F925"
        self._emoji_ok = "\U00002705"
        self._emoji_attention = "\U000026A0"
        self._emoji_bad = "\U000026D4"
        self._emoji_unknown = "\U00002049\U0000FE0F"

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
        """
        Forwards a new message to be spread by bot in connected channels.

        Parameters:
            `title` (str): title of message
            `message` (str): body of message
        """

    @abstractmethod
    def start(self) -> None:
        """
        Starts the bot. Blocking call.
        """

#!/usr/bin/env python

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ServerProviderConfiguration:
    type: str = ""
    token: str = ""


@dataclass
class ServerStatus:
    game_name: str = ""
    version: str = ""
    address: str = ""
    status: str = ""
    available_until: str = ""
    update_available: bool = False
    players_limit: int = 0
    players_connected: int = 0
    player_names: list = field(default_factory=list)


class ServerProviderInterface(ABC):
    @abstractmethod
    def __init__(self, api_token: str, backup_directory: str, notify_callback):
        pass

    @abstractmethod
    def _poll(self) -> None:
        pass

    @abstractmethod
    def get_servers(self) -> list:
        pass

    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def status(self, server_id: str = "") -> ServerStatus:
        pass

    @abstractmethod
    def start(self, server_id: str = "") -> bool:
        pass

    @abstractmethod
    def stop(self, server_id: str = "") -> bool:
        pass

    @abstractmethod
    def restart(self, server_id: str = "") -> bool:
        pass

    @abstractmethod
    def create_backup(self, server_id: str = "") -> bool:
        pass

    @abstractmethod
    def restore_backup(self, server_id: str = "") -> bool:
        pass

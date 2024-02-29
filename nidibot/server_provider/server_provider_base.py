#!/usr/bin/env python

import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ServerProviderNotificationConfiguration:
    on_new_server: bool = False
    on_status_change: bool = False
    on_address_change: bool = False
    on_version_change: bool = False
    on_update_available_change: bool = False


@dataclass
class ServerProviderConfiguration:
    type: str = ""
    token: str = ""
    timeout_seconds: int = 10
    polling_seconds: int = 5
    notifications: ServerProviderNotificationConfiguration = field(
        default_factory=ServerProviderNotificationConfiguration
    )


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


class ServerProviderBase(ABC):
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

        self._configuration = configuration
        self._root_backup_directory = backup_directory
        self._notify_callback = notify_callback

    @abstractmethod
    def _poll(self) -> None:
        pass

    def _get_backup_directory_path(self, game_name: str, server_id: str) -> str:
        return os.path.join(
            self._root_backup_directory, self.name().lower(), game_name, server_id
        )

    def _wait_for_status(
        self,
        server_id: str,
        required_status: str,
        timeout_seconds: int = 60,
        wait_step_seconds: int = 1,
    ) -> bool:
        end_time = time.time() + timeout_seconds
        while time.time() < end_time:
            status = self.status(server_id)
            if status.status == required_status:
                return True

            time.sleep(wait_step_seconds)

        return False

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
    def restore_backup(self, server_id: str = "", filepath: str = "") -> bool:
        pass

    @abstractmethod
    def list_backups(self, server_id: str = "") -> list:
        pass

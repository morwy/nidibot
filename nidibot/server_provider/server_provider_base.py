#!/usr/bin/env python

"""
nidibot.server_provider.server_provider_base
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Base components of server provider instances.

"""

import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ServerProviderNotificationConfiguration:
    """Class describing notification parameters for server provider status changes."""

    on_new_server: bool = False
    """Toggles notification on a new game server appearing."""

    on_status_change: bool = False
    """Toggles notification on a game server status change."""

    on_address_change: bool = False
    """Toggles notification on a game server IP address change."""

    on_version_change: bool = False
    """Toggles notification on a game server version change."""

    on_update_available_change: bool = False
    """Toggles notification if game server got an update available."""


@dataclass
class ServerProviderConfiguration:
    """Class describing general parameters of server provider configuration."""

    type: str = ""
    """The type of the server provider. Allowed values: `nitrado`."""

    token: str = ""
    """The authentication token required for the server provider."""

    timeout_seconds: int = 10
    """The timeout in seconds for getting a response from the server provider."""

    polling_seconds: int = 5
    """The period in seconds for polling a status from the server provider."""

    notifications: ServerProviderNotificationConfiguration = field(
        default_factory=ServerProviderNotificationConfiguration
    )


@dataclass
class ServerStatus:
    """Class describing status parameters of the game server."""

    game_name: str = ""
    """The name of the game."""

    version: str = ""
    """The current version of the game."""

    address: str = ""
    """The IP address of the game server."""

    status: str = ""
    """The status of the game server. Value depends on server provider."""

    available_until: str = ""
    """The date until game server is available."""

    update_available: bool = False
    """The availability of a new un-installed game update."""

    players_limit: int = 0
    """The maximum amount of players supported by server."""

    players_connected: int = 0
    """The amount of players playing at the moment."""

    player_names: list = field(default_factory=list)
    """The list of player names that are playing at the moment."""


class ServerProviderBase(ABC):
    """
    A base class for server provider objects.
    """

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
        """
        Returns list of game servers.
        """

    @abstractmethod
    def name(self) -> str:
        """
        Returns the name of the server provider.
        """

    @abstractmethod
    def status(self, server_id: str = "") -> ServerStatus:
        """
        Returns the current status of the specified server.

        Parameters:
            `server_id` (str): server ID

        Returns:
            ServerStatus: current server status
        """

    @abstractmethod
    def start(self, server_id: str = "") -> bool:
        """
        Starts the specified server.

        Parameters:
            `server_id` (str): server ID

        Returns:
            bool: operation result
        """

    @abstractmethod
    def stop(self, server_id: str = "") -> bool:
        """
        Stops the specified server.

        Parameters:
            `server_id` (str): server ID

        Returns:
            bool: operation result
        """

    @abstractmethod
    def restart(self, server_id: str = "") -> bool:
        """
        Restarts the specified server.

        Parameters:
            `server_id` (str): server ID

        Returns:
            bool: operation result
        """

    @abstractmethod
    def create_backup(self, server_id: str = "") -> bool:
        """
        Creates a backup of the specified server.

        Parameters:
            `server_id` (str): server ID

        Returns:
            bool: operation result
        """

    @abstractmethod
    def restore_backup(self, server_id: str = "", filepath: str = "") -> bool:
        """
        Restores the specified backup on the specified server.

        Parameters:
            `server_id` (str): server ID
            `filepath` (str): filepath to a backup which will be restored

        Returns:
            bool: operation result
        """

    @abstractmethod
    def list_backups(self, server_id: str = "") -> list:
        """
        Creates a list of available backups of the specified server.

        Parameters:
            `server_id` (str): server ID

        Returns:
            list: created instance
        """

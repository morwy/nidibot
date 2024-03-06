#!/usr/bin/env python

"""
nidibot.server_provider.server_provider_factory
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Components for creation of server provider instances.

"""

from nidibot.server_provider.nitrado_server_provider import NitradoServerProvider
from nidibot.server_provider.server_provider_base import ServerProviderConfiguration


class ServerProviderFactory:
    """
    A factory class for creating server provider instances.
    """

    __supported_server_providers = {
        "nitrado": NitradoServerProvider,
    }

    @staticmethod
    def create(
        configuration: ServerProviderConfiguration,
        root_backup_path: str,
        notify_callback,
    ):
        """
        Creates single instance of server provider based on provided configuration.

        Parameters:
            `configuration` (ServerProviderConfiguration): configuration of server provider
            `root_backup_path` (str): path to root backup directory
            `notify_callback` (callback_func): callback function for notifying about changes

        Returns:
            server_provider: created instance
        """

        if configuration.type not in ServerProviderFactory.__supported_server_providers:
            if not configuration.type:
                raise ValueError("Empty bot type provided!")

            raise ValueError("Unknown bot type provided!")

        return ServerProviderFactory.__supported_server_providers[configuration.type](
            configuration=configuration,
            backup_directory=root_backup_path,
            notify_callback=notify_callback,
        )

    @staticmethod
    def create_all(
        configuration_list: list, root_backup_path: str, notify_callback
    ) -> list:
        """
        Creates list of server provider instances based on provided configuration.

        Parameters:
            `configuration` (list): list of server provider configuration
            `root_backup_path` (str): defines path to root backup directory
            `notify_callback` (callback_func): callback function for notifying about changes

        Returns:
            list: list of created instances
        """

        server_providers: list = []

        for configuration in configuration_list:
            server_providers.append(
                ServerProviderFactory.create(
                    configuration=configuration,
                    root_backup_path=root_backup_path,
                    notify_callback=notify_callback,
                )
            )

        return server_providers

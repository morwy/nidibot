#!/usr/bin/env python

from nidibot.server_provider.nitrado_server_provider import NitradoServerProvider
from nidibot.server_provider.server_provider_base import ServerProviderConfiguration


class ServerProviderFactory:
    __supported_server_providers = {
        "nitrado": NitradoServerProvider,
    }

    @staticmethod
    def create(
        configuration: ServerProviderConfiguration,
        root_backup_path: str,
        notify_callback,
    ):
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

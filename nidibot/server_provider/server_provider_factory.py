#!/usr/bin/env python

from nidibot.server_provider.nitrado_server_provider import NitradoServerProvider
from nidibot.server_provider.server_provider_interface import (
    ServerProviderConfiguration,
)


class ServerProviderFactory:
    @staticmethod
    def create(configuration: ServerProviderConfiguration, root_backup_path: str):
        server_providers = {
            "nitrado": NitradoServerProvider,
        }

        if configuration.type not in server_providers:
            if not configuration.type:
                raise ValueError("Empty bot type provided!")

            raise ValueError("Unknown bot type provided!")

        return server_providers[configuration.type](
            api_token=configuration.token, backup_directory=root_backup_path
        )

    @staticmethod
    def create_all(configuration_list: list, root_backup_path: str) -> list:
        server_providers: list = []

        for configuration in configuration_list:
            server_providers.append(
                ServerProviderFactory.create(
                    configuration=configuration, root_backup_path=root_backup_path
                )
            )

        return server_providers

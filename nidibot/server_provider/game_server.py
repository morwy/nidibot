#!/usr/bin/env python

from nidibot.server_provider.server_provider_interface import (
    ServerProviderInterface,
    ServerStatus,
)


class GameServer:
    def __init__(
        self, server_provider: ServerProviderInterface, server_id: str, server_name: str
    ) -> None:
        if not server_id:
            raise ValueError("Server ID is required!")

        self.__server_provider = server_provider
        self.__server_id = server_id
        self.__server_name = server_name

    def name(self) -> str:
        return self.__server_name

    def status(self) -> ServerStatus:
        return self.__server_provider.status(self.__server_id)

    def start(self) -> bool:
        return self.__server_provider.start(self.__server_id)

    def stop(self) -> bool:
        return self.__server_provider.stop(self.__server_id)

    def restart(self) -> bool:
        return self.__server_provider.restart(self.__server_id)

    def create_backup(self) -> bool:
        return self.__server_provider.create_backup(self.__server_id)

    def restore_backup(self) -> bool:
        return self.__server_provider.restore_backup(self.__server_id)

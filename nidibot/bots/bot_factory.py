#!/usr/bin/env python

"""
nidibot.bots.bot_factory
~~~~~~~~~~~~~~~~~~~~~~~~

Components for creation of bot instances.

"""

from typing import List

from nidibot.bots.bot_base import BotConfiguration
from nidibot.bots.discord_bot import DiscordBot
from nidibot.bots.telegram_bot import TelegramBot
from nidibot.server_provider.game_server import GameServer


class BotFactory:
    """
    A factory class for creating bot instances.
    """

    __supported_bots = {
        "discord": DiscordBot,
        "telegram": TelegramBot,
    }

    @staticmethod
    def create(configuration: BotConfiguration, game_servers: List[GameServer]):
        """
        Creates single instance of bot based on provided configuration.

        Parameters:
            `configuration` (BotConfiguration): configuration of bot
            `game_servers` (list): list of available game servers

        Returns:
            bot: created instance
        """

        if configuration.type not in BotFactory.__supported_bots:
            if not configuration.type:
                raise ValueError("Empty bot type provided!")

            raise ValueError("Unknown bot type provided!")

        return BotFactory.__supported_bots[configuration.type](
            configuration=configuration, game_servers=game_servers
        )

    @staticmethod
    def create_all(configuration_list: list, game_servers: List[GameServer]) -> list:
        """
        Creates list of bot instances based on provided configuration.

        Parameters:
            `configuration` (list): list of bot configuration
            `game_servers` (list): list of available game servers

        Returns:
            list: list of created instances
        """
        bots: list = []

        for configuration in configuration_list:
            bots.append(
                BotFactory.create(
                    configuration=configuration, game_servers=game_servers
                )
            )

        return bots

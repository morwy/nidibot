#!/usr/bin/env python

from typing import List

from nidibot.bots.bot_interface import BotConfiguration
from nidibot.bots.discord_bot import DiscordBot
from nidibot.bots.telegram_bot import TelegramBot
from nidibot.server_provider.game_server import GameServer


class BotFactory:
    @staticmethod
    def create(configuration: BotConfiguration, game_servers: List[GameServer]):
        bots = {
            "discord": DiscordBot,
            "telegram": TelegramBot,
        }

        if configuration.type not in bots:
            if not configuration.type:
                raise ValueError("Empty bot type provided!")

            raise ValueError("Unknown bot type provided!")

        return bots[configuration.type](
            configuration=configuration, game_servers=game_servers
        )

    @staticmethod
    def create_all(configuration_list: list, game_servers: List[GameServer]) -> list:
        bots: list = []

        for configuration in configuration_list:
            bots.append(
                BotFactory.create(
                    configuration=configuration, game_servers=game_servers
                )
            )

        return bots

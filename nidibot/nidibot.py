#!/usr/bin/env python

from dataclasses import dataclass, field
from datetime import datetime, date
import json
import logging
import os
import pathlib
import platform
import shutil
from logging.handlers import TimedRotatingFileHandler
from typing import List

from dacite import from_dict
import hikari
import lightbulb
import pkg_resources

from nidibot.server_provider.server_provider_interface import ServerProviderInterface
from nidibot.server_provider.nitrado_server_provider import NitradoServerProvider


@dataclass
class DiscordControllerConfiguration:
    token: str = ""
    privileged_users: list = field(default_factory=list)


@dataclass
class ControllerConfiguration:
    discord: DiscordControllerConfiguration = field(
        default_factory=DiscordControllerConfiguration
    )


@dataclass
class ServerProviderConfiguration:
    type: str = ""
    token: str = ""


@dataclass
class StorageConfiguration:
    type: str = ""
    token: str = ""


@dataclass
class NidibotConfiguration:
    controller: ControllerConfiguration = field(default_factory=ControllerConfiguration)
    server_provider: List[ServerProviderConfiguration] = field(default_factory=list)
    storage: StorageConfiguration = field(default_factory=StorageConfiguration)


class Nidibot:
    def __init__(self, working_folder_path: str):
        if not working_folder_path:
            raise ValueError("Working directory value is required for nidibot start!")

        self.__working_folder_path = working_folder_path
        self.__configuration: NidibotConfiguration = NidibotConfiguration()

        self.__initialize_logging()

        backup_directory = os.path.join(self.__working_folder_path, "backup")
        pathlib.Path(backup_directory).mkdir(parents=True, exist_ok=True)

        self.__configuration = self.__parse_configuration_json_file()
        self.__server_providers: List[ServerProviderInterface] = (
            self.__initialize_server_providers(backup_directory)
        )
        self.__discord_bot = self.__initialize_discord_bot()

    def __initialize_logging(self) -> None:
        #
        # Enable daily logging both to file and stdout.
        #
        log_directory = os.path.join(self.__working_folder_path, "logs")
        pathlib.Path(log_directory).mkdir(parents=True, exist_ok=True)

        filename = "nidibot.log"
        filepath = os.path.join(log_directory, filename)

        handler = TimedRotatingFileHandler(filepath, when="midnight", backupCount=60)
        handler.suffix = "%Y%m%d"

        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s:%(levelname)s:%(funcName)s(): %(message)s",
            handlers=[handler, logging.StreamHandler()],
        )

        logging.getLogger("hikari").setLevel(logging.WARNING)
        logging.getLogger("lightbulb").setLevel(logging.WARNING)
        logging.getLogger("requests").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)

    def __parse_configuration_json_file(self) -> NidibotConfiguration:
        configuration_filepath = os.path.join(
            self.__working_folder_path, "bot_configuration.json"
        )

        with open(configuration_filepath, "r", encoding="utf-8") as json_file:
            configuration_json = json.load(json_file)

        configuration = from_dict(
            data_class=NidibotConfiguration,
            data=configuration_json,
        )

        return configuration

    def __initialize_server_providers(self, backup_directory: str) -> list:
        server_providers: list = []

        for server_provider_configuration in self.__configuration.server_provider:
            if server_provider_configuration.type == "nitrado":
                server_provider = NitradoServerProvider(
                    server_provider_configuration.token, backup_directory
                )
                server_providers.append(server_provider)

        if len(server_providers) == 0:
            raise ValueError("At least one server provider is required!")

        return server_providers

    def __initialize_discord_bot(self) -> lightbulb.BotApp:
        token = self.__configuration.controller.discord.token
        privileged_users = self.__configuration.controller.discord.privileged_users

        bot = lightbulb.BotApp(token=token)

        @bot.listen(hikari.StartedEvent)
        async def on_started(_) -> None:
            try:
                nidibot_version = pkg_resources.get_distribution("nidibot").version
                logging.info("nidibot v%s was started.", nidibot_version)
            except pkg_resources.DistributionNotFound:
                logging.debug("nidibot was started.")

        @bot.command
        @lightbulb.option(
            name="index",
            description="States server index to which command will be applied",
            required=False,
        )
        @lightbulb.command(
            name="status",
            description="Provides extended information about game server status.",
        )
        @lightbulb.implements(lightbulb.SlashCommand)
        async def status(ctx) -> None:
            logging.debug("Called 'status' by '%s'.", ctx.author)

            # server_index = ctx.options.index
            server_status = self.__server_providers[0].status()

            title = f"{server_status.game_name}"
            if server_status.game_version:
                title += f" ({server_status.game_version})"

            if server_status.status == "online":
                status_smiley = ":white_check_mark:"
                status_color = hikari.colors.Color(0x37CB78)
            elif server_status.status == "offline":
                status_smiley = ":no_entry:"
                status_color = hikari.colors.Color(0xE64A42)
            elif server_status.status == "restarting":
                status_smiley = ":warning:"
                status_color = hikari.colors.Color(0xE67E22)
            else:
                status_smiley = ":interrobang:"
                status_color = hikari.colors.Color(0xE67E22)

            embed = hikari.Embed(
                title=title,
                color=status_color,
            )

            embed.add_field(
                name="Address:", value=f"`{server_status.server_address}`", inline=True
            )
            embed.add_field(
                name="Status:",
                value=f"{status_smiley} {server_status.status}",
                inline=True,
            )

            players = (
                f"{server_status.players_connected} / {server_status.players_limit}"
            )
            if len(server_status.player_names) > 0:
                players += f" ({server_status.player_names})"
            embed.add_field(name="Players:", value=f"{players}", inline=True)

            update_smiley = ""
            if server_status.update_available:
                update_smiley = ":warning:"
            else:
                update_smiley = ":white_check_mark:"

            date_time = server_status.available_until.split(" ")
            date_parts = date_time[0].split("-")

            d0 = date(datetime.now().year, datetime.now().month, datetime.now().day)
            d1 = date(int(date_parts[0]), int(date_parts[1]), int(date_parts[2]))
            delta = d1 - d0

            embed.add_field(
                name="Available until:",
                value=f"{server_status.available_until} ({delta.days} days left)",
                inline=True,
            )
            embed.add_field(
                name="Update available:",
                value=f"{update_smiley} {'yes' if server_status.update_available else 'no'}",
                inline=True,
            )

            await ctx.respond(embed=embed)

        @bot.command
        @lightbulb.option(
            name="index",
            description="States server index to which command will be applied",
            required=False,
        )
        @lightbulb.command(
            name="start",
            description="Starts server if it is offline, restarts server if it is online.",
        )
        @lightbulb.implements(lightbulb.SlashCommand)
        async def start(ctx) -> None:
            logging.debug("Called 'start' by '%s'.", ctx.author)

            server_status = self.__server_providers[0].status()

            title = f"{server_status.game_name}"
            if server_status.game_version:
                title += f" ({server_status.game_version})"

            user = str(ctx.author)
            if user not in privileged_users:
                embed = hikari.Embed(
                    title=title,
                    description="Sorry but you don't have rights to call this command! :liar:",
                    color=hikari.colors.Color(0xE64A42),
                )

                await ctx.respond(embed=embed)
                return

            embed = hikari.Embed(
                title=title,
                description=":warning: Starting server! :warning:",
                color=hikari.colors.Color(0xE64A42),
            )
            await ctx.respond(embed=embed)

            self.__server_providers[0].start()

        @bot.command
        @lightbulb.option(
            name="index",
            description="States server index to which command will be applied",
            required=False,
        )
        @lightbulb.command(
            name="stop",
            description="Stops server if it is online.",
        )
        @lightbulb.implements(lightbulb.SlashCommand)
        async def stop(ctx) -> None:
            logging.debug("Called 'stop' by '%s'.", ctx.author)

            server_status = self.__server_providers[0].status()

            title = f"{server_status.game_name}"
            if server_status.game_version:
                title += f" ({server_status.game_version})"

            user = str(ctx.author)
            if user not in privileged_users:
                embed = hikari.Embed(
                    title=title,
                    description="Sorry but you don't have rights to call this command! :liar:",
                    color=hikari.colors.Color(0xE64A42),
                )

                await ctx.respond(embed=embed)
                return

            embed = hikari.Embed(
                title=title,
                description=":warning: Stopping server! :warning:",
                color=hikari.colors.Color(0xE64A42),
            )
            await ctx.respond(embed=embed)

            self.__server_providers[0].stop()

        @bot.command
        @lightbulb.option(
            name="index",
            description="States server index to which command will be applied",
            required=False,
        )
        @lightbulb.command(
            name="restart",
            description="Restarts server if it is online, starts server if it is offline.",
        )
        @lightbulb.implements(lightbulb.SlashCommand)
        async def restart(ctx) -> None:
            logging.debug("Called 'restart' by '%s'.", ctx.author)

            server_status = self.__server_providers[0].status()

            title = f"{server_status.game_name}"
            if server_status.game_version:
                title += f" ({server_status.game_version})"

            user = str(ctx.author)
            if user not in privileged_users:
                embed = hikari.Embed(
                    title=title,
                    description="Sorry but you don't have rights to call this command! :liar:",
                    color=hikari.colors.Color(0xE64A42),
                )

                await ctx.respond(embed=embed)
                return

            embed = hikari.Embed(
                title=title,
                description=":warning: Restarting server! :warning:",
                color=hikari.colors.Color(0xE64A42),
            )
            await ctx.respond(embed=embed)

            self.__server_providers[0].restart()

        @bot.command
        @lightbulb.option(
            name="index",
            description="States server index to which command will be applied",
            required=False,
        )
        @lightbulb.command(
            name="backup",
            description="Creates backup of games server files and uploads them to storage.",
        )
        @lightbulb.implements(lightbulb.SlashCommand)
        async def backup(ctx) -> None:
            logging.debug("Called 'backup' by '%s'.", ctx.author)

            server_status = self.__server_providers[0].status()

            title = f"{server_status.game_name}"
            if server_status.game_version:
                title += f" ({server_status.game_version})"

            user = str(ctx.author)
            if user not in privileged_users:
                embed = hikari.Embed(
                    title=title,
                    description="Sorry but you don't have rights to call this command! :liar:",
                    color=hikari.colors.Color(0xE64A42),
                )

                await ctx.respond(embed=embed)
                return

            embed = hikari.Embed(
                title=title,
                description=":warning: Started creating backup of the server, please wait.",
                color=hikari.colors.Color(0xE67E22),
            )
            await ctx.respond(embed=embed)

            if self.__server_providers[0].create_backup():
                embed = hikari.Embed(
                    title=title,
                    description=":white_check_mark: Backup was created successfully!",
                    color=hikari.colors.Color(0x37CB78),
                )
            else:
                embed = hikari.Embed(
                    title=title,
                    description=":no_entry: Backup creation failed, please check bot logs!",
                    color=hikari.colors.Color(0xE64A42),
                )

            await ctx.respond(embed=embed)

        return bot

    @staticmethod
    def initialize_folder() -> None:
        """ """
        current_script_folder = os.path.dirname(os.path.realpath(__file__))
        current_working_folder = os.getcwd()
        shutil.copytree(
            os.path.join(current_script_folder, "templates", "common"),
            current_working_folder,
            dirs_exist_ok=True,
        )

        if platform.system() == "Linux":
            shutil.copytree(
                os.path.join(current_script_folder, "templates", "linux"),
                current_working_folder,
                dirs_exist_ok=True,
            )

    def activate(self) -> None:
        self.__discord_bot.run()

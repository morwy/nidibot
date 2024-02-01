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

from dacite import from_dict
import hikari
import lightbulb

from nidibot.nitrado import Nitrado


@dataclass
class NidibotConnectionConfiguration:
    discord_bot_token: str = ""
    nitrado_api_token: str = ""


@dataclass
class NidibotConfiguration:
    connection: NidibotConnectionConfiguration = field(
        default_factory=NidibotConnectionConfiguration
    )
    discord_admin_users: list = field(default_factory=list)


class Nidibot:
    def __init__(self, working_folder_path: str = None):
        if working_folder_path is None:
            return

        self.__working_folder_path = working_folder_path
        self.__configuration: NidibotConfiguration = NidibotConfiguration()

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
            format="%(asctime)s:%(levelname)s:%(funcName)s %(message)s",
            handlers=[handler, logging.StreamHandler()],
        )

        self.__configuration = self.__parse_configuration_json_file()

        self.__gameserver = Nitrado(self.__configuration.connection.nitrado_api_token)

        self.__bot = lightbulb.BotApp(
            token=self.__configuration.connection.discord_bot_token
        )

        @self.__bot.listen(hikari.StartedEvent)
        async def on_started(_) -> None:
            logging.debug("Starting the bot.")
            # logging.debug("Bot is logged in as '%s' user.", self.__bot.user.name)

            logging.debug("Waiting for command tree sync.")
            # await self.__bot.tree.sync()
            logging.debug("Command tree sync is completed.")

        @self.__bot.command
        @lightbulb.command(
            name="status",
            description="Provides extended information about game server status.",
        )
        @lightbulb.implements(lightbulb.SlashCommand)
        async def status(ctx) -> None:
            logging.debug("Called 'status' by '%s'.", ctx.author)

            server_status = self.__gameserver.get_status()

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

        @self.__bot.command
        @lightbulb.command(
            name="start",
            description="Starts server if it is offline, restarts server if it is online.",
        )
        @lightbulb.implements(lightbulb.SlashCommand)
        async def start(ctx) -> None:
            logging.debug("Called 'start' by '%s'.", ctx.author)

            user = str(ctx.author)
            if user not in self.__configuration.discord_admin_users:
                embed = hikari.Embed(
                    description="Sorry but you don't have rights to call this command! :liar:",
                    color=hikari.colors.Color(0xE64A42),
                )

                await ctx.respond(embed=embed)
                return

            embed = hikari.Embed(
                description=":warning: Starting server! :warning:",
                color=hikari.colors.Color(0xE64A42),
            )
            await ctx.respond(embed=embed)

            self.__gameserver.start()

        @self.__bot.command
        @lightbulb.command(
            name="stop",
            description="Stops server if it is online.",
        )
        @lightbulb.implements(lightbulb.SlashCommand)
        async def stop(ctx) -> None:
            logging.debug("Called 'stop' by '%s'.", ctx.author)

            user = str(ctx.author)
            if user not in self.__configuration.discord_admin_users:
                embed = hikari.Embed(
                    description="Sorry but you don't have rights to call this command! :liar:",
                    color=hikari.colors.Color(0xE64A42),
                )

                await ctx.respond(embed=embed)
                return

            embed = hikari.Embed(
                description=":warning: Stopping server! :warning:",
                color=hikari.colors.Color(0xE64A42),
            )
            await ctx.respond(embed=embed)

            self.__gameserver.stop()

        @self.__bot.command
        @lightbulb.command(
            name="restart",
            description="Restarts server if it is online, starts server if it is offline.",
        )
        @lightbulb.implements(lightbulb.SlashCommand)
        async def restart(ctx) -> None:
            logging.debug("Called 'restart' by '%s'.", ctx.author)

            user = str(ctx.author)
            if user not in self.__configuration.discord_admin_users:
                embed = hikari.Embed(
                    description="Sorry but you don't have rights to call this command! :liar:",
                    color=hikari.colors.Color(0xE64A42),
                )

                await ctx.respond(embed=embed)
                return

            embed = hikari.Embed(
                description=":warning: Restarting server! :warning:",
                color=hikari.colors.Color(0xE64A42),
            )
            await ctx.respond(embed=embed)

            self.__gameserver.restart()

        @self.__bot.command
        @lightbulb.command(
            name="backup",
            description="Creates backup of games server files and uploads them to storage.",
        )
        @lightbulb.implements(lightbulb.SlashCommand)
        async def backup(ctx) -> None:
            logging.debug("Called 'backup' by '%s'.", ctx.author)

            user = str(ctx.author)
            if user not in self.__configuration.discord_admin_users:
                embed = hikari.Embed(
                    description="Sorry but you don't have rights to call this command! :liar:",
                    color=hikari.colors.Color(0xE64A42),
                )

                await ctx.respond(embed=embed)
                return

            embed = hikari.Embed(
                description=":no_entry: This command is not yet implemented! :no_entry:",
                color=hikari.colors.Color(0xE64A42),
            )

            await ctx.respond(embed=embed)

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
        self.__bot.run()

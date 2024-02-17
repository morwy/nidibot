#!/usr/bin/env python

from datetime import datetime, date
from typing import List
import logging

import hikari
import lightbulb
import pkg_resources
from nidibot.bots.bot_interface import BotConfiguration, BotInterface
from nidibot.server_provider.game_server import GameServer


class DiscordBot(BotInterface):
    def __init__(self, configuration: BotConfiguration, game_servers: List[GameServer]):
        self.__configuration = configuration
        self.__game_servers = game_servers

        self.__game_server_names: list = []
        for game_server in self.__game_servers:
            self.__game_server_names.append(game_server.name())

        self.__bot = lightbulb.BotApp(token=self.__configuration.token)

        def get_embed_title(game_server) -> str:
            server_status = game_server.status()

            title = f"{server_status.game_name}"
            if server_status.game_version:
                title += f" ({server_status.game_version})"

            title += f" - {server_status.server_address}"

            return title

        @self.__bot.listen(hikari.StartedEvent)
        async def on_started(_) -> None:
            try:
                nidibot_version = pkg_resources.get_distribution("nidibot").version
                logging.info("nidibot v%s was started.", nidibot_version)
            except pkg_resources.DistributionNotFound:
                logging.debug("nidibot was started.")

        @self.__bot.command
        @lightbulb.option(
            name="name",
            description="States server to which command will be applied",
            choices=self.__game_server_names,
            required=False,
        )
        @lightbulb.command(
            name="status",
            description="Provides extended information about game server status.",
        )
        @lightbulb.implements(lightbulb.SlashCommand)
        async def status(ctx) -> None:
            logging.debug("Called 'status' by '%s'.", ctx.author)

            server_name = ctx.options.name
            if server_name is None:
                game_server = self.__game_servers[0]
            else:
                game_server = next(
                    x for x in self.__game_servers if x.name() == server_name
                )

            server_status = game_server.status()

            title = get_embed_title(game_server)

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

        @self.__bot.command
        @lightbulb.option(
            name="name",
            description="States server to which command will be applied",
            choices=self.__game_server_names,
            required=False,
        )
        @lightbulb.command(
            name="start",
            description="Starts server if it is offline, restarts server if it is online.",
        )
        @lightbulb.implements(lightbulb.SlashCommand)
        async def start(ctx) -> None:
            logging.debug("Called 'start' by '%s'.", ctx.author)

            server_name = ctx.options.name
            if server_name is None:
                game_server = self.__game_servers[0]
            else:
                game_server = next(
                    x for x in self.__game_servers if x.name() == server_name
                )

            title = get_embed_title(game_server)

            user = str(ctx.author)
            if user not in self.__configuration.privileged_users:
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

            game_server.start()

        @self.__bot.command
        @lightbulb.option(
            name="name",
            description="States server to which command will be applied",
            choices=self.__game_server_names,
            required=False,
        )
        @lightbulb.command(
            name="stop",
            description="Stops server if it is online.",
        )
        @lightbulb.implements(lightbulb.SlashCommand)
        async def stop(ctx) -> None:
            logging.debug("Called 'stop' by '%s'.", ctx.author)

            server_name = ctx.options.name
            if server_name is None:
                game_server = self.__game_servers[0]
            else:
                game_server = next(
                    x for x in self.__game_servers if x.name() == server_name
                )

            title = get_embed_title(game_server)

            user = str(ctx.author)
            if user not in self.__configuration.privileged_users:
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

            game_server.stop()

        @self.__bot.command
        @lightbulb.option(
            name="name",
            description="States server to which command will be applied",
            choices=self.__game_server_names,
            required=False,
        )
        @lightbulb.command(
            name="restart",
            description="Restarts server if it is online, starts server if it is offline.",
        )
        @lightbulb.implements(lightbulb.SlashCommand)
        async def restart(ctx) -> None:
            logging.debug("Called 'restart' by '%s'.", ctx.author)

            server_name = ctx.options.name
            if server_name is None:
                game_server = self.__game_servers[0]
            else:
                game_server = next(
                    x for x in self.__game_servers if x.name() == server_name
                )

            title = get_embed_title(game_server)

            user = str(ctx.author)
            if user not in self.__configuration.privileged_users:
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

            game_server.restart()

        @self.__bot.command
        @lightbulb.option(
            name="name",
            description="States server to which command will be applied",
            choices=self.__game_server_names,
            required=False,
        )
        @lightbulb.command(
            name="backup",
            description="Creates backup of games server files and uploads them to storage.",
        )
        @lightbulb.implements(lightbulb.SlashCommand)
        async def backup(ctx) -> None:
            logging.debug("Called 'backup' by '%s'.", ctx.author)

            server_name = ctx.options.name
            if server_name is None:
                game_server = self.__game_servers[0]
            else:
                game_server = next(
                    x for x in self.__game_servers if x.name() == server_name
                )

            title = get_embed_title(game_server)

            user = str(ctx.author)
            if user not in self.__configuration.privileged_users:
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

            if game_server.create_backup():
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

    def activate(self) -> bool:
        try:
            self.__bot.run()
            return True
        except Exception as exception:
            logging.exception(exception)
            return False

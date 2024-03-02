#!/usr/bin/env python

import logging
import typing
from datetime import date, datetime
from typing import List

import hikari
import lightbulb
from hikari.api import MessageActionRowBuilder
from lightbulb.ext import tasks

from nidibot.bots.bot_base import (
    BackupDescription,
    BotBase,
    BotConfiguration,
    BotForwardMessage,
)
from nidibot.server_provider.game_server import GameServer


class DiscordBot(BotBase):
    def __init__(self, configuration: BotConfiguration, game_servers: List[GameServer]):
        super().__init__(configuration=configuration, game_servers=game_servers)

        self.__bot = lightbulb.BotApp(token=self._configuration.token)
        tasks.load(self.__bot)

        self.__color_green = 0x37CB78
        self.__color_orange = 0xE67E22
        self.__color_red = 0xE64A42

        @self.__bot.listen(hikari.StartedEvent)
        async def on_started(_) -> None:
            logging.info("Discord bot started and connected.")

        @self.__bot.command
        @lightbulb.option(
            name="name",
            description="States server to which command will be applied",
            choices=self._game_server_names,
            required=False,
        )
        @lightbulb.command(
            name="status",
            description="Provides extended information about game server status.",
        )
        @lightbulb.implements(lightbulb.SlashCommand)
        async def status(ctx) -> None:
            if (
                len(self._configuration.allowed_channels) > 0
                and str(ctx.channel_id) not in self._configuration.allowed_channels
            ):
                logging.error(
                    "Called 'status' by '%s' in not allowed channel '%s'.",
                    ctx.author,
                    ctx.channel_id,
                )
                return

            logging.debug("Called 'status' by '%s'.", ctx.author)

            game_server = self._get_game_server(ctx.options.name)
            server_status = game_server.status()

            title = self._get_response_title(game_server)

            if server_status.status == "online":
                status_smiley = ":white_check_mark:"
                status_color = hikari.colors.Color(self.__color_green)
            elif server_status.status == "offline":
                status_smiley = ":no_entry:"
                status_color = hikari.colors.Color(self.__color_red)
            elif server_status.status == "restarting":
                status_smiley = ":warning:"
                status_color = hikari.colors.Color(self.__color_orange)
            else:
                status_smiley = ":interrobang:"
                status_color = hikari.colors.Color(self.__color_orange)

            embed = hikari.Embed(
                title=title,
                color=status_color,
            )

            embed.add_field(
                name="Address:", value=f"`{server_status.address}`", inline=True
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
            choices=self._game_server_names,
            required=False,
        )
        @lightbulb.command(
            name="start",
            description="Starts server if it is offline, restarts server if it is online.",
        )
        @lightbulb.implements(lightbulb.SlashCommand)
        async def start(ctx) -> None:
            if (
                len(self._configuration.allowed_channels) > 0
                and str(ctx.channel_id) not in self._configuration.allowed_channels
            ):
                logging.error(
                    "Called 'start' by '%s' in not allowed channel '%s'.",
                    ctx.author,
                    ctx.channel_id,
                )
                return

            logging.debug("Called 'start' by '%s'.", ctx.author)

            game_server = self._get_game_server(ctx.options.name)
            title = self._get_response_title(game_server)

            user = str(ctx.author)
            if user not in self._configuration.privileged_users:
                embed = hikari.Embed(
                    title=title,
                    description="Sorry but you don't have rights to call this command! :liar:",
                    color=hikari.colors.Color(self.__color_red),
                )

                await ctx.respond(embed=embed)
                return

            embed = hikari.Embed(
                title=title,
                description=":warning: Starting server!",
                color=hikari.colors.Color(self.__color_red),
            )
            await ctx.respond(embed=embed)

            game_server.start()

        @self.__bot.command
        @lightbulb.option(
            name="name",
            description="States server to which command will be applied",
            choices=self._game_server_names,
            required=False,
        )
        @lightbulb.command(
            name="stop",
            description="Stops server if it is online.",
        )
        @lightbulb.implements(lightbulb.SlashCommand)
        async def stop(ctx) -> None:
            if (
                len(self._configuration.allowed_channels) > 0
                and str(ctx.channel_id) not in self._configuration.allowed_channels
            ):
                logging.error(
                    "Called 'stop' by '%s' in not allowed channel '%s'.",
                    ctx.author,
                    ctx.channel_id,
                )
                return

            logging.debug("Called 'stop' by '%s'.", ctx.author)

            game_server = self._get_game_server(ctx.options.name)
            title = self._get_response_title(game_server)

            user = str(ctx.author)
            if user not in self._configuration.privileged_users:
                embed = hikari.Embed(
                    title=title,
                    description="Sorry but you don't have rights to call this command! :liar:",
                    color=hikari.colors.Color(self.__color_red),
                )

                await ctx.respond(embed=embed)
                return

            embed = hikari.Embed(
                title=title,
                description=":warning: Stopping server!",
                color=hikari.colors.Color(self.__color_red),
            )
            await ctx.respond(embed=embed)

            game_server.stop()

        @self.__bot.command
        @lightbulb.option(
            name="name",
            description="States server to which command will be applied",
            choices=self._game_server_names,
            required=False,
        )
        @lightbulb.command(
            name="restart",
            description="Restarts server if it is online, starts server if it is offline.",
        )
        @lightbulb.implements(lightbulb.SlashCommand)
        async def restart(ctx) -> None:
            if (
                len(self._configuration.allowed_channels) > 0
                and str(ctx.channel_id) not in self._configuration.allowed_channels
            ):
                logging.error(
                    "Called 'restart' by '%s' in not allowed channel '%s'.",
                    ctx.author,
                    ctx.channel_id,
                )
                return

            logging.debug("Called 'restart' by '%s'.", ctx.author)

            game_server = self._get_game_server(ctx.options.name)
            title = self._get_response_title(game_server)

            user = str(ctx.author)
            if user not in self._configuration.privileged_users:
                embed = hikari.Embed(
                    title=title,
                    description="Sorry but you don't have rights to call this command! :liar:",
                    color=hikari.colors.Color(self.__color_red),
                )

                await ctx.respond(embed=embed)
                return

            embed = hikari.Embed(
                title=title,
                description=":warning: Restarting server!",
                color=hikari.colors.Color(self.__color_red),
            )
            await ctx.respond(embed=embed)

            game_server.restart()

        @self.__bot.command
        @lightbulb.option(
            name="name",
            description="States server to which command will be applied",
            choices=self._game_server_names,
            required=False,
        )
        @lightbulb.command(
            name="backup_create",
            description="Creates backup of game server files and uploads them to storage.",
        )
        @lightbulb.implements(lightbulb.SlashCommand)
        async def backup_create(ctx) -> None:
            if (
                len(self._configuration.allowed_channels) > 0
                and str(ctx.channel_id) not in self._configuration.allowed_channels
            ):
                logging.error(
                    "Called 'backup_create' by '%s' in not allowed channel '%s'.",
                    ctx.author,
                    ctx.channel_id,
                )
                return

            logging.debug("Called 'backup_create' by '%s'.", ctx.author)

            game_server = self._get_game_server(ctx.options.name)
            title = self._get_response_title(game_server)

            user = str(ctx.author)
            if user not in self._configuration.privileged_users:
                embed = hikari.Embed(
                    title=title,
                    description="Sorry but you don't have rights to call this command! :liar:",
                    color=hikari.colors.Color(self.__color_red),
                )

                await ctx.respond(embed=embed)
                return

            embed = hikari.Embed(
                title=title,
                description=":warning: Started creating backup of the server, please wait.",
                color=hikari.colors.Color(self.__color_orange),
            )
            await ctx.respond(embed=embed)

            if game_server.create_backup():
                embed = hikari.Embed(
                    title=title,
                    description=":white_check_mark: Backup was created successfully!",
                    color=hikari.colors.Color(self.__color_green),
                )
            else:
                embed = hikari.Embed(
                    title=title,
                    description=":no_entry: Backup creation failed, please check bot logs!",
                    color=hikari.colors.Color(self.__color_red),
                )

            await ctx.respond(embed=embed)

        async def create_backup_buttons(
            bot: lightbulb.BotApp, backups: List[BackupDescription]
        ) -> typing.Iterable[MessageActionRowBuilder]:

            rows: typing.List[MessageActionRowBuilder] = []
            row = bot.rest.build_message_action_row()

            buttons_added_to_row = 0
            for backup_description in backups:
                if buttons_added_to_row % 5 == 0 and buttons_added_to_row != 0:
                    rows.append(row)
                    row = bot.rest.build_message_action_row()
                    buttons_added_to_row = 0

                row.add_interactive_button(
                    hikari.ButtonStyle.SECONDARY,
                    backup_description.filepath,
                    label=backup_description.readable_name,
                )

                buttons_added_to_row += 1

            rows.append(row)

            return rows

        async def handle_backup_restore(
            ctx,
            message: hikari.Message,
            title: str,
            backups: List[BackupDescription],
            game_server: GameServer,
        ) -> None:

            with ctx.bot.stream(hikari.InteractionCreateEvent, 120).filter(
                lambda e: (
                    isinstance(e.interaction, hikari.ComponentInteraction)
                    and e.interaction.user == ctx.author
                    and e.interaction.message == message
                )
            ) as stream:
                async for event in stream:
                    interaction: hikari.ComponentInteraction = event.interaction  # type: ignore
                    filename = interaction.custom_id
                    backup_description = next(
                        (x for x in backups if x.filepath == filename), None
                    )
                    if backup_description is None:
                        return

                    embed = hikari.Embed(
                        title=title,
                        color=hikari.colors.Color(self.__color_orange),
                        description=f"Selected backup: {backup_description.readable_name}",
                    )

                    try:
                        await interaction.create_initial_response(
                            hikari.ResponseType.MESSAGE_UPDATE,
                            embed=embed,
                            components=[],
                        )
                    except hikari.NotFoundError:
                        await interaction.edit_initial_response(
                            embed=embed, components=[]
                        )

                    embed = hikari.Embed(
                        title=title,
                        description=f":warning: Started restoring backup from {backup_description.readable_name}, please wait.",
                        color=hikari.colors.Color(self.__color_orange),
                    )
                    await ctx.respond(embed=embed)

                    if game_server.restore_backup(backup_description.filepath):
                        embed = hikari.Embed(
                            title=title,
                            description=f":white_check_mark: Backup from {backup_description.readable_name} was restored successfully!",
                            color=hikari.colors.Color(self.__color_green),
                        )
                    else:
                        embed = hikari.Embed(
                            title=title,
                            description=f":no_entry: Restoring backup from {backup_description.readable_name} failed, please check bot logs!",
                            color=hikari.colors.Color(self.__color_red),
                        )

                    await ctx.respond(embed=embed)

        @self.__bot.command
        @lightbulb.option(
            name="name",
            description="States server to which command will be applied",
            choices=self._game_server_names,
            required=False,
        )
        @lightbulb.command(
            name="backup_restore",
            description="Restores specific backup on a game server.",
        )
        @lightbulb.implements(lightbulb.SlashCommand)
        async def backup_restore(ctx) -> None:
            if (
                len(self._configuration.allowed_channels) > 0
                and str(ctx.channel_id) not in self._configuration.allowed_channels
            ):
                logging.error(
                    "Called 'backup_restore' by '%s' in not allowed channel '%s'.",
                    ctx.author,
                    ctx.channel_id,
                )
                return

            logging.debug("Called 'backup_restore' by '%s'.", ctx.author)

            game_server = self._get_game_server(ctx.options.name)
            title = self._get_response_title(game_server)

            user = str(ctx.author)
            if user not in self._configuration.privileged_users:
                embed = hikari.Embed(
                    title=title,
                    description="Sorry but you don't have rights to call this command! :liar:",
                    color=hikari.colors.Color(self.__color_red),
                )

                await ctx.respond(embed=embed)
                return

            backups = game_server.list_backups()
            if len(backups) > 0:
                self._backups[ctx.options.name] = backups

                embed = hikari.Embed(
                    title=title,
                    description="Select a backup:",
                    color=hikari.colors.Color(self.__color_orange),
                )

                backup_buttons = await create_backup_buttons(ctx.bot, backups)
                response = await ctx.respond(
                    embed=embed,
                    components=backup_buttons,
                )

                message = await response.message()
                await handle_backup_restore(ctx, message, title, backups, game_server)

            else:
                logging.warning("No backups available!")
                embed = hikari.Embed(
                    title=title,
                    description=":no_entry: No backups available!",
                    color=hikari.colors.Color(self.__color_red),
                )

                await ctx.respond(embed=embed)

        @self.__bot.command
        @lightbulb.option(
            name="name",
            description="States server to which command will be applied",
            choices=self._game_server_names,
            required=False,
        )
        @lightbulb.command(
            name="backup_list",
            description="Lists available backups of specific game server.",
        )
        @lightbulb.implements(lightbulb.SlashCommand)
        async def backup_list(ctx) -> None:
            if (
                len(self._configuration.allowed_channels) > 0
                and str(ctx.channel_id) not in self._configuration.allowed_channels
            ):
                logging.error(
                    "Called 'backup_list' by '%s' in not allowed channel '%s'.",
                    ctx.author,
                    ctx.channel_id,
                )
                return

            logging.debug("Called 'backup_list' by '%s'.", ctx.author)

            game_server = self._get_game_server(ctx.options.name)
            title = self._get_response_title(game_server)

            self._backups[ctx.options.name] = game_server.list_backups()

            backup_sum_message = "**Available backups:**\n"
            for backup in self._backups[ctx.options.name]:
                backup_sum_message += f"* {backup.readable_name}\n"

            embed = hikari.Embed(
                title=title,
                description=backup_sum_message,
                color=hikari.colors.Color(self.__color_orange),
            )
            await ctx.respond(embed=embed)

        @tasks.task(s=self._configuration.notify_polling_seconds, auto_start=True)
        async def notify_loop():
            local_notify_messages: List[BotForwardMessage] = []
            with self._notify_mutex:
                local_notify_messages = self._notify_messages
                self._notify_messages = []

            if len(local_notify_messages) == 0:
                return

            connected_channels: list = []
            connected_guilds = await self.__bot.rest.fetch_my_guilds()
            for guild in connected_guilds:
                channels = await self.__bot.rest.fetch_guild_channels(guild)
                for channel in channels:
                    if channel.type == hikari.ChannelType.GUILD_TEXT:
                        connected_channels.append(channel)

            for notify_message in local_notify_messages:
                embed = hikari.Embed(
                    title=notify_message.title,
                    description=f":warning: {notify_message.message}",
                    color=hikari.colors.Color(self.__color_orange),
                )

                for channel in connected_channels:
                    try:
                        await self.__bot.rest.create_message(
                            channel=channel.id, embed=embed
                        )
                    except hikari.errors.ForbiddenError as exception:
                        logging.exception(exception)

    def notify(self, title: str, message: str) -> None:
        with self._notify_mutex:
            notify_message: BotForwardMessage = BotForwardMessage()
            notify_message.title = title
            notify_message.message = message
            self._notify_messages.append(notify_message)

    def start(self) -> None:
        try:
            self.__bot.run()
        except Exception as exception:
            logging.exception(exception)

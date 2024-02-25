#!/usr/bin/env python

import logging
from datetime import date, datetime
from itertools import chain
from typing import List, Sequence

from telegram import BotCommand, ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.helpers import escape_markdown

from nidibot.bots.bot_interface import BotConfiguration, BotForwardMessage, BotInterface
from nidibot.server_provider.game_server import GameServer


class TelegramBot(BotInterface):
    def __init__(self, configuration: BotConfiguration, game_servers: List[GameServer]):
        super().__init__(configuration=configuration, game_servers=game_servers)

        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("telegram").setLevel(logging.WARNING)
        logging.getLogger("telegram.constants").setLevel(logging.WARNING)
        logging.getLogger("telegram.ext").setLevel(logging.WARNING)
        logging.getLogger("telegram.helpers").setLevel(logging.WARNING)

        self.__bot = (
            Application.builder()
            .token(self._configuration.token)
            .post_init(self.__publish_commands)
            .build()
        )

        self.__bot.add_handler(CommandHandler("status", self.__status))
        self.__bot.add_handler(CommandHandler("start", self.__start))
        self.__bot.add_handler(CommandHandler("stop", self.__stop))
        self.__bot.add_handler(CommandHandler("restart", self.__restart))
        self.__bot.add_handler(CommandHandler("backup", self.__backup))
        self.__bot.add_handler(CommandHandler("backup", self.__backup))

    def __concatenate_sequences(
        self, sequence1: Sequence, sequence2: Sequence
    ) -> Sequence:
        sequence_type = type(sequence1)
        return sequence_type(chain(sequence1, sequence2))  # type: ignore

    async def __publish_commands(self, application: Application) -> None:
        commands = [
            BotCommand(
                "status", "Provides extended information about game server status."
            ),
            BotCommand(
                "start",
                "Starts server if it is offline, restarts server if it is online.",
            ),
            BotCommand("stop", "Stops server if it is online."),
            BotCommand(
                "restart",
                "Restarts server if it is online, starts server if it is offline.",
            ),
            BotCommand(
                "backup",
                "Creates backup of games server files and uploads them to storage.",
            ),
        ]
        await application.bot.set_my_commands(commands)

    async def __status(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        args = []
        if context.args is not None:
            args = context.args

        if update.effective_user is None or update.effective_user.username is None:
            logging.critical("No username in incoming message!")
            return

        username = update.effective_user.username

        if update.effective_message is None or update.effective_message.chat_id is None:
            logging.critical("No chat_id in incoming message!")
            return

        chat_id = update.effective_message.chat_id

        logging.debug("Called 'status' by '%s'.", username)

        if len(args) == 0:
            reply_keyboard = [[]]  # type: ignore
            for game_server in self._game_server_names:
                sub_keyboard = [[f"/status {game_server}"]]
                reply_keyboard = self.__concatenate_sequences(reply_keyboard, sub_keyboard)  # type: ignore

            markup = ReplyKeyboardMarkup(
                reply_keyboard,
                one_time_keyboard=False,
                resize_keyboard=True,
            )

            await context.bot.send_message(
                chat_id,
                text=r"Please select server\!",
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=markup,
            )
            return

        game_server = self._get_game_server(args[0])
        server_status = game_server.status()

        if server_status.status == "online":
            status_smiley = "\u2705"
        elif server_status.status == "offline":
            status_smiley = "\u26D4"
        elif server_status.status == "restarting":
            status_smiley = "\u26A0"
        else:
            status_smiley = "\u203D"

        if server_status.update_available:
            update_smiley = "\u26A0"
            update_text = "yes"
        else:
            update_smiley = "\u2705"
            update_text = "no"

        date_time = server_status.available_until.split(" ")
        date_parts = date_time[0].split("-")
        d0 = date(datetime.now().year, datetime.now().month, datetime.now().day)
        d1 = date(int(date_parts[0]), int(date_parts[1]), int(date_parts[2]))
        delta = d1 - d0
        days_left = f"({delta.days} days left)"

        server_name = self._get_response_title(game_server=game_server)
        response_text = f"__*{escape_markdown(server_name, version=2)}*__\n\n"
        response_text += (
            f"*Address:* {escape_markdown(server_status.address, version=2)}\n"
        )
        response_text += f"*Status:* {status_smiley} {server_status.status}\n"
        response_text += f"*Players:* {server_status.players_connected} / {server_status.players_limit}\n"
        response_text += f"*Available until:* {escape_markdown(server_status.available_until, version=2)} {escape_markdown(days_left, version=2)}\n"
        response_text += f"*Update available:* {update_smiley} {update_text}"

        await context.bot.send_message(
            chat_id,
            text=response_text,
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=ReplyKeyboardRemove(),
        )

    async def __start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        args = []
        if context.args is not None:
            args = context.args

        if update.effective_user is None or update.effective_user.username is None:
            logging.critical("No username in incoming message!")
            return

        username = update.effective_user.username

        if update.effective_message is None or update.effective_message.chat_id is None:
            logging.critical("No chat_id in incoming message!")
            return

        chat_id = update.effective_message.chat_id

        logging.debug("Called 'start' by '%s'.", username)

        if len(args) == 0:
            reply_keyboard = [[]]  # type: ignore
            for game_server in self._game_server_names:
                sub_keyboard = [[f"/start {game_server}"]]
                reply_keyboard = self.__concatenate_sequences(reply_keyboard, sub_keyboard)  # type: ignore

            markup = ReplyKeyboardMarkup(
                reply_keyboard,
                one_time_keyboard=False,
                resize_keyboard=True,
            )

            await context.bot.send_message(
                chat_id,
                text=r"Please select server\!",
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=markup,
            )
            return

        game_server = self._get_game_server(args[0])

        if username not in self._configuration.privileged_users:
            await context.bot.send_message(
                chat_id,
                text="Sorry but you don't have rights to call this command\! \u1F925",
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=ReplyKeyboardRemove(),
            )
            return

        await context.bot.send_message(
            chat_id,
            text="\u26A0 Starting server\! \u26A0",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=ReplyKeyboardRemove(),
        )

        game_server.start()

    async def __stop(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        args = []
        if context.args is not None:
            args = context.args

        if update.effective_user is None or update.effective_user.username is None:
            logging.critical("No username in incoming message!")
            return

        username = update.effective_user.username

        if update.effective_message is None or update.effective_message.chat_id is None:
            logging.critical("No chat_id in incoming message!")
            return

        chat_id = update.effective_message.chat_id

        logging.debug("Called 'stop' by '%s'.", username)

        if len(args) == 0:
            reply_keyboard = [[]]  # type: ignore
            for game_server in self._game_server_names:
                sub_keyboard = [[f"/stop {game_server}"]]
                reply_keyboard = self.__concatenate_sequences(reply_keyboard, sub_keyboard)  # type: ignore

            markup = ReplyKeyboardMarkup(
                reply_keyboard,
                one_time_keyboard=False,
                resize_keyboard=True,
            )

            await context.bot.send_message(
                chat_id,
                text=r"Please select server\!",
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=markup,
            )
            return

        game_server = self._get_game_server(args[0])

        if username not in self._configuration.privileged_users:
            await context.bot.send_message(
                chat_id,
                text="Sorry but you don't have rights to call this command\! \u1F925",
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=ReplyKeyboardRemove(),
            )
            return

        await context.bot.send_message(
            chat_id,
            text="\u26A0 Stopping server\! \u26A0",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=ReplyKeyboardRemove(),
        )

        game_server.stop()

    async def __restart(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        args = []
        if context.args is not None:
            args = context.args

        if update.effective_user is None or update.effective_user.username is None:
            logging.critical("No username in incoming message!")
            return

        username = update.effective_user.username

        if update.effective_message is None or update.effective_message.chat_id is None:
            logging.critical("No chat_id in incoming message!")
            return

        chat_id = update.effective_message.chat_id

        logging.debug("Called 'restart' by '%s'.", username)

        if len(args) == 0:
            reply_keyboard = [[]]  # type: ignore
            for game_server in self._game_server_names:
                sub_keyboard = [[f"/restart {game_server}"]]
                reply_keyboard = self.__concatenate_sequences(reply_keyboard, sub_keyboard)  # type: ignore

            markup = ReplyKeyboardMarkup(
                reply_keyboard,
                one_time_keyboard=False,
                resize_keyboard=True,
            )

            await context.bot.send_message(
                chat_id,
                text=r"Please select server\!",
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=markup,
            )
            return

        game_server = self._get_game_server(args[0])

        if username not in self._configuration.privileged_users:
            await context.bot.send_message(
                chat_id,
                text="Sorry but you don't have rights to call this command\! \u1F925",
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=ReplyKeyboardRemove(),
            )
            return

        await context.bot.send_message(
            chat_id,
            text="\u26A0 Restarting server\! \u26A0",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=ReplyKeyboardRemove(),
        )

        game_server.restart()

    async def __backup(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        args = []
        if context.args is not None:
            args = context.args

        if update.effective_user is None or update.effective_user.username is None:
            logging.critical("No username in incoming message!")
            return

        username = update.effective_user.username

        if update.effective_message is None or update.effective_message.chat_id is None:
            logging.critical("No chat_id in incoming message!")
            return

        chat_id = update.effective_message.chat_id

        logging.debug("Called 'backup' by '%s'.", username)

        if len(args) == 0:
            reply_keyboard = [[]]  # type: ignore
            for game_server in self._game_server_names:
                sub_keyboard = [[f"/backup {game_server}"]]
                reply_keyboard = self.__concatenate_sequences(reply_keyboard, sub_keyboard)  # type: ignore

            markup = ReplyKeyboardMarkup(
                reply_keyboard,
                one_time_keyboard=False,
                resize_keyboard=True,
            )

            await context.bot.send_message(
                chat_id,
                text=r"Please select server\!",
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=markup,
            )
            return

        game_server = self._get_game_server(args[0])

        if username not in self._configuration.privileged_users:
            await context.bot.send_message(
                chat_id,
                text="Sorry but you don't have rights to call this command\! \u1F925",
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=ReplyKeyboardRemove(),
            )
            return

        await context.bot.send_message(
            chat_id,
            text="\u26A0 Started creating backup of the server\, please wait\. \u26A0",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=ReplyKeyboardRemove(),
        )

        if game_server.create_backup():
            await context.bot.send_message(
                chat_id,
                text="\u2705 Backup was created successfully\!",
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=ReplyKeyboardRemove(),
            )
        else:
            await context.bot.send_message(
                chat_id,
                text="\u26D4 Backup creation failed\, please check bot logs\!",
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=ReplyKeyboardRemove(),
            )

    def notify(self, title: str, message: str) -> None:
        with self._notify_mutex:
            notify_message: BotForwardMessage = BotForwardMessage()
            notify_message.title = title
            notify_message.message = message
            self._notify_messages.append(notify_message)

    def start(self) -> None:
        try:
            self.__bot.run_polling(allowed_updates=Update.ALL_TYPES, close_loop=False)
        except Exception as exception:
            logging.exception(exception)

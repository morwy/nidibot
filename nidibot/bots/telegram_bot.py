#!/usr/bin/env python

"""
nidibot.bots.telegram_bot
~~~~~~~~~~~~~~~~~~~~~~~~

Components for managing Telegram bot.

"""

import asyncio
import logging
from datetime import date, datetime
from itertools import chain
from typing import List, Sequence

import nest_asyncio  # type: ignore
from telegram import BotCommand, ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
)
from telegram.helpers import escape_markdown

from nidibot.bots.bot_base import BotBase, BotConfiguration, BotForwardMessage
from nidibot.server_provider.game_server import GameServer


class TelegramBot(BotBase):
    """
    A class for managing Telegram bot.
    """

    def __init__(self, configuration: BotConfiguration, game_servers: List[GameServer]):
        super().__init__(configuration=configuration, game_servers=game_servers)

        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("httpcore").setLevel(logging.WARNING)
        logging.getLogger("telegram").setLevel(logging.WARNING)

        self.__bot = (
            Application.builder()
            .token(self._configuration.token)
            .post_init(self.__publish_commands)
            .build()
        )

        (
            self.__PROCESS_OPERATION,
            self.__BACKUP_RESTORE_SERVER,
            self.__BACKUP_RESTORE_FILEPATH,
            self.__CONVERSATION_END,
        ) = range(4)

        common_command_handler = ConversationHandler(
            allow_reentry=True,
            entry_points=[
                CommandHandler(
                    [
                        "status",
                        "start",
                        "stop",
                        "restart",
                        "backup_create",
                        "backup_list",
                    ],
                    self.__select_server,
                )
            ],
            states={
                self.__PROCESS_OPERATION: [
                    MessageHandler(
                        filters=None,
                        callback=self.__process_operation,
                    )
                ],
                self.__CONVERSATION_END: [
                    MessageHandler(filters=None, callback=self.__conversation_end)
                ],
            },
            fallbacks=[MessageHandler(filters=None, callback=self.__conversation_end)],
        )
        self.__bot.add_handler(common_command_handler)

        backup_restore_handler = ConversationHandler(
            allow_reentry=True,
            entry_points=[CommandHandler("backup_restore", self.__backup_restore)],
            states={
                self.__BACKUP_RESTORE_SERVER: [
                    MessageHandler(
                        filters=None,
                        callback=self.__backup_restore_server,
                    )
                ],
                self.__BACKUP_RESTORE_FILEPATH: [
                    MessageHandler(
                        filters=None,
                        callback=self.__backup_restore_filepath,
                    )
                ],
                self.__CONVERSATION_END: [
                    MessageHandler(filters=None, callback=self.__conversation_end)
                ],
            },
            fallbacks=[MessageHandler(filters=None, callback=self.__conversation_end)],
        )
        self.__bot.add_handler(backup_restore_handler)

        job_queue = self.__bot.job_queue
        job_queue.run_repeating(  # type: ignore
            self.__notify_loop,
            interval=self._configuration.notify_polling_seconds,
            first=0,
        )

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
                "backup_create",
                "Creates backup of games server files and uploads them to storage.",
            ),
            BotCommand(
                "backup_list",
                "Lists available backups of specific game server.",
            ),
            BotCommand(
                "backup_restore",
                "Restores specific backup on a game server.",
            ),
        ]
        await application.bot.set_my_commands(commands)

    async def __select_server(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        if update.effective_user is None or update.effective_user.username is None:
            logging.critical("No username in incoming message!")
            return self.__CONVERSATION_END

        username = update.effective_user.username

        if update.message is None or update.message.text is None:
            logging.critical("No chat_id in incoming message!")
            return self.__CONVERSATION_END

        if (
            update.effective_message is None
            or update.effective_message.chat_id is None
            or update.effective_message.text is None
        ):
            logging.critical("No chat_id in incoming message!")
            return self.__CONVERSATION_END

        chat_id = update.effective_message.chat_id
        message_text = update.effective_message.text
        command = message_text.replace("/", "")[: message_text.find("@") - 1]

        if (
            len(self._configuration.allowed_channels) > 0
            and str(chat_id) not in self._configuration.allowed_channels
        ):
            logging.error(
                "Called '%s' by '%s' in not allowed channel '%s'.",
                command,
                username,
                chat_id,
            )
            return self.__CONVERSATION_END

        logging.debug("Called '%s' by '%s'.", command, username)

        if context.user_data is not None:
            context.user_data["command"] = command

        reply_keyboard = [[]]  # type: ignore
        for game_server in self._game_server_names:
            sub_keyboard = [[game_server]]
            reply_keyboard = self.__concatenate_sequences(reply_keyboard, sub_keyboard)  # type: ignore

        await update.message.reply_text(
            "Please select server:",
            reply_markup=ReplyKeyboardMarkup(
                reply_keyboard,
                one_time_keyboard=True,
                resize_keyboard=True,
            ),
        )

        return self.__PROCESS_OPERATION

    async def __process_operation(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        if update.message is None or update.message.from_user is None:
            logging.critical("No username in incoming message!")
            return self.__CONVERSATION_END

        username = update.message.from_user.username

        if update.message is None or update.message.text is None:
            logging.critical("No text in incoming message!")
            return self.__CONVERSATION_END

        server_name = update.message.text

        command = ""
        if context.user_data is not None:
            command = context.user_data["command"]

        if not command:
            return self.__CONVERSATION_END

        if update.effective_message is None or update.effective_message.chat_id is None:
            logging.critical("No chat_id in incoming message!")
            return self.__CONVERSATION_END

        chat_id = update.effective_message.chat_id

        logging.debug(
            "'%s' selected server '%s' for command '%s'.",
            username,
            server_name,
            command,
        )

        game_server = next(
            (x for x in self._game_servers if x.name() == server_name), None
        )
        if game_server is None:
            return self.__CONVERSATION_END

        #
        # Process un-privileged commands.
        #
        if command == "status":
            server_status = game_server.status()

            if server_status.status == "online":
                status_emoji = self._emoji_ok
            elif server_status.status == "offline":
                status_emoji = self._emoji_bad
            elif server_status.status == "restarting":
                status_emoji = self._emoji_attention
            else:
                status_emoji = self._emoji_unknown

            if server_status.update_available:
                update_emoji = self._emoji_attention
                update_text = "yes"
            else:
                update_emoji = self._emoji_ok
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
            response_text += f"*Status:* {status_emoji} {server_status.status}\n"
            response_text += f"*Players:* {server_status.players_connected} / {server_status.players_limit}\n"
            response_text += f"*Available until:* {escape_markdown(server_status.available_until, version=2)} {escape_markdown(days_left, version=2)}\n"
            response_text += f"*Update available:* {update_emoji} {update_text}"

            await context.bot.send_message(
                chat_id,
                text=response_text,
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=ReplyKeyboardRemove(),
            )

            return self.__CONVERSATION_END

        if command == "backup_list":
            self._backups[server_name] = game_server.list_backups()

            backup_sum_message = "Available backups:\n"
            for backup in self._backups[server_name]:
                backup_sum_message += (
                    f"\\- {escape_markdown(backup.readable_name, version=2)}\n"
                )

            await context.bot.send_message(
                chat_id,
                text=backup_sum_message,
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=ReplyKeyboardRemove(),
            )
            return self.__CONVERSATION_END

        #
        # Process privileged commands.
        #
        if username not in self._configuration.privileged_users:
            await update.message.reply_text(
                f"Sorry but you don't have rights to call this command\\! {self._emoji_no_access}",
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=ReplyKeyboardRemove(),
            )
            return self.__CONVERSATION_END

        if command == "start":
            await context.bot.send_message(
                chat_id,
                text=f"{self._emoji_attention} Starting server\\!",
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=ReplyKeyboardRemove(),
            )

            game_server.start()

        elif command == "stop":
            await context.bot.send_message(
                chat_id,
                text=f"{self._emoji_attention} Stopping server\\!",
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=ReplyKeyboardRemove(),
            )

            game_server.stop()

        elif command == "restart":
            await context.bot.send_message(
                chat_id,
                text=f"{self._emoji_attention} Restarting server\\!",
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=ReplyKeyboardRemove(),
            )

            game_server.restart()

        elif command == "backup_create":
            await context.bot.send_message(
                chat_id,
                text=f"{self._emoji_attention} Started creating backup\\, please wait\\.",
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=ReplyKeyboardRemove(),
            )

            if game_server.create_backup():
                await context.bot.send_message(
                    chat_id,
                    text=f"{self._emoji_ok} Backup was created successfully\\!",
                    parse_mode=ParseMode.MARKDOWN_V2,
                    reply_markup=ReplyKeyboardRemove(),
                )
            else:
                await context.bot.send_message(
                    chat_id,
                    text=f"{self._emoji_bad} Backup creation failed\\, please check bot logs\\!",
                    parse_mode=ParseMode.MARKDOWN_V2,
                    reply_markup=ReplyKeyboardRemove(),
                )

        return self.__CONVERSATION_END

    async def __backup_restore(
        self, update: Update, _: ContextTypes.DEFAULT_TYPE
    ) -> int:
        if update.effective_user is None or update.effective_user.username is None:
            logging.critical("No username in incoming message!")
            return self.__CONVERSATION_END

        username = update.effective_user.username

        if update.message is None or update.message.text is None:
            logging.critical("No chat_id in incoming message!")
            return self.__CONVERSATION_END

        if update.effective_message is None or update.effective_message.chat_id is None:
            logging.critical("No chat_id in incoming message!")
            return self.__CONVERSATION_END

        chat_id = update.effective_message.chat_id

        if (
            len(self._configuration.allowed_channels) > 0
            and str(chat_id) not in self._configuration.allowed_channels
        ):
            logging.error(
                "Called 'backup_restore' by '%s' in not allowed channel '%s'.",
                username,
                chat_id,
            )
            return self.__CONVERSATION_END

        logging.debug("Called 'backup_restore' by '%s'.", username)

        if username not in self._configuration.privileged_users:
            await update.message.reply_text(
                f"Sorry but you don't have rights to call this command\\! {self._emoji_no_access}",
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=ReplyKeyboardRemove(),
            )
            return self.__CONVERSATION_END

        reply_keyboard = [[]]  # type: ignore
        for game_server in self._game_server_names:
            sub_keyboard = [[game_server]]
            reply_keyboard = self.__concatenate_sequences(reply_keyboard, sub_keyboard)  # type: ignore

        await update.message.reply_text(
            "Please select server:",
            reply_markup=ReplyKeyboardMarkup(
                reply_keyboard,
                one_time_keyboard=True,
                resize_keyboard=True,
            ),
        )

        return self.__BACKUP_RESTORE_SERVER

    async def __backup_restore_server(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        if update.message is None or update.message.from_user is None:
            logging.critical("No username in incoming message!")
            return self.__CONVERSATION_END

        username = update.message.from_user.username

        if update.message is None or update.message.text is None:
            logging.critical("No text in incoming message!")
            return self.__CONVERSATION_END

        server_name = update.message.text

        if context.user_data is not None:
            context.user_data["game_server"] = server_name

        logging.debug("'%s' selected server '%s'.", username, server_name)

        game_server = next(
            (x for x in self._game_servers if x.name() == server_name), None
        )
        if game_server is None:
            return self.__CONVERSATION_END

        backups = game_server.list_backups()
        if len(backups) > 0:
            reply_keyboard = [[]]  # type: ignore
            for backup_description in backups:
                sub_keyboard = [[backup_description.readable_name]]
                reply_keyboard = self.__concatenate_sequences(reply_keyboard, sub_keyboard)  # type: ignore

            await update.message.reply_text(
                "Please select backup:",
                reply_markup=ReplyKeyboardMarkup(
                    reply_keyboard,
                    one_time_keyboard=True,
                    resize_keyboard=True,
                ),
            )

            return self.__BACKUP_RESTORE_FILEPATH

        logging.warning("No backups available!")
        await update.message.reply_text(
            escape_markdown(
                text=f"{self._emoji_bad} No backups available!",
                version=2,
            ),
            reply_markup=ReplyKeyboardRemove(),
        )

        return self.__CONVERSATION_END

    async def __backup_restore_filepath(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        if update.message is None or update.message.from_user is None:
            logging.critical("No username in incoming message!")
            return self.__CONVERSATION_END

        username = update.message.from_user.username

        if update.message is None or update.message.text is None:
            logging.critical("No text in incoming message!")
            return self.__CONVERSATION_END

        backup_readable_name = update.message.text

        logging.debug("'%s' selected backup '%s'.", username, backup_readable_name)

        if context.user_data is None:
            return self.__CONVERSATION_END

        server_name = context.user_data["game_server"]
        game_server = next(
            (x for x in self._game_servers if x.name() == server_name),
            None,
        )
        if game_server is None:
            return self.__CONVERSATION_END

        backups = self._backups[server_name]
        if backups is None:
            return self.__CONVERSATION_END

        backup_description = next(
            (x for x in backups if x.readable_name == backup_readable_name), None
        )
        if backup_description is None:
            return self.__CONVERSATION_END

        escaped_backup_name = escape_markdown(
            backup_description.readable_name, version=2
        )
        await update.message.reply_text(
            text=f"{self._emoji_attention} Started restoring backup from {escaped_backup_name}\\, please wait\\.",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=ReplyKeyboardRemove(),
        )

        if game_server.restore_backup(backup_description.filepath):
            await update.message.reply_text(
                text=f"{self._emoji_ok} Backup from {escaped_backup_name} was restored successfully\\!",
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=ReplyKeyboardRemove(),
            )
        else:
            await update.message.reply_text(
                text=f"{self._emoji_bad} Restoring backup from {escaped_backup_name} failed\\, please check bot logs\\!",
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=ReplyKeyboardRemove(),
            )

        return ConversationHandler.END

    async def __conversation_end(
        self, _1: Update, _2: ContextTypes.DEFAULT_TYPE
    ) -> int:
        return ConversationHandler.END

    async def __notify_loop(self, context: ContextTypes.DEFAULT_TYPE) -> None:
        local_notify_messages: List[BotForwardMessage] = []
        with self._notify_mutex:
            local_notify_messages = self._notify_messages
            self._notify_messages = []

        if len(local_notify_messages) == 0:
            return

        for notify_message in local_notify_messages:
            for channel in self._configuration.allowed_channels:
                await context.bot.send_message(
                    channel,
                    text=f"__*{escape_markdown(text=notify_message.title, version=2)}*__"
                    f"\n{self._emoji_attention} {escape_markdown(text=notify_message.message, version=2)}",
                    parse_mode=ParseMode.MARKDOWN_V2,
                    reply_markup=ReplyKeyboardRemove(),
                )

    def notify(self, title: str, message: str) -> None:
        with self._notify_mutex:
            notify_message: BotForwardMessage = BotForwardMessage()
            notify_message.title = title
            notify_message.message = message
            self._notify_messages.append(notify_message)

    #
    # A bit of tricky solution to run python-telegram-bot in separate thread.
    #
    async def __start_bot(self) -> None:
        self.__bot.run_polling(
            allowed_updates=Update.ALL_TYPES,
            close_loop=False,
            stop_signals=None,
            drop_pending_updates=True,
        )

    def start(self) -> None:
        nest_asyncio.apply()

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.__start_bot())
            loop.close()

        except Exception as exception:
            logging.exception(exception)

#!/usr/bin/env python

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

        self.__bot.add_handler(CommandHandler("status", self.__status))
        self.__bot.add_handler(CommandHandler("start", self.__start))
        self.__bot.add_handler(CommandHandler("stop", self.__stop))
        self.__bot.add_handler(CommandHandler("restart", self.__restart))
        self.__bot.add_handler(CommandHandler("backup_create", self.__backup_create))
        self.__bot.add_handler(CommandHandler("backup_list", self.__backup_list))

        (
            self.__BACKUP_RESTORE_SERVER,
            self.__BACKUP_RESTORE_FILEPATH,
            self.__BACKUP_RESTORE_CANCEL,
        ) = range(3)

        conversation_handler = ConversationHandler(
            allow_reentry=True,
            entry_points=[CommandHandler("backup_restore", self.__backup_restore)],
            states={
                self.__BACKUP_RESTORE_SERVER: [
                    MessageHandler(
                        filters=None,
                        callback=self.__backup_restore_filepath,
                    )
                ],
                self.__BACKUP_RESTORE_FILEPATH: [
                    MessageHandler(
                        filters=None,
                        callback=self.__backup_restore_start,
                    )
                ],
                self.__BACKUP_RESTORE_CANCEL: [
                    CommandHandler("cancel", self.__backup_restore_cancel)
                ],
            },
            fallbacks=[CommandHandler("cancel", self.__backup_restore_cancel)],
        )
        self.__bot.add_handler(conversation_handler)

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

        if (
            len(self._configuration.allowed_channels) > 0
            and str(chat_id) not in self._configuration.allowed_channels
        ):
            logging.error(
                "Called 'status' by '%s' in not allowed channel '%s'.",
                username,
                chat_id,
            )
            return

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

        if (
            len(self._configuration.allowed_channels) > 0
            and str(chat_id) not in self._configuration.allowed_channels
        ):
            logging.error(
                "Called 'start' by '%s' in not allowed channel '%s'.",
                username,
                chat_id,
            )
            return

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
            text="\u26A0 Starting server\!",
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

        if (
            len(self._configuration.allowed_channels) > 0
            and str(chat_id) not in self._configuration.allowed_channels
        ):
            logging.error(
                "Called 'stop' by '%s' in not allowed channel '%s'.",
                username,
                chat_id,
            )
            return

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
            text="\u26A0 Stopping server\!",
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

        if (
            len(self._configuration.allowed_channels) > 0
            and str(chat_id) not in self._configuration.allowed_channels
        ):
            logging.error(
                "Called 'restart' by '%s' in not allowed channel '%s'.",
                username,
                chat_id,
            )
            return
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
            text="\u26A0 Restarting server\!",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=ReplyKeyboardRemove(),
        )

        game_server.restart()

    async def __backup_create(
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

        if (
            len(self._configuration.allowed_channels) > 0
            and str(chat_id) not in self._configuration.allowed_channels
        ):
            logging.error(
                "Called 'backup_create' by '%s' in not allowed channel '%s'.",
                username,
                chat_id,
            )
            return

        logging.debug("Called 'backup_create' by '%s'.", username)

        if len(args) == 0:
            reply_keyboard = [[]]  # type: ignore
            for game_server in self._game_server_names:
                sub_keyboard = [[f"/backup_create {game_server}"]]
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
            text="\u26A0 Started creating backup of the server\, please wait\.",
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

    async def __backup_restore(
        self, update: Update, _: ContextTypes.DEFAULT_TYPE
    ) -> int:
        if update.effective_user is None or update.effective_user.username is None:
            logging.critical("No username in incoming message!")
            return self.__BACKUP_RESTORE_CANCEL

        username = update.effective_user.username

        if update.message is None or update.message.text is None:
            logging.critical("No chat_id in incoming message!")
            return self.__BACKUP_RESTORE_CANCEL

        if update.effective_message is None or update.effective_message.chat_id is None:
            logging.critical("No chat_id in incoming message!")
            return self.__BACKUP_RESTORE_CANCEL

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
            return self.__BACKUP_RESTORE_CANCEL

        logging.debug("Called 'backup_restore' by '%s'.", username)

        reply_keyboard = [[]]  # type: ignore
        for game_server in self._game_server_names:
            sub_keyboard = [[game_server]]
            reply_keyboard = self.__concatenate_sequences(reply_keyboard, sub_keyboard)  # type: ignore

        await update.message.reply_text(
            "Please select server:",
            reply_markup=ReplyKeyboardMarkup(
                reply_keyboard,
                one_time_keyboard=True,
            ),
        )

        return self.__BACKUP_RESTORE_SERVER

    async def __backup_restore_filepath(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        if update.message is None or update.message.from_user is None:
            logging.critical("No username in incoming message!")
            return self.__BACKUP_RESTORE_CANCEL

        username = update.message.from_user.username

        if update.message is None or update.message.text is None:
            logging.critical("No text in incoming message!")
            return self.__BACKUP_RESTORE_CANCEL

        server_name = update.message.text

        if context.user_data is not None:
            context.user_data["game_server"] = server_name

        logging.debug("'%s' selected server '%s'.", username, server_name)

        game_server = next(
            (x for x in self._game_servers if x.name() == server_name), None
        )
        if game_server is None:
            return self.__BACKUP_RESTORE_CANCEL

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
                ),
            )

            return self.__BACKUP_RESTORE_FILEPATH

        logging.warning("No backups available!")
        await update.message.reply_text(
            escape_markdown(text="\u26D4 No backups available!", version=2),
            reply_markup=ReplyKeyboardRemove(),
        )

        return self.__BACKUP_RESTORE_CANCEL

    async def __backup_restore_start(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> int:
        if update.message is None or update.message.from_user is None:
            logging.critical("No username in incoming message!")
            return self.__BACKUP_RESTORE_CANCEL

        username = update.message.from_user.username

        if update.message is None or update.message.text is None:
            logging.critical("No text in incoming message!")
            return self.__BACKUP_RESTORE_CANCEL

        backup_readable_name = update.message.text

        logging.debug("'%s' selected backup '%s'.", username, backup_readable_name)

        if context.user_data is None:
            return self.__BACKUP_RESTORE_CANCEL

        server_name = context.user_data["game_server"]
        game_server = next(
            (x for x in self._game_servers if x.name() == server_name),
            None,
        )
        if game_server is None:
            return self.__BACKUP_RESTORE_CANCEL

        backups = self._backups[server_name]
        if backups is None:
            return self.__BACKUP_RESTORE_CANCEL

        backup_description = next(
            (x for x in backups if x.readable_name == backup_readable_name), None
        )
        if backup_description is None:
            return self.__BACKUP_RESTORE_CANCEL

        escaped_backup_name = escape_markdown(
            backup_description.readable_name, version=2
        )
        await update.message.reply_text(
            text=f"\u26A0 Started restoring backup from {escaped_backup_name}\, please wait\.",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=ReplyKeyboardRemove(),
        )

        if game_server.restore_backup(backup_description.filepath):
            await update.message.reply_text(
                text=f"\u2705 Backup from {escaped_backup_name} was restored successfully\!",
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=ReplyKeyboardRemove(),
            )
        else:
            await update.message.reply_text(
                text=f"\u26D4 Restoring backup from {escaped_backup_name} failed\, please check bot logs\!",
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=ReplyKeyboardRemove(),
            )

        return ConversationHandler.END

    async def __backup_restore_cancel(
        self, _1: Update, _2: ContextTypes.DEFAULT_TYPE
    ) -> int:
        return ConversationHandler.END

    async def __backup_list(
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

        if (
            len(self._configuration.allowed_channels) > 0
            and str(chat_id) not in self._configuration.allowed_channels
        ):
            logging.error(
                "Called 'backup_list' by '%s' in not allowed channel '%s'.",
                username,
                chat_id,
            )
            return

        logging.debug("Called 'backup_list' by '%s'.", username)

        if len(args) == 0:
            reply_keyboard = [[]]  # type: ignore
            for game_server in self._game_server_names:
                sub_keyboard = [[f"/backup_list {game_server}"]]
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

        self._backups[args[0]] = game_server.list_backups()

        backup_sum_message = "Available backups:\n"
        for backup in self._backups[args[0]]:
            backup_sum_message += (
                f"\- {escape_markdown(backup.readable_name, version=2)}\n"
            )

        await context.bot.send_message(
            chat_id,
            text=backup_sum_message,
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=ReplyKeyboardRemove(),
        )

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
                    f"\n\u26A0 {escape_markdown(text=notify_message.message, version=2)}",
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

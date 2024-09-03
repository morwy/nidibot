import json
import logging
import os
import signal
import sys

from nidibot import Nidibot


try:
    DISCORD_ALLOWED_CHANNELS = os.getenv('DISCORD_ALLOWED_CHANNELS').split(",")
except:
    DISCORD_ALLOWED_CHANNELS = ""

try:
    DISCORD_BOT_CONFIG = {
            'type': 'discord',
            'token': os.getenv('DISCORD_TOKEN'),
            'privileged_users': os.getenv('DISCORD_PRIVILEGED_USERS').split(","),
            'allowed_channels': DISCORD_ALLOWED_CHANNELS,
            'notify_polling_seconds': 5
            }
except:
    logging.warning("No Valid Discord Bot Config Provided")

try:
    TELEGRAM_ALLOWED_CHANNELS = os.getenv('TELEGRAM_ALLOWED_CHANNELS').split(",")
except:
    TELEGRAM_ALLOWED_CHANNELS = ""

try:
    TELEGRAM_BOT_CONFIG = {
            'type': 'telegram',
            'token': os.getenv('TELEGRAM_TOKEN'),
            'privileged_users': os.getenv('TELEGRAM_PRIVILEGED_USERS').split(","),
            'allowed_channels': TELEGRAM_ALLOWED_CHANNELS,
            'notify_polling_seconds': 5
            }
except:
    logging.warning("No Valid Telegram Bot Config Provided")

CONFIG = {
    'general': {
              'backups_folder_path': 'backups',
              'logs_folder_path': 'logs'
              },
    'bots': [],
    'server_providers': [{
        'type': 'nitrado',
        'token': os.getenv('NITRADO_TOKEN'),
        'timeout_seconds': 10,
        'polling_seconds': 5,
        'notifications': {
            'on_new_server': False,
            'on_status_change': False,
            'on_address_change': False,
            'on_version_change': False,
            'on_update_available_change': False
            }
        }]
    }

if DISCORD_BOT_CONFIG:
    CONFIG['bots'].append(DISCORD_BOT_CONFIG)

if os.path.exists('bot_configuration.json'):
    os.remove('bot_configuration.json')

with open('bot_configuration.json', 'w+') as configwriter:
    json.dump(CONFIG, configwriter, indent=4)


def shutdown_signal_handler(_1, _2):
    logging.critical("Caught SIGINT signal, nidibot will be shut down.")
    sys.exit(0)


if __name__ == "__main__":
    #
    # Catch Ctrl+C signal for notifying about bureau shutdown.
    #
    signal.signal(signal.SIGINT, shutdown_signal_handler)

    bot = Nidibot(os.path.dirname(os.path.realpath(__file__)))
    bot.start()

# nidibot

[![Supported Versions](https://img.shields.io/pypi/pyversions/nidibot.svg)](https://pypi.org/project/nidibot) [![PyPi Versions](https://img.shields.io/pypi/v/nidibot)](https://pypi.org/project/nidibot) [![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black) [![License](https://img.shields.io/pypi/l/nidibot.svg)](https://pypi.python.org/pypi/nidibot/)

## Description

nidibot is a simple to install and configure bot for controlling your game servers from any messaging platform. **Any** is a bit of exaggeration here, since only Discord and Telegram is supported.

**nidibot** name was derived from **Ni**trado, **Di**scord and **bot** - game server provider and messaging platform for which this bot was written originally.

### Features

* A minimalistic set of fundamental commands - everything you need to run and manage your game server.
* Possibility of connecting unlimited (somewhat) amount of game server providers and bots.
* High extensibility for game server providers and bots - just add a new class for missing game server provider or bot and make a PR.
* Easy setup - install ready-made nidibot package from PyPI and call `initialize_folder()`.
* Simple configuration - everything is located in `bot_configuration.json` file in bot folder.

### Limitations

* Telegram bot can not notify about game server status changes if 'allowed_channels' is empty. This is coming from Telegram API limitation.

### Commands

nidibot supports following commands:

```batch
/status [OPTIONAL:name]
```

Provides extended information about game server status.

---

```batch
/start [OPTIONAL:name]
```

Starts server if it is offline, restarts server if it is online.

---

```batch
/stop [OPTIONAL:name]
```

Stops server if it is online.

---

```batch
/restart [OPTIONAL:name]
```

Restarts server if it is online, starts server if it is offline.

---

```batch
/backup_create [OPTIONAL:name]
```

Creates backup of games server files. Backed up files are stored in the working folder of bot under **backup** folder.

---

```batch
/backup_list [OPTIONAL:name]
```

Lists available backups of specific game server.

---

```batch
/backup_restore [OPTIONAL:name] [REQUIRED:backup_name]
```

Restores specific backup on a game server.

---

Each command supports optional argument **name**. It is a convenience argument in case you have multiple game servers connected to the bot at once. In case if no name is specified, the command is applied to the first game server in the list.

## Quick start

### Prerequisites

You need to have following before you proceed with the instructions:

1. Virtual machine (VM) or server somewhere in the Internet.
2. Discord account (register or login at <https://discord.com/>).
3. Any Discord server where you have access.
4. Nitrado account (register or login at <https://server.nitrado.net/en-GB/>).
5. Any game server that runs on Nitrado to which you have access.

### Installation

1. Login to your VM or server via SSH.
2. Install Python 3.x. Do this only if Python 3.x is missing or very old. You don't need to have latest Python version for this bot.
3. Install this bot as Python package via pip:

```bash
pip install nidibot
```

4. Or upgrade already installed bot:

```bash
pip install nidibot --upgrade
```

### Configuration

1. Login to your VM or server via SSH.
2. Create new folder for storing bot files.
3. Proceed to the folder.
4. Call following command for initializing bot in this folder and create default configuration files:

```bash
# Ubuntu/Linux only.
python3 -c 'from nidibot.nidibot import Nidibot; Nidibot.initialize_folder()'
```

5. Following files should appear.
6. Open **bot_configuration.json** file in any text editor and modify required values to your own:

```json
{
    "general": {
        "backups_folder_path": "backups",
        "logs_folder_path": "logs"
    },
    "bots": [
        {
            "type": "discord",
            "token": "your-bot-token",
            "privileged_users": [],
            "allowed_channels": [],
            "notify_polling_seconds": 5
        }
    ],
    "server_providers": [
        {
            "type": "nitrado",
            "token": "your-gameserver-api-token",
            "timeout_seconds": 10,
            "polling_seconds": 5,
            "notifications": {
                "on_new_server": true,
                "on_status_change": true,
                "on_address_change": true,
                "on_version_change": true,
                "on_update_available_change": true
            }
        }
    ]
}
```

7. Install **nidibot** service, so it will start automatically every system restart.

```bash
sudo cp nidibot.service /etc/systemd/system/nidibot.service && sudo systemctl daemon-reload && sudo systemctl enable nidibot.service
```

8. Start newly installed service:

```bash
sudo systemctl start nidibot.service
```

9. Check service status:

```bash
sudo systemctl status nidibot.service
```

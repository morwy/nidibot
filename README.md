# nidibot

[![Supported Versions](https://img.shields.io/pypi/pyversions/nidibot.svg)](https://pypi.org/project/nidibot) [![PyPi Versions](https://img.shields.io/pypi/v/nidibot)](https://pypi.org/project/nidibot) [![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black) [![License](https://img.shields.io/pypi/l/nidibot.svg)](https://pypi.python.org/pypi/nidibot/)

## Description

nidibot is a simple to install and configure bot for controlling your game servers from any messaging platform. **Any** is a bit of exaggeration here, since only Discord and Telegram is supported.

**nidibot** name was derived from **Ni**trado, **Di**scord and **bot** - game server provider and messaging platform for which this bot was written originally.

It seems that only Nitrado has a good API for developers available. Any other game server provider does not provide (_pun intended_) any API at all. Some of them provide possibility of managing game server with remote console (RCON) though. RCON support would be a great addition to this project (_someday_).

Any contributions, bug reports and pull requests are welcome!

### Features

* A minimalistic set of fundamental commands - everything you need to run and manage your game server.
* Possibility of connecting unlimited (somewhat) amount of game server providers and bots.
* High extensibility for game server providers and bots - just add a new class for missing game server provider or bot and make a PR.
* Easy setup - install ready-made nidibot package from PyPI and call `initialize_folder()`.
* Simple configuration - everything is located in `bot_configuration.json` file in bot folder. Please see configuration description below for more details.

### Limitations

* Command `/backup_restore` shows only latest 25 backups in Discord bot. This is coming from Discord limitation, it can show only 25 buttons in total (5 rows with 5 buttons each).
* Telegram bot can not notify about game server status changes if 'allowed_channels' is empty. This is coming from Telegram API limitation.

### Commands

nidibot supports following commands:

```batch
/status [OPTIONAL:name]
```

Provides extended status information about game server.

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

Creates backup of games server files. Backed up files are stored in the working folder of bot under **backups** folder.

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
2. Bot account (Discord or Telegram one).
3. Any Discord server or Telegram channel where you have administrative access.
4. Nitrado account (register or login at <https://server.nitrado.net/en-GB/>).
5. Any game server that runs on Nitrado to which you have administrative access.

### Installation

#### Docker

1. Create a `compose.yml` file with the following contents:

```yaml
name: nidibot
services:
  nidibot:
    container_name: nidibot
    image: ghcr.io/thechainercygnus/nidibot:latest
    volumes:
      - ./backups:/app/backups
      - ./logs:/app/logs
    restart: unless-stopped
    # env_file:
    #  - .env
    # Uncomment to set Environment Variables
    # environment:
    #  - NITRADO_TOKEN=nitrado_api_token
    #   Uncomment the following to use Discord
    #   - DISCORD_TOKEN=discord_token
    #   - DISCORD_PRIVILEGED_USERS=user1,user2                    # Can be single or comma separated list
    #   - DISCORD_ALLOWED_CHANNELS=channel_id_1,channel_id_2      # Can be single or comma separated list
    #   Uncomment the following to use Telegram
    #   - TELEGRAM_TOKEN=telegram_atoken
    #   - TELEGRAM_PRIVILEGED_USERS=user1,user2                   # Can be single or comma separated list
    #   - TELEGRAM_ALLOWED_CHANNELS=channel_id_1,channel_id_2     # Can be single or comma separated list
```

2. Nidibot requires a few environment variables to get up and running. Use only the necessary chat platforms (e.g. if you only need discord, only set the discord settings).

|Variable|Description|Required|
|----|----|----|
|`NITRADO_TOKEN`|Nitrado API Token|**Yes**|
|`DISCORD_TOKEN`|Discord Bot Token|No|
|`DISCORD_PRIVILEGED_USERS`|Comma Separated List of Privileged Discord Usernames|No|
|`DISCORD_ALLOWED_CHANNELS`|Comma Separated List of Allowed Channels for Nidibot to recieve commands in|No|
|`TELEGRAM_TOKEN`|Telegram Bot Token|No|
|`TELEGRAM_PRIVILEGED_USERS`|Comma Separated List of Privileged Telegram Usernames|No|
|`TELEGRAM_ALLOWED_CHANNELS`|Comma Separated List of Allowed Channels for Nidibot to recieve commands in|No|

3. Set required environment variables for your needs using either:
    1. .env File method.
        a. Delete lines 12-22 of `compose.yml`.
        b. Uncomment the remainder of the file.
        c. Create a file named `.env` alongside `compose.yml`.
        d. Create the file with the needed variables besides `NITRADO_TOKEN` to connect to your services.
    2. Set the variables in `compose.yml`.
        a. Delete lines 10-12 of `compose.yml`.
        b. Uncomment the remainder of the file.
        c. Update and Delete lines as needed to configure your instance.
4. Start the bot with `docker compose up -d`
5. Note that it can take up to an hour for the new slash commands to register in your client. This can sometimes be worked around by completely closing and reopening your client.

#### Linux Service

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
python3 -c 'from nidibot import Nidibot; Nidibot.initialize_folder()'
```

5. Open **bot_configuration.json** file in any text editor and modify required values to your own:

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

6. Install **nidibot** service, so it will start automatically every system restart.

```bash
# Ubuntu/Linux only.
sudo cp nidibot.service /etc/systemd/system/nidibot.service && sudo systemctl daemon-reload && sudo systemctl enable nidibot.service
```

7. Start newly installed service:

```bash
# Ubuntu/Linux only.
sudo systemctl start nidibot.service
```

8. Check service status:

```bash
# Ubuntu/Linux only.
sudo systemctl status nidibot.service
```

## Configuration description

The top level of configuration contains:

| Group | Description |
| --- | --- |
| `general` | General parameters of nidibot configuration. |
| `bots` | List of structures describing bot configuration parameters. |
| `server_providers` | List of structures describing game server configuration parameters. |

### General

| Parameter | Description |
| --- | --- |
| `backups_folder_path` | The directory path in which all backups will be stored. Can be both relative or absolute. Default: **"backups"**, relative to bot working directory. |
| `logs_folder_path` | The directory path in which logs will be stored. Can be both relative or absolute. Default: **"logs"**, relative to bot working directory |

### Bot configuration

| Parameter | Description |
| --- | --- |
| `type` | The type of the bot. Allowed values: `discord`, `telegram`. Default: **empty**. |
| `token` | The authentication token required for the bot. Default: **empty**. |
| `privileged_users` | The list of privileged users that can call administrative commands. Default: **empty**. |
| `allowed_channels` | The list of allowed channels from where commands will be accepted and processed. Default: **empty**. |
| `notify_polling_seconds` | The period in seconds for forwarding messages from queue to connected channels. Default: **5**. |

### Server provider configuration

| Parameter | Description |
| --- | --- |
| `type` | The type of the server provider. Allowed values: `nitrado`. Default: **""**. |
| `token` | The authentication token required for the server provider. Default: **""**. |
| `timeout_seconds` | The timeout in seconds for getting a response from the server provider. Default: **10**. |
| `polling_seconds` | The period in seconds for polling a status from the server provider. Default: **5**. |
| `notifications / on_new_server` | Toggles notification on a new game server appearing. Default: **false**. |
| `notifications / on_status_change` | Toggles notification on a game server status change. Default: **false**. |
| `notifications / on_address_change` | Toggles notification on a game server IP address change. Default: **false**. |
| `notifications / on_version_change` | Toggles notification on a game server version change. Default: **false**. |
| `notifications / on_update_available_change` | Toggles notification if game server got an update available. Default: **false**. |

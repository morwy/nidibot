# Nitrado Discord bot

[![Supported Versions](https://img.shields.io/pypi/pyversions/nidibot.svg)](https://pypi.org/project/nidibot) [![PyPi Versions](https://img.shields.io/pypi/v/nidibot)](https://pypi.org/project/nidibot) [![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black) [![License](https://img.shields.io/pypi/l/nidibot.svg)](https://pypi.python.org/pypi/nidibot/)

## Prerequisites

You need to have following before you proceed with the instructions:

1. Virtual machine (VM) or server somewhere in the Internet.
2. Discord account (register or login at <https://discord.com/>).
3. Any Discord server where you have access.
4. Nitrado account (register or login at <https://server.nitrado.net/en-GB/>).
5. Any game server that runs on Nitrado to which you have access.

## Installation

1. Login to your VM or server via SSH.
2. Install Python 3.x. Do this only if Python is missing or very old. You don't need to have latest Python version for this bot.
3. Install this bot as Python package via pip:

```bash
pip install nidibot
```

4. Or upgrade already installed bot:

```bash
pip install nidibot --upgrade
```

## Configuration

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
    "connection": {
        "discord_bot_token": "your-discord-bot-token",
        "nitrado_api_token": "your-nitrado-api-token"
    },
    "discord_admin_users": []
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

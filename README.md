# Nitrado Discord bot

## Prerequisites

You need to have following before you proceed with the instructions:

1. Virtual machine (VM) or server somewhere in the Internet.
2. Discord account (register or login at <https://discord.com/>).
3. Any Discord server where you have access.
4. Nitrado account (register or login at <https://server.nitrado.net/en-GB/>).
5. Any game server that runs on Nitrado to which you have access.

## Installation

1. Login to your VM or server via SSH.
2. Install Python 3.x from <https://www.python.org/downloads/>.
3. Install following packages (Ubuntu/Linux only):

```bash
sudo apt install libffi-dev libnacl-dev python3-dev -y
```

5. Install Discord Python package:

```bash
pip install -U discord.py
```

6. In case if you meet "**externally-managed-environment**" error under Python 3.11 version, then run following command:

```bash
# Ubuntu/Linux only.
sudo mv /usr/lib/python3.11/EXTERNALLY-MANAGED /usr/lib/python3.11/EXTERNALLY-MANAGED.old
```

7. Install this bot as Python package via pip:

```bash
pip install nidibot
```

8. Or upgrade already installed bot:

```bash
pip install nidibot --upgrade
```

<details>
<summary><b>References used (click to show):</b></summary>
<ul>
<li><a href="https://discordpy.readthedocs.io/en/latest/intro.html">https://discordpy.readthedocs.io/en/latest/intro.html</a></li>
<li><a href="https://stackoverflow.com/questions/75608323/how-do-i-solve-error-externally-managed-environment-every-time-i-use-pip-3">https://stackoverflow.com/questions/75608323/how-do-i-solve-error-externally-managed-environment-every-time-i-use-pip-3</a></li>
</ul>
</details>

## Configuration

1. Login to your VM or server via SSH.
2. Create new folder for storing bot files.
3. Proceed to the folder.
4. Call following command for initializing bot in this folder and create default configuration files:

```bash
# Ubuntu/Linux only.
python3 -c 'from nidibot import Nidibot; Nidibot.initialize_folder()'
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

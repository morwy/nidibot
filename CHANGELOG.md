# Changelog

All notable changes to this project will be documented in this file.

## [1.2.0] - 2024-03-04

### 🐛 Bug Fixes

- *(telegram-bot)* Fixed anomalous slashes in strings.
- *(ci)* Corrected creation of GitHub release entry text.

### 🚜 Refactor

- *(bots)* Moved emojis to BotBase class.
- *(telegram-bot)* Unified common commands under the same functionality.
- *(telegram-bot)* Unified conversation enumeration.

### ⚙️ Miscellaneous Tasks

- *(discord-bot)* Added missing imports.

## [1.1.9] - 2024-03-04

### 🐛 Bug Fixes

- *(ci)* Corrected way of generating CHANGELOG.md and GitHub release entry text.
- *(telegram-bot)* Resizing reply keyboard during backup_restore.

### 🚜 Refactor

- *(telegram-bot)* Switched fallback to MessageHandler and not CommandHandler.
- *(telegram-bot)* Changed status command handling to ConversationHandler.
- *(telegram-bot)* Changed start command handling to ConversationHandler.
- *(telegram-bot)* Changed stop command handling to ConversationHandler.
- *(telegram-bot)* Changed restart command handling to ConversationHandler.
- *(telegram-bot)* Changed backup_create command handling to ConversationHandler.
- *(telegram-bot)* Changed backup_list command handling to ConversationHandler.

### Build

- *(deps)* Bump actions/setup-python from 3 to 5
- *(deps)* Bump actions/checkout from 3 to 4

## [1.1.8] - 2024-03-02

### 🚀 Features

- *(bots)* Controlling notify period from nidibot configuration.

### 🐛 Bug Fixes

- *(ci)* Fixed generation of CHANGELOG.md and GitHub release entry.
- *(bots)* Fixed issue with crash when there were no backups available.
- *(telegram-bot)* Dropping pending signals from Telegram server for avoiding spam on nidibot restart.
- *(telegram-bot)* Fixed issue when conversation was not started again after one run.

### 🚜 Refactor

- *(bot-base)* Renamed BotInterface to BotBase.

## [1.1.7] - 2024-03-02

### 🚀 Features

- *(cd)* Added usage of git-cliff GitHub Action.

### 🚜 Refactor

- *(bot_factory.py)* Changed support bot list to be a static private class field.
- *(server_provider_factory.py)* Changed supported server provider list to be a static private class field.

### README.md

- Removed limitation entry about only one Telegram bot.

## [1.1.6] - 2024-02-29

### Setup.cfg

- Added missing python-telegram-bot[job-queue] dependency.

## [1.1.5] - 2024-02-29

### README.md

- Added entry about '/backup_restore'.

### Discord_bot.py

- Removed redundant smileys.

### Telegram_bot.py

- Disabled redundant logging.
- Added auto notification for channels from allowed_channels list.
- Fixed issue with running in thread.

## [1.1.4] - 2024-02-26

### README.md

- Corrected typos.

### Discord_bot.py

- Fixed issue with showing backup list.

### Nitrado_server_provider.py

- Moved some variables to base class.
- Added API check, MySQL credentials reading and saving MySQL DB via mysqldump.

### Setup.cfg

- Corrected development status, environment and intended audience.

### Telegram_bot.py

- Fixed redundant logging of httpcore logger.

## [1.1.3] - 2024-02-25

### README.md

- Added information about limitations.

### Bot_interface.py

- Moved common functionality from discord_bot.py and telegram_bot.py.

## [1.1.0] - 2024-02-17

### 🧪 Testing

- Removed due to being redundant.

### Nidibot.py

- Moved bot functionality to separate folder. Implemented factory and interface classes for server providers.
- Modifying working directory in nidibot.service file upon copy.

## [1.0.9] - 2024-02-15

### README.md

- Added description and commands.

### Game_server.py

- Added docstrings.

### Nidibot.py

- Added server address to response title.

### Nitrado_server_provider.py

- Removed excessive logging.

## [1.0.8] - 2024-02-04

### Game_server.py

- Added GameServer wrapper class for easier access and control of each game server instance.

### Nidibot.py

- Added possibility to state server name in all available commands.

### Server_provider_interface.py

- Accessing game server functions via IDs rather than indices.

## [1.0.7] - 2024-02-03

### Nidibot.py

- Switched to using NitradoServerProvider class.
- Added server information into response.
- Added nidibot version into logging.

## [1.0.6] - 2024-02-02

### .gitignore

- Corrected folder filter.

### Nidibot.py

- Changed structure of bot_configuration.json for higher flexibility.
- Properly initializing server providers.
- Added test options for each available command.

### Nitrado.py

- Added safety checks in constructor.

### Setup.cfg

- Added missing ftputil.

## [1.0.5] - 2024-02-01

### Nidibot.py

- Migrated bot to hikari + lightbulb. That fixed issue with commands not showing in Discord chat.

## [1.0.4] - 2024-01-31

### Nidibot.py

- Added on_ready() event.

## [1.0.3] - 2024-01-31

### Nidibot.py

- Added descriptions to all commands.
- Fixed double stating of @command decorator.

## [1.0.2] - 2024-01-31

### Nidibot/templates

- Corrected errors.

## [1.0.0] - 2024-01-31

### Setup.cfg

- Corrected format of install_requires.

<!-- generated by git-cliff -->

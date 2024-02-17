import json
import os

from nidibot.nidibot import Nidibot


def test_folder_initialization(tmp_path):
    os.chdir(tmp_path)

    assert len(os.listdir(tmp_path)) == 0

    Nidibot.initialize_folder()

    assert len(os.listdir(tmp_path)) > 0


def test_discord_connection(tmp_path):
    os.chdir(tmp_path)

    json_configuration = {
        "discord_bot_token": "",
        "nitrado_api_token": "",
        "nitrado_service_id": "",
    }

    configuration_filepath = os.path.join(tmp_path, "bot_configuration.json")
    with open(configuration_filepath, "w", encoding="utf-8") as file:
        json.dump(
            json_configuration,
            file,
            ensure_ascii=False,
            indent=4,
        )

    bot = Nidibot(tmp_path)
    bot.start()

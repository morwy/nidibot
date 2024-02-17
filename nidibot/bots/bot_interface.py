#!/usr/bin/env python

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List

from nidibot.server_provider.game_server import GameServer


@dataclass
class BotConfiguration:
    type: str = ""
    token: str = ""
    privileged_users: list = field(default_factory=list)


class BotInterface(ABC):
    @abstractmethod
    def __init__(self, configuration: BotConfiguration, game_servers: List[GameServer]):
        pass

    @abstractmethod
    def notify(self, title: str, message: str) -> None:
        pass

    @abstractmethod
    def activate(self) -> bool:
        pass

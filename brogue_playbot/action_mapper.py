from abc import ABC, abstractmethod
from .command import *


class ActionMapper(ABC):
    """
    ACTION_MAP SHOULD BE DEFINED IN SUBCLASS
    """

    @property
    @abstractmethod
    def ACTION_MAP(self) -> dict[str, list[Command]]:
        pass

    def __init__(self):
        self.action_map = self.ACTION_MAP

    def get_commands(self, action_command: str) -> list[Command]:
        action_command = action_command.upper()
        if action_command not in self.action_map:
            raise ValueError(f"Invalid action command: {action_command}")
        return self.action_map[action_command]

    def get_commands_sequence(self, actions: list[str]) -> list[Command]:
        commands = []
        for action in actions:
            commands.extend(self.get_commands(action))
        return commands


class BrogueActionMapper(ActionMapper):
    ACTION_MAP = {
        "MOVE_UP": [PressCommand(key="up")],
        "MOVE_DOWN": [PressCommand(key="down")],
        "MOVE_LEFT": [PressCommand(key="left")],
        "MOVE_RIGHT": [PressCommand(key="right")],
        "REST": [PressCommand(key="z")],
        "SEARCH": [PressCommand(key="s")],
        "EXPLORE": [PressCommand(key="x")],
        "INVENTORY": [PressCommand(key="i")],
    }

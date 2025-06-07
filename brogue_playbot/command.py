from dataclasses import dataclass, asdict, field
from typing import Type, Self
from enum import StrEnum
import json


class MouseButton(StrEnum):
    LEFT = "left"
    RIGHT = "right"
    MIDDLE = "middle"


@dataclass
class Command:
    type: str = field(init=False)

    def __post_init__(self):
        # Set type to the class name without "Command" and convert to lowercase (e.g. PressCommand -> press)
        self.type = self.__class__.__name__.replace("Command", "").lower()

    @classmethod
    def serialize(cls, commands: list[Self], compact: bool = False) -> str:
        command_dicts = [asdict(cmd) for cmd in commands]
        if compact:
            return json.dumps(command_dicts, ensure_ascii=False, separators=(",", ":"))
        return json.dumps(command_dicts, indent=4, ensure_ascii=False)

    @classmethod
    def deserialize(cls, json_str: str) -> list[Self]:
        command_dicts = json.loads(json_str)
        commands = []
        for cmd_dict in command_dicts:
            cmd_type_str = cmd_dict.pop("type")  # 'type' 필드를 먼저 추출
            if cmd_type_str not in COMMAND_TYPES:
                print(
                    f"경고: 알 수 없는 명령어 타입 '{cmd_type_str}'. 이 명령어를 건너뜁니다."
                )
                continue

            command_class = COMMAND_TYPES[cmd_type_str]

            # Enum 값을 다시 Enum 객체로 변환
            if "button" in cmd_dict and cmd_type_str in [
                "click"
            ]:  # 'click' 명령어에만 해당
                cmd_dict["button"] = MouseButton(cmd_dict["button"])

            # hotkey의 keys 필드가 문자열인 경우 리스트로 변환
            if cmd_type_str == "hotkey" and isinstance(cmd_dict.get("keys"), str):
                cmd_dict["keys"] = cmd_dict["keys"].split(",")

            try:
                # 추출된 type 필드를 제외한 나머지 키-값을 사용하여 dataclass 인스턴스 생성
                cmd_instance = command_class(**cmd_dict)
                commands.append(cmd_instance)
            except TypeError as e:
                print(
                    f"오류: 명령어 '{cmd_type_str}'의 필드 불일치 또는 타입 오류: {e}. 데이터: {cmd_dict}"
                )
            except ValueError as e:  # Enum 변환 오류 등
                print(
                    f"오류: 명령어 '{cmd_type_str}'의 값 오류: {e}. 데이터: {cmd_dict}"
                )
        return commands


@dataclass
class PressCommand(Command):
    key: str


@dataclass
class KeyUpDownCommand(Command):
    key: str
    action: str  # 'down' 또는 'up'


@dataclass
class ClickCommand(Command):
    button: MouseButton = MouseButton.LEFT
    clicks: int = 1  # 1: click, 2: doubleclick, 3: tripleclick


@dataclass
class MoveCommand(Command):
    x: int
    y: int


@dataclass
class DragCommand(Command):
    x: int
    y: int
    duration: float = 0.5


@dataclass
class WriteCommand(Command):
    text: str
    interval: float = 0.1


@dataclass
class ScrollCommand(Command):
    amount: int  # 양수는 위로, 음수는 아래로


@dataclass
class HotkeyCommand(Command):
    keys: str | list[str]  # 'ctrl,c' 또는 ['ctrl', 'c']


@dataclass
class WaitCommand(Command):
    duration: float


COMMAND_TYPES: dict[str, Type[Command]] = {
    "press": PressCommand,
    "keyupdown": KeyUpDownCommand,
    "click": ClickCommand,
    "move": MoveCommand,
    "drag": DragCommand,
    "write": WriteCommand,
    "scroll": ScrollCommand,
    "hotkey": HotkeyCommand,
    "wait": WaitCommand,
}

import pyautogui
import time

from .command import *


class HardwareController:
    def __init__(self, delay: float = 0.1):
        self.delay = delay

    def execute_sequence(self, sequence: list[Command]):
        for command in sequence:
            try:
                self.execute_command(command)
            except Exception as e:
                print(f"명령어 실행 중 오류 발생: {e}")
                continue
            time.sleep(self.delay)

    def execute_command(self, command: Command):
        """결정된 행동에 따라 키보드를 조작합니다."""
        print(f"행동 실행: {command}")

        if isinstance(command, PressCommand):
            pyautogui.press(command.key)
        elif isinstance(command, KeyUpDownCommand):
            if command.action == "down":
                pyautogui.keyDown(command.key)
            elif command.action == "up":
                pyautogui.keyUp(command.key)
        elif isinstance(command, ClickCommand):
            if command.button == MouseButton.LEFT:
                if command.clicks == 1:
                    pyautogui.click()
                elif command.clicks == 2:
                    pyautogui.doubleClick()
                elif command.clicks == 3:
                    pyautogui.tripleClick()
            elif command.button == MouseButton.RIGHT:
                pyautogui.rightClick()
            elif command.button == MouseButton.MIDDLE:
                pyautogui.middleClick()
        elif isinstance(command, MoveCommand):
            pyautogui.moveTo(command.x, command.y)
        elif isinstance(command, DragCommand):
            pyautogui.dragTo(command.x, command.y, duration=command.duration)
        elif isinstance(command, WriteCommand):
            pyautogui.write(command.text, interval=command.interval)
        elif isinstance(command, ScrollCommand):
            pyautogui.scroll(command.amount)
        elif isinstance(command, HotkeyCommand):
            pyautogui.hotkey(*command.keys)
        elif isinstance(command, WaitCommand):
            time.sleep(command.duration)
        else:
            raise ValueError(f"알 수 없는 명령어: {command}")

import os
import time
import platform
import datetime

from brogue_playbot.action_mapper import BrogueActionMapper
from brogue_playbot.hardware_controller import HardwareController
from brogue_playbot.gemini_agent import GeminiVLMAgent, GeminiPolicyAgent
from brogue_playbot.screen_capturer import ScreenCapturer
from brogue_playbot.windows_finder import MacWindowFinder, WindowsWindowFinder


class BrogueBot:
    def __init__(self, interval: float = 0.5, image_directory: str = "data"):
        self.step_count = 0
        self.interval = interval
        system = platform.system()
        if system == "Darwin":  # macOS
            self.windows_finder = MacWindowFinder()
        elif system == "Windows":
            self.windows_finder = WindowsWindowFinder()
        else:
            raise ValueError(f"지원하지 않는 운영체제: {system}")
        self.screen_capturer = ScreenCapturer()
        self.vlm_agent = GeminiVLMAgent()
        self.policy_agent = GeminiPolicyAgent()
        self.action_mapper = BrogueActionMapper()
        self.hardware_controller = HardwareController()

        now = datetime.datetime.now().strftime("%Y%m%d")
        bot_index = f"brogue-{now}"
        self.image_directory = os.path.join(image_directory, bot_index)
        os.makedirs(self.image_directory, exist_ok=True)

    def run(self, steps: int = 100):
        brogue_window_region = self.windows_finder.find_window("brogue")
        if not brogue_window_region:
            print("Brogue 윈도우를 찾을 수 없습니다.")
            return

        self.screen_capturer.set_region(brogue_window_region)
        self.step_count = 0
        while self.step_count < steps:
            self.step(brogue_window_region)
            time.sleep(self.interval)
            # TODO: 게임 종료 조건 추가
            
        print(f"Bot ended in {self.step_count} steps")

    def step(self, brogue_window_region):
        self.screen_capturer.set_region(brogue_window_region)
        screenshot = self.screen_capturer.capture()
        if screenshot:
            screenshot.save(
                os.path.join(self.image_directory, f"screenshot_{self.step_count}.png")
            )
        else:
            print("screenshot is None")
        vlm_response = self.vlm_agent.generate_content(screenshot)
        print(f"vlm_agent: {vlm_response}")
        policy_response = self.policy_agent.generate_content(vlm_response)
        print(f"policy_agent: {policy_response}")
        actions = policy_response.split("\n")
        commands = self.action_mapper.get_commands_sequence(actions)
        self.hardware_controller.execute_sequence(commands)

        self.step_count += 1


if __name__ == "__main__":
    bot = BrogueBot()
    bot.run()

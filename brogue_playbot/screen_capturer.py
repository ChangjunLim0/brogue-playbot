from PIL import Image
import pyautogui
import mss


class ScreenCapturer:
    def __init__(self, region=None, method="mss"):
        """
        Args:
            region (tuple, optional): (x, y, width, height) 캡처할 화면 영역. None이면 주 모니터 전체.
            method (str, optional): 'mss' 또는 'pyautogui' 중 캡처 방법 선택.
        """
        self.region = region
        self.method = method
        self.sct = None
        if self.method == "mss":
            self.sct = mss.mss()
            # if self.region:
            #     self.monitor = {
            #         "top": self.region[1],
            #         "left": self.region[0],
            #         "width": self.region[2],
            #         "height": self.region[3],
            #     }
            # else:
            #     # macOS와 Windows에서 sct.monitors[0]은 전체 가상화면, [1]부터 실제 모니터입니다.
            #     # 주 모니터를 사용하도록 설정합니다.
            #     if not self.sct.monitors:
            #         raise EnvironmentError(
            #             "사용 가능한 모니터를 찾을 수 없습니다. 디스플레이 설정을 확인하세요."
            #         )
            # self.monitor = self.sct.monitors[1]  # 주 모니터

        print(
            f"ScreenCapturer 초기화 완료. 방법: {self.method}, 영역: {self.region if self.region else '전체 화면'}"
        )
        # if self.method == "mss":
        #     print(f"MSS 선택된 모니터 정보: {self.monitor}")

    def set_region(self, region: tuple[int, int, int, int]):
        self.region = region

    def capture(self) -> Image.Image | None:
        """화면을 캡처하여 PIL Image 객체로 반환합니다."""
        try:
            if self.method == "mss":
                if not self.sct:  # sct가 None이면 mss.mss() 재호출
                    self.sct = mss.mss()
                mss_region = {
                    "left": self.region[0],
                    "top": self.region[1],
                    "width": self.region[2],
                    "height": self.region[3],
                }
                sct_img = self.sct.grab(mss_region)
                img = Image.frombytes(
                    "RGB", (sct_img.width, sct_img.height), sct_img.rgb
                )
                print(f"width: {sct_img.width}, height: {sct_img.height}")
                return img
            elif self.method == "pyautogui":
                if self.region:
                    return pyautogui.screenshot(region=self.region)
                else:
                    return pyautogui.screenshot()
            else:
                print(f"알 수 없는 캡처 방법: {self.method}")
                return None
        except Exception as e:
            print(f"화면 캡처 중 오류 발생 ({self.method}): {e}")
            # mss 객체가 닫혔을 수 있으므로, 다음 시도를 위해 None으로 설정
            if (
                self.method == "mss"
                and isinstance(e, mss.exception.ScreenShotError)
                and self.sct
            ):
                # sct 객체 재초기화 시도 또는 None으로 설정하여 다음 호출시 재시도 유도
                try:
                    self.sct.close()  # 기존 객체 명시적 닫기
                except:
                    pass
                self.sct = None
            return None

    def __del__(self):
        if self.method == "mss" and self.sct:
            try:
                self.sct.close()
            except Exception as e:
                print(f"MSS 객체 닫는 중 오류: {e}")

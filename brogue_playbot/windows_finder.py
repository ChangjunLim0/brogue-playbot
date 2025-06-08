from abc import ABC, abstractmethod


class WindowFinder(ABC):
    @abstractmethod
    def find_window(self, window_name: str) -> tuple[int, int, int, int]:
        """
        Returns:
            tuple[int, int, int, int]: (x, y, width, height)
        """
        pass


class MacWindowFinder(WindowFinder):
    def find_window(self, window_name: str) -> tuple[int, int, int, int]:
        try:
            import Quartz
            from AppKit import NSWorkspace

            # 실행 중인 모든 앱 가져오기
            workspace = NSWorkspace.sharedWorkspace()
            running_apps = workspace.runningApplications()

            for app in running_apps:
                if window_name in app.localizedName().lower():
                    pid = app.processIdentifier()
                    options = (
                        Quartz.kCGWindowListOptionOnScreenOnly
                        | Quartz.kCGWindowListExcludeDesktopElements
                    )
                    window_list = Quartz.CGWindowListCopyWindowInfo(
                        options, Quartz.kCGNullWindowID
                    )

                    for window in window_list:
                        if window[Quartz.kCGWindowOwnerPID] == pid:
                            bounds = window[Quartz.kCGWindowBounds]
                            window_region = (
                                int(bounds["X"]),
                                int(bounds["Y"]),
                                int(bounds["Width"]),
                                int(bounds["Height"]),
                            )
                            print(f"Brogue 윈도우 찾음: {window_region}")
                            return window_region
            return None

        except ImportError:
            print("macOS 관련 라이브러리 import 실패")
            return None


class WindowsWindowFinder(WindowFinder):
    def find_window(self, window_name: str) -> tuple[int, int, int, int]:
        try:
            import win32gui

            window_handle = win32gui.FindWindow(None, window_name)
            rect = win32gui.GetWindowRect(window_handle)  # left, top, right, bottom
            rect_ltwh = (
                rect[0],  # left
                rect[1],  # top
                rect[2] - rect[0],  # width
                rect[3] - rect[1],  # height
            )
            return rect_ltwh

        except ImportError:
            print("Windows 관련 라이브러리 import 실패")
            return None

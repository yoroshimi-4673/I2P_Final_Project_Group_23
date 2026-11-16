class SettingsController:

    def __init__(self):

        self.volume = 50

        self.dragging_volume = False


    def start_volume_drag(self):
        """開始拖曳音量Slider。"""

        self.dragging_volume = True


    def stop_volume_drag(self):
        """停止拖曳音量Slider。"""

        self.dragging_volume = False


    def update_volume(
        self,
        slider_rect,
        mouse_pos
    ):
        """依滑鼠位置更新音量百分比。"""

        relative_x = (
            mouse_pos[0]
            - slider_rect.x
        )

        relative_x = max(
            0,
            min(
                relative_x,
                slider_rect.width
            )
        )

        self.volume = int(
            relative_x
            / slider_rect.width
            * 100
        )


    def handle_click(
        self,
        settings_buttons,
        mouse_pos
    ):
        """處理Settings內各按鈕點擊。"""

        if not settings_buttons:
            return None

        if settings_buttons[
            "slider"
        ].collidepoint(
            mouse_pos
        ):

            self.start_volume_drag()

            return "volume"


        if settings_buttons[
            "800"
        ].collidepoint(
            mouse_pos
        ):

            return "resolution_800"


        if settings_buttons[
            "1024"
        ].collidepoint(
            mouse_pos
        ):

            return "resolution_1024"


        if settings_buttons[
            "codex"
        ].collidepoint(
            mouse_pos
        ):

            return "open_codex"


        if settings_buttons[
            "menu"
        ].collidepoint(
            mouse_pos
        ):

            return "go_menu"


        if settings_buttons[
            "close"
        ].collidepoint(
            mouse_pos
        ):

            return "close_settings"

        return None
    def handle_key(
        self,
        event
    ):
        """處理Settings畫面的鍵盤輸入。"""

        import pygame

        if event.key == pygame.K_ESCAPE:
            return "close_settings"

        return None
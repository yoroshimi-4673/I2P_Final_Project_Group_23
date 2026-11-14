class CodexController:

    def __init__(self, codex_ui):

        self.codex_ui = codex_ui

        # 記錄Codex關閉後應返回哪個主畫面
        self.previous_ui_screen = None

        # 記錄Codex是否從Settings進入
        self.return_to_settings = False


    def open(
        self,
        current_ui_screen,
        from_settings=False
    ):
        """記錄Codex開啟前的畫面來源。"""

        # 保存目前主畫面供關閉Codex時返回
        self.previous_ui_screen = (
            current_ui_screen
        )

        # 保存是否需要返回Settings
        self.return_to_settings = (
            from_settings
        )


    def close(self):
        """關閉Codex並回傳應返回的位置。"""

        # 關閉目前開啟中的Codex物品
        self.codex_ui.close_item()

        result = {
            "ui_screen": (
                self.previous_ui_screen
            ),
            "open_settings": (
                self.return_to_settings
            )
        }

        # 關閉後清除暫存返回狀態
        self.return_to_settings = False

        return result


    def handle_key(self, event):
        """處理Codex鍵盤輸入。"""

        import pygame

        if event.key != pygame.K_ESCAPE:
            return None

        # Item Modal開啟時Esc只關閉Item
        if self.codex_ui.selected_item is not None:

            self.codex_ui.close_item()

            return "item_closed"

        # 沒有Item時Esc才離開Codex
        return "close_codex"


    def handle_click(
        self,
        codex_buttons,
        mouse_pos
    ):
        """處理Codex滑鼠點擊。"""

        modal_buttons = (
            codex_buttons.get(
                "modal",
                {}
            )
        )

        # Item Modal開啟時優先處理Modal
        if self.codex_ui.selected_item is not None:

            close_button = (
                modal_buttons.get(
                    "close"
                )
            )

            if (
                close_button is not None
                and close_button.collidepoint(
                    mouse_pos
                )
            ):
                self.codex_ui.close_item()

            return None

        back_button = (
            codex_buttons.get(
                "back"
            )
        )

        if (
            back_button is not None
            and back_button.collidepoint(
                mouse_pos
            )
        ):
            return "close_codex"

        for (
            item_id,
            rect
        ) in codex_buttons.get(
            "items",
            {}
        ).items():

            if rect.collidepoint(
                mouse_pos
            ):

                # 將目前點擊的物品交給CodexUI顯示
                self.codex_ui.select_item(
                    item_id
                )

                break

        return None


    def handle_wheel(
        self,
        event,
        mouse_pos
    ):
        """將Codex滾輪操作交給CodexUI。"""

        self.codex_ui.handle_wheel(
            event,
            mouse_pos
        )


    def stop_dragging(self):
        """停止拖曳Codex捲動條。"""

        self.codex_ui.dragging_scrollbar = (
            False
        )
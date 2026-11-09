# Hotbar 道具欄
import pygame

class HotbarController:

    def __init__(
        self,
        game,
        game_ui,
        interaction_ui,
        interaction_controller
    ):
        self.game = game
        self.game_ui = game_ui
        self.interaction_ui = interaction_ui
        self.interaction_controller = (
            interaction_controller
        )

        # 記錄目前選中的Hotbar格子
        self.selected_slot = 0

        # 記錄目前選中的物品
        self.selected_item = None

        # 記錄Hotbar目前翻頁位置
        self.offset = 0


    def get_selected_item(self):
        """取得目前Hotbar真正選中的item_id。"""

        visible_items = (
            self.game_ui.get_visible_inventory(
                self.game,
                self.offset
            )
        )

        if (
            self.selected_slot < 0
            or self.selected_slot
            >= len(visible_items)
        ):

            return None

        return visible_items[
            self.selected_slot
        ]


    def open_item(self, item_id):
        """從Hotbar開啟物品詳細內容。"""

        if item_id is None:
            return

        if item_id == "photo_1":

            self.interaction_controller.reset_interaction_focus()

            self.interaction_ui.open_photo(
                item_id,
                mode="inventory"
            )

            return

        self.interaction_controller.reset_interaction_focus()

        self.interaction_ui.open_object(
            item_id
        )
    def handle_wheel(
            self,
            event
    ):
        visible_items = (
            self.game_ui.get_visible_inventory(
                self.game,
                self.offset
            )
        )

        if not visible_items:
            return

        if event.y > 0:

            self.selected_slot = max(
                0,
                self.selected_slot - 1
            )

        elif event.y < 0:

            self.selected_slot = min(
                len(
                    visible_items
                ) - 1,
                self.selected_slot + 1
            )

    def select_slot(
        self,
        index,
        visible_items
    ):
        """選擇指定Hotbar格子並開啟物品。"""

        if index >= len(visible_items):
            return False

        self.selected_slot = index

        self.selected_item = (
            visible_items[index]
        )

        self.open_item(
            self.selected_item
        )

        return True

    def move_page_left(
        self,
    ):
        """Hotbar向左翻動一格。"""

        self.offset = max(
            0,
            self.offset - 1
        )

        self.selected_slot = 0

    def move_page_right(
        self,
        visible_slots
    ):
        """Hotbar向右翻動一格。"""

        max_offset = max(
            0,
            len(self.game.inventory)
            - visible_slots
        )

        self.offset = min(
            max_offset,
            self.offset + 1
        )

        self.selected_slot = 0

    def handle_key(
        self,
        event
    ):
        """處理Hotbar鍵盤操作。"""

        visible_items = (
            self.game_ui.get_visible_inventory(
                self.game,
                self.offset
            )
        )

        if event.key == pygame.K_LEFT:

            self.selected_slot = max(
                0,
                self.selected_slot - 1
            )

        elif event.key == pygame.K_RIGHT:

            if visible_items:

                self.selected_slot = min(
                    len(visible_items) - 1,
                    self.selected_slot + 1
                )

        elif (
            pygame.K_1
            <= event.key
            <= pygame.K_5
        ):

            index = (
                event.key
                - pygame.K_1
            )

            if index < len(
                visible_items
            ):

                self.selected_slot = index

                self.selected_item = (
                    visible_items[index]
                )

        elif event.key == pygame.K_RETURN:

            self.selected_item = (
                self.get_selected_item()
            )

            self.open_item(
                self.selected_item
            )
            
    def reset(self):
        """重設Hotbar操作狀態。"""

        self.selected_slot = 0
        self.selected_item = None
        self.offset = 0
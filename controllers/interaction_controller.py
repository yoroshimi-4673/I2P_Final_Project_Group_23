"""負責interaction的鍵盤焦點與輸入處理"""
import pygame
from managers.interaction_manager import (
    leave_puzzle,
    search_object
)

class InteractionController:

    def __init__(self, interaction_ui, story_manager, game):

        self.interaction_ui = interaction_ui
        self.story_manager = story_manager
        self.game = game

        # 紀錄目前鍵盤焦點控制向ID
        self.focus_id = None

        # 紀錄焦點所屬Interaction模式
        self.focus_mode = None

        # 保存上一幀產生的按鈕Rect
        self.last_buttons = {}

        self.pending_entry_rift = None
        
    def reset_interaction_focus(self):
        """重新開啟Interaction時清除上一個鍵盤焦點。"""

        self.focus_id = None
        self.focus_mode = None
        self.last_buttons = {}

    def get_interaction_rect_buttons(self, buttons):
        """只保留Interaction UI中可取得Rect的控制項。"""

        return {
            control_id: rect
            for control_id, rect in buttons.items()
            if isinstance(
                rect,
                pygame.Rect
            )
        }


    def ensure_interaction_focus(self, buttons):
        """確保目前Interaction模式具有有效鍵盤焦點。"""

        mode = self.interaction_ui.mode
        rect_buttons = self.get_interaction_rect_buttons(
            buttons
        )

        # 切換Interaction模式時重新選第一個控制項
        if mode != self.focus_mode:
            self.focus_mode = mode
            self.focus_id = None

        if not rect_buttons:
            self.focus_id = None
            return

        if self.focus_id not in rect_buttons:
            self.focus_id = next(
                iter(
                    rect_buttons
                )
            )


    def update_interaction_hover_focus(self, buttons, mouse_pos):
        """滑鼠移到控制項時同步鍵盤焦點。"""

        self.ensure_interaction_focus(
            buttons
        )

        for control_id, rect in (
            self.get_interaction_rect_buttons(
                buttons
            ).items()
        ):

            if rect.collidepoint(
                mouse_pos
            ):
                self.focus_id = control_id
                break


    def move_interaction_focus(
        self,
        direction_key,
        buttons
        ):
        """依照方向鍵移動Interaction UI目前焦點。"""

        self.ensure_interaction_focus(
            buttons
        )

        rect_buttons = self.get_interaction_rect_buttons(
            buttons
        )

        if (
            not rect_buttons
            or self.focus_id
            not in rect_buttons
        ):
            return

        current_rect = rect_buttons[
            self.focus_id
        ]

        current_center = pygame.Vector2(
            current_rect.center
        )

        candidates = []

        for control_id, rect in rect_buttons.items():

            if control_id == self.focus_id:
                continue

            center = pygame.Vector2(
                rect.center
            )

            delta = center - current_center

            valid = (
                direction_key == pygame.K_LEFT
                and delta.x < 0
            ) or (
                direction_key == pygame.K_RIGHT
                and delta.x > 0
            ) or (
                direction_key == pygame.K_UP
                and delta.y < 0
            ) or (
                direction_key == pygame.K_DOWN
                and delta.y > 0
            )

            if not valid:
                continue

            # 主方向距離優先，垂直偏差作為次要成本
            if direction_key in (
                pygame.K_LEFT,
                pygame.K_RIGHT
            ):
                score = (
                    abs(delta.x)
                    + abs(delta.y) * 1.5
                )

            else:
                score = (
                    abs(delta.y)
                    + abs(delta.x) * 1.5
                )

            candidates.append(
                (
                    score,
                    control_id
                )
            )

        if candidates:
            candidates.sort(
                key=lambda item: item[0]
            )

            self.focus_id = (
                candidates[0][1]
            )

            return

        # 指定方向沒有控制項時從另一側循環
        if direction_key == pygame.K_LEFT:
            self.focus_id = max(
                rect_buttons,
                key=lambda control_id: (
                    rect_buttons[
                        control_id
                    ].centerx
                )
            )

        elif direction_key == pygame.K_RIGHT:
            self.focus_id = min(
                rect_buttons,
                key=lambda control_id: (
                    rect_buttons[
                        control_id
                    ].centerx
                )
            )

        elif direction_key == pygame.K_UP:
            self.focus_id = max(
                rect_buttons,
                key=lambda control_id: (
                    rect_buttons[
                        control_id
                    ].centery
                )
            )

        elif direction_key == pygame.K_DOWN:
            self.focus_id = min(
                rect_buttons,
                key=lambda control_id: (
                    rect_buttons[
                        control_id
                    ].centery
                )
            )
    def activate_interaction_focus(self, buttons):
        """用Enter執行目前Interaction焦點控制項。"""

        self.ensure_interaction_focus(
            buttons
        )

        rect_buttons = self.get_interaction_rect_buttons(
            buttons
        )

        rect = rect_buttons.get(
            self.focus_id
        )

        if rect is None:
            return

        # 重用滑鼠點擊流程避免產生第二套互動邏輯
        self.handle_click(
            buttons,
            rect.center
        )

    def handle_key(self, event):

        """處理所有Interaction UI共用鍵盤操作。"""

        if not self.interaction_ui.is_open():
            return

        # 密碼介面仍保留數字鍵與Backspace快速輸入
        if self.interaction_ui.mode == "password":

            if (
                pygame.K_0
                <= event.key
                <= pygame.K_9
            ):
                digit = (
                    event.key
                    - pygame.K_0
                )

                self.interaction_ui.add_password_digit(
                    digit
                )
                return

            if event.key == pygame.K_BACKSPACE:
                self.interaction_ui.remove_password_digit()
                return

        # 四方向鍵統一移動目前Interaction焦點
        if event.key in (
            pygame.K_UP,
            pygame.K_DOWN,
            pygame.K_LEFT,
            pygame.K_RIGHT
        ):
            self.move_interaction_focus(
                event.key,
                self.last_buttons
            )
            return

        # Enter等同點擊目前鍵盤焦點控制項
        if event.key == pygame.K_RETURN:
            self.activate_interaction_focus(
                self.last_buttons
            )
            return

        # Escape統一處理返回或關閉互動視窗
        if event.key == pygame.K_ESCAPE:

            if self.interaction_ui.mode == "password":
                leave_puzzle(
                    self.game
                )
                self.interaction_ui.close()

            elif self.interaction_ui.parent_stack:
                self.interaction_ui.go_back()

            else:
                self.interaction_ui.close()

    def handle_click(
        self,
        buttons,
        mouse_pos
        ):
        """處理所有Interaction Popup滑鼠操作。"""

        if not self.interaction_ui.is_open():

            return

        mode = self.interaction_ui.mode

        # ========================================================
        # Container
        # ========================================================

        if mode == "container":

            if (
                "close" in buttons
                and buttons[
                    "close"
                ].collidepoint(
                    mouse_pos
                )
            ):

                self.interaction_ui.close()

                return

            for (
                child_id,
                rect
            ) in buttons.items():

                if child_id == "close":

                    continue

                if rect.collidepoint(
                    mouse_pos
                ):

                    self.open_container_child(
                        child_id
                    )

                    return

        # ========================================================
        # Searchable
        # ========================================================

        elif mode == "searchable":

            if buttons[
                "yes"
            ].collidepoint(
                mouse_pos
            ):

                self.interaction_ui.confirm_search()

            elif buttons[
                "no"
            ].collidepoint(
                mouse_pos
            ):

                self.interaction_ui.go_back()

        # ========================================================
        # Inspectable
        # ========================================================

        elif mode == "inspectable":

            if buttons[
                "back"
            ].collidepoint(
                mouse_pos
            ):

                self.interaction_ui.go_back()

        # ========================================================
        # Rift
        # ========================================================

        elif mode == "rift":

            if buttons[
                "enter"
            ].collidepoint(
                mouse_pos
            ):

                if (
                    self.interaction_ui.result[
                        "status"
                    ]
                    == "rift_available"
                ):

                    # 切換前先保存來源裂隙與預期目的空間
                    source_rift_id = (
                        self.interaction_ui.current_object_id
                    )

                    target_space = (
                        self.interaction_ui.result.get(
                            "target_space"
                        )
                    )

                    self.interaction_ui.confirm_rift()

                    # 成功切換後交給新Space使用對應入口出生點
                    if self.game.current_space == target_space:
                        self.pending_entry_rift = (
                            source_rift_id
                        )

            elif buttons[
                "cancel"
            ].collidepoint(
                mouse_pos
            ):

                self.interaction_ui.close()

        # ========================================================
        # Password
        # ========================================================

        elif mode == "password":

            for digit in (
                "0", "1", "2", "3", "4",
                "5", "6", "7", "8", "9"
            ):

                if (
                    digit in buttons
                    and buttons[
                        digit
                    ].collidepoint(
                        mouse_pos
                    )
                ):

                    self.interaction_ui.add_password_digit(
                        digit
                    )

                    return

            if buttons[
                "clear"
            ].collidepoint(
                mouse_pos
            ):

                self.interaction_ui.clear_password()

            elif buttons[
                "submit"
            ].collidepoint(
                mouse_pos
            ):

                self.interaction_ui.submit_password()

                if (
                    self.interaction_ui.result
                    is not None
                    and self.interaction_ui.result.get(
                        "status"
                    )
                    == "game_over"
                ):

                    self.interaction_ui.close()

            elif buttons[
                "back"
            ].collidepoint(
                mouse_pos
            ):

                leave_puzzle(
                    self.game
                )

                self.interaction_ui.close()

        # ========================================================
        # Photo
        # ========================================================

        elif mode == "photo":

            if buttons[
                "front"
            ].collidepoint(
                mouse_pos
            ):

                self.interaction_ui.view_photo_front()

            elif buttons[
                "back"
            ].collidepoint(
                mouse_pos
            ):

                result = (
                    self.interaction_ui
                    .view_photo_back()
                )

                if (
                    result.get(
                        "status"
                    )
                    == "photo_story_triggered"
                ):

                    self.interaction_ui.close()

                    self.story_manager.start_photo_story(
                        result
                    )

            elif (
                buttons[
                    "allow_close"
                ]
                and buttons[
                    "close"
                ].collidepoint(
                    mouse_pos
                )
            ):

                self.interaction_ui.close()

        # ========================================================
        # Door
        # ========================================================

        elif mode == "door":

            if (
                "enter" in buttons
                and buttons[
                    "enter"
                ].collidepoint(
                    mouse_pos
                )
            ):

                result = (
                    self.interaction_ui
                    .confirm_door()
                )

                if (
                    result.get(
                        "status"
                    )
                    == "chapter_end"
                ):

                    self.interaction_ui.close()

                    self.story_manager.start_chapter_end(
                        result
                    )

            elif (
                "cancel" in buttons
                and buttons[
                    "cancel"
                ].collidepoint(
                    mouse_pos
                )
            ):

                self.interaction_ui.close()

            elif (
                "close" in buttons
                and buttons[
                    "close"
                ].collidepoint(
                    mouse_pos
                )
            ):

                self.interaction_ui.close()

        # ========================================================
        # Item
        # ========================================================

        elif mode == "item":

            if buttons[
                "close"
            ].collidepoint(
                mouse_pos
            ):

                self.interaction_ui.close()

        # ========================================================
        # Item Notification
        # ========================================================

        elif mode == "item_notification":

            if buttons[
                "ok"
            ].collidepoint(
                mouse_pos
            ):

                self.interaction_ui.go_back()

        # ========================================================
        # Message
        # ========================================================

        elif mode == "message":

            if buttons[
                "ok"
            ].collidepoint(
                mouse_pos
            ):

                self.interaction_ui.go_back()

    def open_container_child(
        self,
        child_id
    ):
        """
        開啟Container子物件。

        已搜尋過的Searchable不再顯示是/否，
        而是直接顯示empty_text。
        """

        child = self.interaction_ui.objects[
            child_id
        ]

        if child[
            "type"
        ] == "searchable":

            item_id = child.get(
                "item"
            )

            if (
                item_id is not None
                and self.game.has_discovered_item(
                    item_id
                )
            ):

                self.interaction_ui.push_current()

                self.interaction_ui.current_object_id = (
                    child_id
                )

                self.interaction_ui.result = (
                    search_object(
                        self.game,
                        child_id,
                        self.interaction_ui.objects
                    )
                )

                self.interaction_ui.mode = (
                    "message"
                )

                return

        self.interaction_ui.open_child(
            child_id
        )

    def draw_focus(
        self,
        screen,
        buttons
    ):
        """繪製方向鍵與Enter目前作用的控制項外框。"""

        self.ensure_interaction_focus(
            buttons
        )

        rect = self.get_interaction_rect_buttons(
            buttons
        ).get(
            self.focus_id
        )

        if rect is None:
            return

        pygame.draw.rect(
            screen,
            (255, 225, 120),
            rect.inflate(6, 6),
            width=3,
            border_radius=9
        )


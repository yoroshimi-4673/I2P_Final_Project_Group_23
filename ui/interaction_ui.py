import pygame

from ui.dialogue_ui import wrap_text


class InteractionUI:
    """管理所有場景物件互動Popup與特殊UI。"""

    def __init__(
        self,
        game_ui,
        game,
        objects,
        levels
    ):
        self.game_ui = game_ui

        self.game = game

        self.objects = objects

        self.levels = levels

        self.mode = None

        self.current_object_id = None

        self.parent_stack = []

        self.result = None

        self.password_input = ""

        self.photo_id = None

        self.photo_mode = "inventory"

        self.photo_side = "front"

        self.notification = None


    # ========================================================
    # State
    # ========================================================

    def is_open(self):
        """判斷目前是否存在互動UI。"""

        return (
            self.mode is not None
        )


    def close(self):
        """關閉目前整個互動流程。"""

        self.mode = None

        self.current_object_id = None

        self.parent_stack = []

        self.result = None

        self.password_input = ""

        self.photo_id = None

        self.notification = None


    def go_back(self):
        """返回上一層互動。"""

        if not self.parent_stack:

            self.close()

            return

        previous = (
            self.parent_stack.pop()
        )

        self.mode = previous[
            "mode"
        ]

        self.current_object_id = (
            previous[
                "object_id"
            ]
        )

        self.result = previous.get(
            "result"
        )


    def push_current(self):
        """記錄目前互動供返回使用。"""

        self.parent_stack.append(
            {
                "mode": self.mode,

                "object_id": (
                    self.current_object_id
                ),

                "result": self.result
            }
        )


    # ========================================================
    # Open Interaction
    # ========================================================

    def open_object(
        self,
        object_id
    ):
        """依物件type決定要開啟哪一種UI。"""

        from interaction_manager import (
            get_container_info,
            inspect_object,
            get_rift_info,
            get_puzzle_info,
            get_door_info
        )

        self.current_object_id = (
            object_id
        )

        current_object = (
            self.objects[
                object_id
            ]
        )

        object_type = (
            current_object[
                "type"
            ]
        )

        if object_type == "container":

            self.mode = "container"

            self.result = (
                get_container_info(
                    self.game,
                    object_id,
                    self.objects
                )
            )

        elif object_type == "inspectable":

            self.mode = "inspectable"

            self.result = (
                inspect_object(
                    self.game,
                    object_id,
                    self.objects
                )
            )

        elif object_type == "rift":

            self.mode = "rift"

            self.result = (
                get_rift_info(
                    self.game,
                    object_id,
                    self.objects,
                    self.levels
                )
            )

        elif object_type == "puzzle":

            self.password_input = ""

            self.result = (
                get_puzzle_info(
                    self.game,
                    object_id,
                    self.objects
                )
            )

            if (
                self.result["status"]
                == "puzzle_solved"
            ):
                self.mode = "message"

            else:
                self.mode = "password"

        elif object_type == "door":

            self.mode = "door"

            self.result = (
                get_door_info(
                    self.game,
                    object_id,
                    self.objects
                )
            )

        elif object_type == "item":

            self.mode = "item"

            self.result = {
                "object_id": object_id,

                "name": current_object.get(
                    "name",
                    object_id
                ),

                "description": (
                    current_object.get(
                        "description",
                        ""
                    )
                )
            }


    # ========================================================
    # Child Object
    # ========================================================

    def open_child(
        self,
        child_id
    ):
        """從Container進入子物件。"""

        child = self.objects[
            child_id
        ]

        child_type = child[
            "type"
        ]

        self.push_current()

        self.current_object_id = (
            child_id
        )

        if child_type == "searchable":

            self.mode = "searchable"

            self.result = {
                "name": child[
                    "name"
                ],

                "description": child[
                    "description"
                ],

                "search_prompt": child[
                    "search_prompt"
                ]
            }

        elif child_type == "inspectable":

            from interaction_manager import (
                inspect_object
            )

            self.mode = (
                "inspectable"
            )

            self.result = (
                inspect_object(
                    self.game,
                    child_id,
                    self.objects
                )
            )

        elif child_type == "item":

            self.mode = "item"

            self.result = {
                "name": child[
                    "name"
                ],

                "description": child[
                    "description"
                ]
            }


    # ========================================================
    # Search
    # ========================================================

    def confirm_search(self):
        """正式執行Searchable搜尋。"""

        from interaction_manager import (
            search_object
        )

        result = search_object(
            self.game,
            self.current_object_id,
            self.objects
        )

        self.result = result

        if (
            result["status"]
            == "item_found"
        ):

            self.mode = (
                "item_notification"
            )

            self.notification = (
                result
            )

        else:

            self.mode = (
                "message"
            )


    # ========================================================
    # Rift
    # ========================================================

    def confirm_rift(self):
        """玩家確認後正式切換空間。"""

        from interaction_manager import (
            enter_rift
        )

        result = enter_rift(
            self.game,
            self.current_object_id,
            self.objects,
            self.levels
        )

        self.result = result

        if (
            result["status"]
            == "space_changed"
        ):

            self.close()


    # ========================================================
    # Password
    # ========================================================

    def add_password_digit(
        self,
        digit
    ):
        """加入密碼數字。"""

        if len(
            self.password_input
        ) >= 6:

            return

        self.password_input += str(
            digit
        )


    def remove_password_digit(self):
        """刪除最後一個密碼數字。"""

        self.password_input = (
            self.password_input[:-1]
        )


    def clear_password(self):
        """清空密碼。"""

        self.password_input = ""


    def submit_password(self):
        """送出目前密碼。"""

        from interaction_manager import (
            submit_password
        )

        result = submit_password(
            self.game,
            self.current_object_id,
            self.password_input,
            self.objects
        )

        self.result = result

        status = result[
            "status"
        ]

        if status in (
            "password_wrong",
            "incomplete_password",
            "invalid_password_format"
        ):

            self.password_input = ""

        elif status == "password_correct":

            self.password_input = ""

            reward_item = result.get(
                "reward_item"
            )

            if reward_item is not None:

                self.photo_id = (
                    reward_item
                )

                self.photo_mode = (
                    "story"
                )

                self.photo_side = (
                    "front"
                )

                self.mode = (
                    "photo"
                )


    # ========================================================
    # Photo
    # ========================================================

    def open_photo(
        self,
        photo_id,
        mode="inventory"
    ):
        """開啟照片檢視模式。"""

        self.photo_id = photo_id

        self.photo_mode = mode

        self.photo_side = "front"

        self.mode = "photo"


    def view_photo_front(self):
        """切換照片正面。"""

        self.photo_side = "front"


    def view_photo_back(self):
        """切換照片背面並處理Story事件。"""

        from interaction_manager import (
            view_photo_back
        )

        self.photo_side = "back"

        result = view_photo_back(
            self.game,
            self.photo_id,
            self.objects,
            self.photo_mode
        )

        self.result = result

        return result


    # ========================================================
    # Door
    # ========================================================

    def confirm_door(self):
        """確認進入出口門。"""

        from interaction_manager import (
            enter_door
        )

        result = enter_door(
            self.game,
            self.current_object_id,
            self.objects
        )

        self.result = result

        return result


    # ========================================================
    # Drawing Helpers
    # ========================================================

    def draw_modal_base(
        self,
        screen,
        width=460,
        height=300
    ):
        """繪製互動Popup共同底板。"""

        screen_width, screen_height = (
            screen.get_size()
        )

        overlay = pygame.Surface(
            (
                screen_width,
                screen_height
            ),
            pygame.SRCALPHA
        )

        overlay.fill(
            (0, 0, 0, 150)
        )

        screen.blit(
            overlay,
            (0, 0)
        )

        width = min(
            width,
            screen_width - 40
        )

        height = min(
            height,
            screen_height - 40
        )

        rect = pygame.Rect(
            (
                screen_width - width
            ) // 2,

            (
                screen_height - height
            ) // 2,

            width,
            height
        )

        pygame.draw.rect(
            screen,
            (42, 44, 56),
            rect,
            border_radius=12
        )

        pygame.draw.rect(
            screen,
            (220, 220, 230),
            rect,
            width=2,
            border_radius=12
        )

        return rect


    def draw_multiline_text(
        self,
        screen,
        text,
        x,
        y,
        width,
        font=None,
        color=(235, 235, 240)
    ):
        """繪製自動換行文字。"""

        if font is None:

            font = (
                self.game_ui.font_ui
            )

        lines = wrap_text(
            text,
            font,
            width
        )

        line_y = y

        for line in lines:

            surface = font.render(
                line,
                True,
                color
            )

            screen.blit(
                surface,
                (
                    x,
                    line_y
                )
            )

            line_y += (
                font.get_linesize()
                + 3
            )

        return line_y


    # ========================================================
    # Draw
    # ========================================================

    def draw(
        self,
        screen,
        mouse_pos
    ):
        """依照目前Interaction mode繪製UI。"""

        if not self.is_open():

            return {}

        handlers = {
            "container": self.draw_container,
            "searchable": self.draw_searchable,
            "inspectable": self.draw_inspectable,
            "rift": self.draw_rift,
            "password": self.draw_password,
            "photo": self.draw_photo,
            "door": self.draw_door,
            "item": self.draw_item,
            "item_notification": self.draw_item_notification,
            "message": self.draw_message
        }

        handler = handlers.get(
            self.mode
        )

        if handler is None:

            return {}

        return handler(
            screen,
            mouse_pos
        )


    # ========================================================
    # Container UI
    # ========================================================

    def draw_container(
        self,
        screen,
        mouse_pos
    ):
        """繪製Container Popup。"""

        modal = self.draw_modal_base(
            screen
        )

        title = self.game_ui.font_large.render(
            self.result["name"],
            True,
            (255, 220, 140)
        )

        screen.blit(
            title,
            (
                modal.x + 25,
                modal.y + 20
            )
        )

        y = self.draw_multiline_text(
            screen,
            self.result[
                "description"
            ],
            modal.x + 25,
            modal.y + 65,
            modal.width - 50
        )

        buttons = {}

        for (
            index,
            child
        ) in enumerate(
            self.result[
                "contents"
            ]
        ):

            rect = pygame.Rect(
                modal.x + 40,
                y + 20
                + index * 48,
                modal.width - 80,
                38
            )

            self.game_ui.draw_button(
                screen,
                child["name"],
                rect,
                rect.collidepoint(
                    mouse_pos
                )
            )

            buttons[
                child["object_id"]
            ] = rect

        buttons["close"] = pygame.Rect(
            modal.right - 45,
            modal.y + 12,
            30,
            30
        )

        self.game_ui.draw_button(
            screen,
            "X",
            buttons["close"],
            buttons["close"].collidepoint(
                mouse_pos
            ),
            bg_color=(110, 60, 60)
        )

        return buttons


    # ========================================================
    # Searchable
    # ========================================================

    def draw_searchable(
        self,
        screen,
        mouse_pos
    ):
        """繪製Searchable確認Popup。"""

        modal = self.draw_modal_base(
            screen
        )

        title = self.game_ui.font_large.render(
            self.result["name"],
            True,
            (255, 220, 140)
        )

        screen.blit(
            title,
            (
                modal.x + 25,
                modal.y + 20
            )
        )

        self.draw_multiline_text(
            screen,
            self.result[
                "search_prompt"
            ],
            modal.x + 25,
            modal.y + 80,
            modal.width - 50
        )

        yes_rect = pygame.Rect(
            modal.centerx - 130,
            modal.bottom - 70,
            110,
            40
        )

        no_rect = pygame.Rect(
            modal.centerx + 20,
            modal.bottom - 70,
            110,
            40
        )

        self.game_ui.draw_button(
            screen,
            "是",
            yes_rect,
            yes_rect.collidepoint(
                mouse_pos
            )
        )

        self.game_ui.draw_button(
            screen,
            "否",
            no_rect,
            no_rect.collidepoint(
                mouse_pos
            )
        )

        return {
            "yes": yes_rect,
            "no": no_rect
        }


    # ========================================================
    # Inspectable
    # ========================================================

    def draw_inspectable(
        self,
        screen,
        mouse_pos
    ):
        """繪製一般調查Popup。"""

        modal = self.draw_modal_base(
            screen
        )

        title = self.game_ui.font_large.render(
            self.result["name"],
            True,
            (255, 220, 140)
        )

        screen.blit(
            title,
            (
                modal.x + 25,
                modal.y + 20
            )
        )

        self.draw_multiline_text(
            screen,
            self.result[
                "description"
            ],
            modal.x + 25,
            modal.y + 75,
            modal.width - 50
        )

        back_rect = pygame.Rect(
            modal.centerx - 60,
            modal.bottom - 65,
            120,
            38
        )

        self.game_ui.draw_button(
            screen,
            "返回",
            back_rect,
            back_rect.collidepoint(
                mouse_pos
            )
        )

        return {
            "back": back_rect
        }


    # ========================================================
    # Rift
    # ========================================================

    def draw_rift(
        self,
        screen,
        mouse_pos
    ):
        """繪製Rift確認Popup。"""

        modal = self.draw_modal_base(
            screen
        )

        title = self.game_ui.font_large.render(
            self.result[
                "name"
            ],
            True,
            (180, 210, 255)
        )

        screen.blit(
            title,
            (
                modal.x + 25,
                modal.y + 20
            )
        )

        self.draw_multiline_text(
            screen,
            self.result[
                "description"
            ],
            modal.x + 25,
            modal.y + 70,
            modal.width - 50
        )

        enter_rect = pygame.Rect(
            modal.centerx - 150,
            modal.bottom - 70,
            135,
            40
        )

        cancel_rect = pygame.Rect(
            modal.centerx + 15,
            modal.bottom - 70,
            135,
            40
        )

        if (
            self.result[
                "status"
            ]
            == "rift_available"
        ):

            enter_text = (
                "進入"
                + self.result[
                    "target_name"
                ]
            )

        else:

            enter_text = "無法進入"

        self.game_ui.draw_button(
            screen,
            enter_text,
            enter_rect,
            enter_rect.collidepoint(
                mouse_pos
            ),
            enabled=(
                self.result[
                    "status"
                ]
                == "rift_available"
            )
        )

        self.game_ui.draw_button(
            screen,
            "取消",
            cancel_rect,
            cancel_rect.collidepoint(
                mouse_pos
            )
        )

        return {
            "enter": enter_rect,
            "cancel": cancel_rect
        }


    # ========================================================
    # Password
    # ========================================================

    def draw_password(
        self,
        screen,
        mouse_pos
    ):
        """繪製六位數密碼UI。"""

        modal = self.draw_modal_base(
            screen,
            width=520,
            height=500
        )

        title = self.game_ui.font_large.render(
            "六位數密碼鎖",
            True,
            (255, 220, 140)
        )

        screen.blit(
            title,
            title.get_rect(
                center=(
                    modal.centerx,
                    modal.y + 35
                )
            )
        )

        attempts = self.result.get(
            "remaining_attempts",
            3
        )

        attempts_surface = self.game_ui.font_small.render(
            f"剩餘嘗試次數：{attempts}",
            True,
            (235, 190, 160)
        )

        screen.blit(
            attempts_surface,
            attempts_surface.get_rect(
                center=(
                    modal.centerx,
                    modal.y + 70
                )
            )
        )

        box_size = 48
        gap = 10

        total_width = (
            6 * box_size
            + 5 * gap
        )

        start_x = (
            modal.centerx
            - total_width // 2
        )

        box_y = modal.y + 105

        for index in range(6):

            rect = pygame.Rect(
                start_x
                + index
                * (
                    box_size
                    + gap
                ),
                box_y,
                box_size,
                box_size
            )

            pygame.draw.rect(
                screen,
                (30, 32, 40),
                rect,
                border_radius=5
            )

            pygame.draw.rect(
                screen,
                (210, 210, 220),
                rect,
                width=2,
                border_radius=5
            )

            if (
                index
                < len(
                    self.password_input
                )
            ):

                digit = self.password_input[
                    index
                ]

                surface = self.game_ui.font_large.render(
                    digit,
                    True,
                    (245, 245, 245)
                )

                screen.blit(
                    surface,
                    surface.get_rect(
                        center=rect.center
                    )
                )

        buttons = {}

        keypad_y = modal.y + 190

        button_width = 65
        button_height = 42
        button_gap = 10

        digits = [
            "1", "2", "3",
            "4", "5", "6",
            "7", "8", "9"
        ]

        for index, digit in enumerate(
            digits
        ):

            row = index // 3
            col = index % 3

            rect = pygame.Rect(
                modal.centerx
                - (
                    button_width
                    * 3
                    + button_gap
                    * 2
                ) // 2
                + col
                * (
                    button_width
                    + button_gap
                ),

                keypad_y
                + row
                * (
                    button_height
                    + button_gap
                ),

                button_width,
                button_height
            )

            self.game_ui.draw_button(
                screen,
                digit,
                rect,
                rect.collidepoint(
                    mouse_pos
                )
            )

            buttons[
                digit
            ] = rect

        zero_rect = pygame.Rect(
            modal.centerx
            - button_width // 2,

            keypad_y
            + 3
            * (
                button_height
                + button_gap
            ),

            button_width,
            button_height
        )

        self.game_ui.draw_button(
            screen,
            "0",
            zero_rect,
            zero_rect.collidepoint(
                mouse_pos
            )
        )

        buttons["0"] = zero_rect

        clear_rect = pygame.Rect(
            modal.x + 45,
            modal.bottom - 65,
            100,
            38
        )

        submit_rect = pygame.Rect(
            modal.centerx - 50,
            modal.bottom - 65,
            100,
            38
        )

        back_rect = pygame.Rect(
            modal.right - 145,
            modal.bottom - 65,
            100,
            38
        )

        self.game_ui.draw_button(
            screen,
            "清除",
            clear_rect,
            clear_rect.collidepoint(
                mouse_pos
            )
        )

        self.game_ui.draw_button(
            screen,
            "確認",
            submit_rect,
            submit_rect.collidepoint(
                mouse_pos
            )
        )

        self.game_ui.draw_button(
            screen,
            "返回",
            back_rect,
            back_rect.collidepoint(
                mouse_pos
            )
        )

        buttons["clear"] = clear_rect
        buttons["submit"] = submit_rect
        buttons["back"] = back_rect

        if (
            self.result is not None
            and self.result.get(
                "message"
            )
        ):

            message = self.result[
                "message"
            ]

            surface = self.game_ui.font_small.render(
                message,
                True,
                (255, 170, 150)
            )

            screen.blit(
                surface,
                surface.get_rect(
                    center=(
                        modal.centerx,
                        modal.bottom - 100
                    )
                )
            )

        return buttons


    # ========================================================
    # Photo
    # ========================================================

    def draw_photo(
        self,
        screen,
        mouse_pos
    ):
        """繪製照片正反面。"""

        modal = self.draw_modal_base(
            screen,
            width=560,
            height=420
        )

        photo = self.objects[
            self.photo_id
        ]

        title = self.game_ui.font_large.render(
            photo.get(
                "name",
                "照片"
            ),
            True,
            (255, 220, 140)
        )

        screen.blit(
            title,
            title.get_rect(
                center=(
                    modal.centerx,
                    modal.y + 35
                )
            )
        )

        picture_rect = pygame.Rect(
            modal.centerx - 100,
            modal.y + 75,
            200,
            140
        )

        self.game_ui.draw_placeholder_rect(
            screen,
            picture_rect,
            (
                "照片正面 Placeholder"
                if self.photo_side
                == "front"
                else
                "照片背面 Placeholder"
            ),
            color=(115, 105, 95)
        )

        if self.photo_side == "front":

            text = photo.get(
                "description",
                ""
            )

        else:

            text = photo.get(
                "back_text",
                ""
            )

        self.draw_multiline_text(
            screen,
            text,
            modal.x + 40,
            modal.y + 235,
            modal.width - 80
        )

        front_rect = pygame.Rect(
            modal.x + 50,
            modal.bottom - 65,
            130,
            38
        )

        back_rect = pygame.Rect(
            modal.centerx - 65,
            modal.bottom - 65,
            130,
            38
        )

        close_rect = pygame.Rect(
            modal.right - 180,
            modal.bottom - 65,
            130,
            38
        )

        self.game_ui.draw_button(
            screen,
            "查看正面",
            front_rect,
            front_rect.collidepoint(
                mouse_pos
            )
        )

        self.game_ui.draw_button(
            screen,
            "查看背面",
            back_rect,
            back_rect.collidepoint(
                mouse_pos
            )
        )

        # Story模式尚未看背面前禁止離開。
        allow_close = (
            self.photo_mode
            != "story"
            or self.photo_side
            == "back"
        )

        self.game_ui.draw_button(
            screen,
            "返回",
            close_rect,
            close_rect.collidepoint(
                mouse_pos
            ),
            enabled=allow_close
        )

        return {
            "front": front_rect,
            "back": back_rect,
            "close": close_rect,
            "allow_close": allow_close
        }


    # ========================================================
    # Door
    # ========================================================

    def draw_door(
        self,
        screen,
        mouse_pos
    ):
        """繪製出口門確認UI。"""

        modal = self.draw_modal_base(
            screen
        )

        title = self.game_ui.font_large.render(
            self.result[
                "name"
            ],
            True,
            (255, 220, 140)
        )

        screen.blit(
            title,
            (
                modal.x + 25,
                modal.y + 20
            )
        )

        self.draw_multiline_text(
            screen,
            self.result[
                "description"
            ],
            modal.x + 25,
            modal.y + 80,
            modal.width - 50
        )

        buttons = {}

        if (
            self.result[
                "status"
            ]
            == "door_available"
        ):

            enter_rect = pygame.Rect(
                modal.centerx - 130,
                modal.bottom - 70,
                110,
                40
            )

            cancel_rect = pygame.Rect(
                modal.centerx + 20,
                modal.bottom - 70,
                110,
                40
            )

            self.game_ui.draw_button(
                screen,
                "進入",
                enter_rect,
                enter_rect.collidepoint(
                    mouse_pos
                )
            )

            self.game_ui.draw_button(
                screen,
                "取消",
                cancel_rect,
                cancel_rect.collidepoint(
                    mouse_pos
                )
            )

            buttons["enter"] = (
                enter_rect
            )

            buttons["cancel"] = (
                cancel_rect
            )

        else:

            close_rect = pygame.Rect(
                modal.centerx - 60,
                modal.bottom - 70,
                120,
                40
            )

            self.game_ui.draw_button(
                screen,
                "返回",
                close_rect,
                close_rect.collidepoint(
                    mouse_pos
                )
            )

            buttons["close"] = (
                close_rect
            )

        return buttons


    # ========================================================
    # Item Popup
    # ========================================================

    def draw_item(
        self,
        screen,
        mouse_pos
    ):
        """繪製Hotbar物品詳細資料。"""

        modal = self.draw_modal_base(
            screen
        )

        title = self.game_ui.font_large.render(
            self.result[
                "name"
            ],
            True,
            (255, 220, 140)
        )

        screen.blit(
            title,
            (
                modal.x + 25,
                modal.y + 20
            )
        )

        icon_rect = pygame.Rect(
            modal.x + 30,
            modal.y + 75,
            110,
            110
        )

        self.game_ui.draw_placeholder_rect(
            screen,
            icon_rect,
            "Item Placeholder"
        )

        self.draw_multiline_text(
            screen,
            self.result[
                "description"
            ],
            modal.x + 165,
            modal.y + 80,
            modal.width - 195
        )

        close_rect = pygame.Rect(
            modal.centerx - 60,
            modal.bottom - 65,
            120,
            38
        )

        self.game_ui.draw_button(
            screen,
            "關閉",
            close_rect,
            close_rect.collidepoint(
                mouse_pos
            )
        )

        return {
            "close": close_rect
        }


    # ========================================================
    # Item Notification
    # ========================================================

    def draw_item_notification(
        self,
        screen,
        mouse_pos
    ):
        """繪製新物品取得通知。"""

        modal = self.draw_modal_base(
            screen,
            width=380,
            height=240
        )

        title = self.game_ui.font_large.render(
            "獲得新物品！",
            True,
            (255, 220, 120)
        )

        screen.blit(
            title,
            title.get_rect(
                center=(
                    modal.centerx,
                    modal.y + 45
                )
            )
        )

        item_name = self.notification[
            "name"
        ]

        name_surface = self.game_ui.font_ui.render(
            item_name,
            True,
            (245, 245, 245)
        )

        screen.blit(
            name_surface,
            name_surface.get_rect(
                center=(
                    modal.centerx,
                    modal.centery
                )
            )
        )

        ok_rect = pygame.Rect(
            modal.centerx - 55,
            modal.bottom - 60,
            110,
            36
        )

        self.game_ui.draw_button(
            screen,
            "確定",
            ok_rect,
            ok_rect.collidepoint(
                mouse_pos
            )
        )

        return {
            "ok": ok_rect
        }


    # ========================================================
    # Message
    # ========================================================

    def draw_message(
        self,
        screen,
        mouse_pos
    ):
        """繪製單純訊息Popup。"""

        modal = self.draw_modal_base(
            screen,
            width=420,
            height=220
        )

        text = self.result.get(
            "description",
            self.result.get(
                "message",
                ""
            )
        )

        self.draw_multiline_text(
            screen,
            text,
            modal.x + 30,
            modal.y + 45,
            modal.width - 60
        )

        ok_rect = pygame.Rect(
            modal.centerx - 55,
            modal.bottom - 60,
            110,
            36
        )

        self.game_ui.draw_button(
            screen,
            "確定",
            ok_rect,
            ok_rect.collidepoint(
                mouse_pos
            )
        )

        return {
            "ok": ok_rect
        }
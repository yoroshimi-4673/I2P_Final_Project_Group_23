import pygame

from ui.dialogue_ui import wrap_text


class InteractionUI:
    """管理所有場景物件互動Popup與特殊UI。"""

    def __init__(
        self,
        game_ui,
        game,
        objects,
        levels,
        puzzle_controller
    ):
        self.game_ui = game_ui

        self.game = game

        self.objects = objects

        self.levels = levels

        self.mode = None

        self.current_object_id = None

        self.parent_stack = []

        self.result = None

        self.puzzle_controller = puzzle_controller

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

        self.puzzle_controller.close_puzzle()

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
        if self.mode == "container":
            from managers.interaction_manager import get_container_info

            self.result = get_container_info(self.game, self.current_object_id, self.objects)


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

    def open_message(
        self,
        message,
        object_id=None
    ):
        """開啟單純訊息視窗。"""

        self.current_object_id = (
            object_id
        )

        self.result = {
            "status": "message",
            "description": message
        }

        self.mode = "message"


    def open_readable(
        self,
        object_id
    ):
        """開啟可閱讀圖片。"""

        self.current_object_id = (
            object_id
        )

        current_object = (
            self.objects[
                object_id
            ]
        )

        self.result = {
            "status": "readable",
            "object_id": object_id,
            "name": current_object.get(
                "name",
                object_id
            ),
            "description": current_object.get(
                "description",
                ""
            ),
            "asset": current_object.get(
                "reader_asset",
                current_object.get("ui_asset")
            )
        }

        self.mode = "readable"


    def draw_readable(
        self,
        screen,
        mouse_pos
    ):
        """繪製置中的可閱讀文件。"""

        modal = self.draw_modal_base(
            screen,
            width=600,
            height=500
        )

        image_rect = pygame.Rect(
            modal.x + 60,
            modal.y + 40,
            modal.width - 120,
            modal.height - 120
        )

        self.game_ui.draw_asset(
            screen,
            self.result.get(
                "asset"
            ),
            image_rect
        )

        close_rect = pygame.Rect(
            modal.centerx - 55,
            modal.bottom - 60,
            110,
            36
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


    def open_object(
        self,
        object_id
    ):
        """依物件type決定要開啟哪一種UI。"""

        from managers.interaction_manager import (
            get_container_info,
            inspect_object,
            get_rift_info,
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

        if current_object.get("reader_type") == "diary":
            self.puzzle_controller.diary_reader_page = 0
            self.open_diary_reader(object_id)
            return

        if object_type == "container":

            self.mode = "container"

            self.result = (
                get_container_info(
                    self.game,
                    object_id,
                    self.objects
                )
            )

        elif object_type == "searchable":

            self.mode = "searchable"

            self.result = {
                "status": "searchable",
                "object_id": object_id,
                "name": current_object["name"],
                "description": current_object.get(
                    "description",
                    ""
                ),
                "search_prompt": current_object.get(
                    "search_prompt",
                    "要繼續搜索嗎？"
                )
            }

        elif object_type == "readable":

            self.open_readable(object_id)

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
                    self.game_ui.get_item_display_value(
                        object_id, "description", self.game, default=""
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

            from managers.interaction_manager import (
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
                "object_id": child_id,  # 保留子道具編號供圖片查詢
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

        from managers.interaction_manager import (
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

        from managers.interaction_manager import (
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

        from managers.interaction_manager import (
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

        from managers.interaction_manager import (
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
            "sequence": self.draw_sequence,
            "exit_confirmation": self.draw_exit_confirmation,
            "diary_drag": self.draw_diary_drag,
            "diary_exit_confirmation": self.draw_diary_exit_confirmation,
            "diary_reader": self.draw_diary_reader,
            "anchor_fragments": self.draw_anchor_fragments,
            "multi_input": self.draw_multi_input,
            "photo": self.draw_photo,
            "door": self.draw_door,
            "item": self.draw_item,
            "item_notification": self.draw_item_notification,
            "readable": self.draw_readable,
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

            # 容器內道具共用相同圖片入口
            self.game_ui.draw_item_asset(
                screen, child["object_id"],
                pygame.Rect(rect.x + 4, rect.y + 2, 34, 34), padding=2
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

    def draw_sequence(self, screen, mouse_pos):
        """依控制器目前順序繪製日記頁卡片。"""

        modal = self.draw_modal_base(screen, width=700, height=500)
        title = self.game_ui.font_large.render("陪伴日記", True, (255, 220, 140))
        screen.blit(title, title.get_rect(center=(modal.centerx, modal.y + 35)))
        page_ids = self.puzzle_controller.puzzle.get("answer", [])
        selected = self.puzzle_controller.sequence_input
        buttons = {}
        card_width = (modal.width - 80) // max(1, len(page_ids))

        for index, item_id in enumerate(page_ids):
            rect = pygame.Rect(modal.x + 40 + index * card_width, modal.y + 85,
                               card_width - 15, 145)
            label = self.objects.get(item_id, {}).get("name", item_id)
            self.game_ui.draw_button(screen, label, rect, rect.collidepoint(mouse_pos))
            image_rect = rect.inflate(-12, -36)
            if self.objects.get(item_id, {}).get("ui_asset"):
                pygame.draw.rect(screen, (55, 58, 72), rect, border_radius=6)
                self.game_ui.draw_item_asset(screen, item_id, image_rect)
                text = self.game_ui.font_small.render(label, True, (240, 240, 245))
                screen.blit(text, text.get_rect(center=(rect.centerx, rect.bottom - 14)))
            if item_id in selected:
                pygame.draw.rect(screen, (255, 220, 140), rect, 3, border_radius=6)
            buttons["page:" + item_id] = rect

        order = [self.objects.get(item, {}).get("name", item) for item in selected]
        order_text = "目前順序：" + " → ".join(
            f"{index + 1}. {name}" for index, name in enumerate(order)
        )
        self.draw_multiline_text(screen, order_text, modal.x + 35, modal.y + 250,
                                 modal.width - 70)
        message = (self.result or {}).get("message", "")
        self.draw_multiline_text(screen, message, modal.x + 35, modal.y + 320,
                                 modal.width - 70, font=self.game_ui.font_small)
        for index, (key, label) in enumerate((("clear", "清除"), ("submit", "確認"),
                                               ("back", "返回"))):
            rect = pygame.Rect(modal.x + 35 + index * (modal.width - 70) // 3,
                               modal.bottom - 60, (modal.width - 100) // 3, 36)
            self.game_ui.draw_button(screen, label, rect, rect.collidepoint(mouse_pos))
            buttons[key] = rect
        return buttons


    def draw_u_groove(self, screen, rect, label, filled=False):
        """沿用原型上方開口與三面槽牆造型。"""

        wall_x = max(1, self.game_ui.scale_x(screen, 25))
        wall_y = max(1, self.game_ui.scale_y(screen, 25))
        fill = (100, 105, 115) if filled else (78, 81, 94)
        border = (180, 185, 198)
        # 三面牆直接畫成凹形，保留透明的上方開口
        points = [(rect.left, rect.top), (rect.left + wall_x, rect.top),
                  (rect.left + wall_x, rect.bottom - wall_y),
                  (rect.right - wall_x, rect.bottom - wall_y),
                  (rect.right - wall_x, rect.top), (rect.right, rect.top),
                  (rect.right, rect.bottom), (rect.left, rect.bottom)]
        pygame.draw.polygon(screen, fill, points)
        pygame.draw.polygon(screen, border, points, width=2)
        text = self.game_ui.font_ui.render(label, True, (205, 210, 220))
        screen.blit(text, text.get_rect(center=(rect.centerx,
                    rect.bottom + self.game_ui.scale_y(screen, 25))))


    def draw_anchor_fragments(self, screen, mouse_pos):
        """繪製持續保存狀態的三枚錨點凹槽。"""

        overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        overlay.fill((20, 20, 25, 210))
        screen.blit(overlay, (0, 0))
        layout = self.game_ui.ui_layout["puzzle_layouts"]["anchor_fragment_slots"]
        title = self.game_ui.font_large.render(layout["title"], True, (255, 220, 140))
        screen.blit(title, title.get_rect(center=(screen.get_width() // 2,
                    self.game_ui.scale_y(screen, 55))))
        buttons = {}
        slots = self.puzzle_controller.anchor_slots
        for slot_id, data in layout["slots"].items():
            rect = self.game_ui.scale_rect(screen, data)
            item_id = slots.get(slot_id)
            self.draw_u_groove(screen, rect, data["label"], filled=item_id is not None)
            if item_id:
                icon = rect.inflate(-self.game_ui.scale_x(screen, 60),
                                    -self.game_ui.scale_y(screen, 70))
                if not self.game_ui.draw_item_asset(screen, item_id, icon):
                    self.draw_multiline_text(screen, self.objects[item_id]["name"],
                                             icon.x, icon.centery, icon.width,
                                             font=self.game_ui.font_small)
            buttons["slot:" + slot_id] = rect

        for index, item_id in enumerate(("past_fragment", "present_fragment", "future_fragment")):
            if not self.game.has_item(item_id) or item_id in slots.values():
                continue
            rect = self.game_ui.scale_rect(screen, {
                "x": 90 + index * 220, "y": 500, "width": 180, "height": 48
            })
            position = self.puzzle_controller.anchor_fragment_positions.get(item_id)
            if position is not None:
                rect.topleft = position  # 拖曳碎片依滑鼠位置即時繪製
            pygame.draw.rect(screen, (65, 68, 85), rect, border_radius=5)
            if not self.game_ui.draw_item_asset(screen, item_id, rect):
                self.game_ui.draw_button(screen, self.objects[item_id]["name"], rect,
                                         rect.collidepoint(mouse_pos))
            buttons["fragment:" + item_id] = rect

        close = self.game_ui.scale_rect(screen, {
            "x": 700, "y": 20, "width": 80, "height": 36
        })
        self.game_ui.draw_button(screen, "關閉", close, close.collidepoint(mouse_pos))
        buttons["close"] = close
        self.draw_multiline_text(screen, (self.result or {}).get("message", ""),
                                 self.game_ui.scale_x(screen, 100),
                                 self.game_ui.scale_y(screen, 565),
                                 self.game_ui.scale_x(screen, 600),
                                 font=self.game_ui.font_small)
        return buttons


    def draw_white_wall(self, screen):
        """由剩餘次數與版面設定推導白牆範圍。"""

        if self.puzzle_controller.current_puzzle_id != "anchor_age_verification":
            return
        config = self.game_ui.ui_layout["chapter2_effects"]["white_wall"]
        stage = self.puzzle_controller.puzzle_manager.get_failure_stage(
            "anchor_age_verification"
        )
        ratio = config["stages"].get(stage, 0)
        width = int(screen.get_width() * ratio)
        if width > 0:
            wall = pygame.Surface((width, screen.get_height()), pygame.SRCALPHA)
            wall.fill((*config["color"], config["alpha"]))
            screen.blit(wall, (screen.get_width() - width, 0))


    def draw_multi_input(self, screen, mouse_pos):
        """分別顯示三個時間年齡及共用數字輸入。"""

        self.draw_white_wall(screen)
        if (self.puzzle_controller.last_result or {}).get("status") == "final_failure_pending":
            # 白牆吞沒後先保留畫面等待玩家確認
            overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
            overlay.fill((20, 20, 25, 80))
            screen.blit(overlay, (0, 0))
            message = self.puzzle_controller.last_result.get("message", "白牆吞沒了整條走廊。")
            self.draw_multiline_text(screen, message, self.game_ui.scale_x(screen, 100),
                                     self.game_ui.scale_y(screen, 240),
                                     self.game_ui.scale_x(screen, 600), color=(45, 45, 50))
            rect = self.game_ui.scale_rect(screen, {"x": 320, "y": 380, "width": 160, "height": 60})
            self.game_ui.draw_button(screen, "確定", rect, rect.collidepoint(mouse_pos))
            return {"ack_failure": rect}
        overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        overlay.fill((20, 20, 25, 150))
        screen.blit(overlay, (0, 0))
        layout = self.game_ui.ui_layout["puzzle_layouts"]["anchor_age_verification"]
        title = self.game_ui.font_large.render(layout["title"], True, (255, 220, 140))
        screen.blit(title, title.get_rect(center=(screen.get_width() // 2,
                    self.game_ui.scale_y(screen, 100))))
        buttons = {}
        for field_id, data in layout["fields"].items():
            rect = self.game_ui.scale_rect(screen, data)
            label = self.game_ui.font_ui.render(data["label"], True, (235, 235, 240))
            screen.blit(label, label.get_rect(midbottom=(rect.centerx, rect.top - 8)))
            pygame.draw.rect(screen, (42, 44, 56), rect, border_radius=6)
            active = self.puzzle_controller.active_field_id == field_id
            pygame.draw.rect(screen, (255, 220, 140) if active else (160, 165, 180),
                             rect, 3 if active else 2, border_radius=6)
            text = self.game_ui.font_large.render(
                self.puzzle_controller.multi_input.get(field_id, ""), True, (245, 245, 245)
            )
            screen.blit(text, text.get_rect(center=rect.center))
            buttons["field:" + field_id] = rect

        for index in range(10):
            rect = self.game_ui.scale_rect(screen, {
                "x": 140 + index * 52, "y": 325, "width": 44, "height": 36
            })
            self.game_ui.draw_button(screen, str(index), rect, rect.collidepoint(mouse_pos))
            buttons[str(index)] = rect
        for key, label, data in (
            ("clear", "清除此欄", {"x": 80, "y": 380, "width": 160, "height": 60}),
            ("submit", layout["submit"]["label"], layout["submit"]),
            ("back", "返回", {"x": 560, "y": 380, "width": 160, "height": 60})
        ):
            rect = self.game_ui.scale_rect(screen, data)
            self.game_ui.draw_button(screen, label, rect, rect.collidepoint(mouse_pos))
            buttons[key] = rect
        self.draw_multiline_text(screen, (self.result or {}).get("message", ""),
                                 self.game_ui.scale_x(screen, 100),
                                 self.game_ui.scale_y(screen, 465),
                                 self.game_ui.scale_x(screen, 600),
                                 font=self.game_ui.font_small)
        return buttons


    def draw_binary_lock(self, screen):
        """繪製 C 空間的鎖面與圖片按鍵。"""
        layout = self.game_ui.ui_layout["puzzle_layouts"]["chapter1_binary_lock"]
        modal = self.draw_modal_base(screen, width=520, height=480)
        lock = layout["lock_rect"]
        scale_x = modal.width / 520
        scale_y = modal.height / 480
        target = pygame.Rect(
            modal.x + round(lock["x"] * scale_x),
            modal.y + round(lock["y"] * scale_y),
            round(lock["width"] * scale_x),
            round(lock["height"] * scale_y),
        )
        title = self.game_ui.font_large.render(
            self.objects[self.current_object_id]["name"], True, (255, 220, 140)
        )
        screen.blit(title, title.get_rect(center=(modal.centerx, modal.y + round(30 * scale_y))))
        attempts = self.puzzle_controller.remaining_attempts
        if attempts is not None:
            label = self.game_ui.font_small.render(f"剩餘嘗試次數：{attempts}", True, (235, 190, 160))
            screen.blit(label, label.get_rect(center=(modal.centerx, modal.y + round(61 * scale_y))))

        buttons = {}
        asset = layout["asset"]
        if self.game_ui.draw_asset(screen, asset, target):
            image_rect = self.game_ui.get_fitted_image_rect(self.game_ui.load_image(asset), target)
            slots = layout["input_slots"]
            for index, digit in enumerate(self.puzzle_controller.input_text):
                text = self.game_ui.font_large.render(digit, True, (225, 255, 255))
                x_ratio = slots["first_x_ratio"] + index * slots["step_ratio"]
                center = (
                    image_rect.x + round(image_rect.width * x_ratio),
                    image_rect.y + round(image_rect.height * slots["y_ratio"]),
                )
                screen.blit(text, text.get_rect(center=center))
            for digit in ("1", "0"):
                data = layout["buttons"][digit]
                buttons[digit] = pygame.Rect(
                    image_rect.x + round(image_rect.width * data["x_ratio"]),
                    image_rect.y + round(image_rect.height * data["y_ratio"]),
                    round(image_rect.width * data["width_ratio"]),
                    round(image_rect.height * data["height_ratio"]),
                )
            if layout.get("debug_hitboxes", False):
                pygame.draw.rect(screen, (255, 80, 80), buttons["1"], width=2)
                pygame.draw.rect(screen, (80, 220, 120), buttons["0"], width=2)

        hint = self.game_ui.font_small.render("Esc 返回", True, (210, 210, 220))
        screen.blit(hint, hint.get_rect(center=(modal.centerx, modal.bottom - 25)))
        return buttons

    def draw_password(
        self,
        screen,
        mouse_pos
    ):
        """沿用密碼版面並讀取謎題控制器狀態。"""

        if self.puzzle_controller.current_puzzle_id == "chapter1_password":
            return self.draw_binary_lock(screen)

        modal = self.draw_modal_base(screen, width=520, height=500)

        title = self.game_ui.font_large.render(
            self.objects[self.current_object_id]["name"],
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

        attempts = self.puzzle_controller.remaining_attempts

        if attempts is not None:  # 不限次數的謎題不顯示次數文字
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

        puzzle = self.puzzle_controller.puzzle
        input_length = puzzle.get("length", 0)
        input_text = self.puzzle_controller.input_text
        total_width = input_length * box_size + max(0, input_length - 1) * gap

        start_x = (
            modal.centerx
            - total_width // 2
        )

        box_y = modal.y + 105

        for index in range(input_length):

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
                    input_text
                )
            ):

                digit = input_text[
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
            self.puzzle_controller.last_result is not None
            and self.puzzle_controller.last_result.get(
                "message"
            )
        ):

            message = self.puzzle_controller.last_result[
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

        # 照片正反面沿用同一圖片繪製入口
        asset_key = "ui_asset" if self.photo_side == "front" else "ui_back_asset"
        picture_drawn = self.game_ui.draw_item_asset(
            screen,
            self.photo_id,
            picture_rect,
            asset_key=asset_key
        )

        if not picture_drawn:
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

        # 依道具編號繪圖並保留缺圖備援
        if not self.game_ui.draw_item_asset(
            screen, self.result.get("object_id", self.current_object_id), icon_rect, game=self.game
        ):
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
            height=340
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

        # 通知依道具編號顯示共用圖片
        icon_rect = pygame.Rect(modal.centerx - 60, modal.y + 75, 120, 120)
        if not self.game_ui.draw_item_asset(
            screen, self.notification.get("item_id"), icon_rect, game=self.game
        ):
            self.game_ui.draw_placeholder_rect(screen, icon_rect, "Item Placeholder")

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
                    modal.y + 225
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


    def open_exit_confirmation(
        self,
        object_id
    ):
        """開啟時間房出口確認視窗。"""

        self.current_object_id = (
            object_id
        )

        self.result = {
            "status": "exit_confirmation",
            "message": "確定要離開這個房間嗎？"
        }

        self.mode = (
            "exit_confirmation"
        )


    def draw_exit_confirmation(
        self,
        screen,
        mouse_pos
    ):
        """繪製時間房出口確認視窗。"""

        modal = self.draw_modal_base(
            screen,
            width=460,
            height=230
        )

        message = (
            "確定要離開這個房間嗎？"
        )

        self.draw_multiline_text(
            screen,
            message,
            modal.x + 35,
            modal.y + 55,
            modal.width - 70,
            font=self.game_ui.font_ui
        )

        leave_rect = pygame.Rect(
            modal.x + 55,
            modal.bottom - 70,
            140,
            40
        )

        cancel_rect = pygame.Rect(
            modal.right - 195,
            modal.bottom - 70,
            140,
            40
        )

        self.game_ui.draw_button(
            screen,
            "離開",
            leave_rect,
            leave_rect.collidepoint(
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

        return {
            "leave": leave_rect,
            "cancel": cancel_rect
        }


    def _get_scaled_diary_surface(self, asset_path, max_size):
        raw = self.game_ui.load_image(asset_path)
        if raw is None:
            return None
        orig_w, orig_h = raw.get_size()
        max_w, max_h = max_size
        if orig_w <= 0 or orig_h <= 0 or max_w <= 0 or max_h <= 0:
            return None
        ratio = min(max_w / orig_w, max_h / orig_h)
        new_size = (max(1, int(orig_w * ratio)), max(1, int(orig_h * ratio)))
        return pygame.transform.smoothscale(raw, new_size)

    def draw_diary_drag(
        self,
        screen,
        mouse_pos
    ):
        """繪製雙頁翻頁版陪伴日記拖放謎題（沿用主程式槽位與判定）。"""
        layout = self.game_ui.ui_layout["puzzle_layouts"]["diary_drag"]
        spreads = self.puzzle_controller.diary_spreads
        spread_index = self.puzzle_controller.diary_spread_index
        spread = spreads[spread_index]

        overlay = pygame.Surface(
            screen.get_size(),
            pygame.SRCALPHA
        )
        overlay.fill((20, 20, 25, 235))
        screen.blit(overlay, (0, 0))

        width = screen.get_width()

        # 標題（不顯示頁數）
        title = self.game_ui.font_large.render(
            "《陪伴日記》",
            True,
            (245, 245, 245)
        )
        screen.blit(
            title,
            title.get_rect(
                center=(width // 2, self.game_ui.scale_y(screen, layout["title_y"]))
            )
        )

        active_slot_id = spread["slot_id"]
        max_book_rect = self.game_ui.scale_rect(screen, layout["book_area"])
        bg_surf = self._get_scaled_diary_surface(
            spread["background_asset"], max_book_rect.size
        )
        if bg_surf is not None:
            book_rect = bg_surf.get_rect(center=max_book_rect.center)
            screen.blit(bg_surf, book_rect.topleft)
        else:
            book_rect = max_book_rect
            pygame.draw.rect(screen, (62, 56, 52), book_rect, border_radius=10)

        # 計算目前畫面的左半或右半感應區（無放置框線與提示文字）
        half_w = book_rect.width // 2
        if spread["side"] == "left":
            target_slot_rect = pygame.Rect(book_rect.left, book_rect.top, half_w, book_rect.height)
        else:
            target_slot_rect = pygame.Rect(book_rect.left + half_w, book_rect.top, book_rect.width - half_w, book_rect.height)

        buttons = {
            "diary_slot:" + active_slot_id: target_slot_rect
        }

        # 左右翻頁按鈕 (< / >)
        prev_rect = self.game_ui.scale_rect(screen, layout["navigation"]["previous"])
        next_rect = self.game_ui.scale_rect(screen, layout["navigation"]["next"])
        self.game_ui.draw_button(
            screen, "<", prev_rect,
            prev_rect.collidepoint(mouse_pos),
            enabled=(spread_index > 0)
        )
        self.game_ui.draw_button(
            screen, ">", next_rect,
            next_rect.collidepoint(mouse_pos),
            enabled=(spread_index < len(spreads) - 1)
        )
        buttons["diary_prev_page"] = prev_rect
        buttons["diary_next_page"] = next_rect

        # 下方待選碎片列座標
        home_layout = layout["page_home_positions"]
        available_pages = self.puzzle_controller.get_available_diary_pages()
        drag_rects = {}
        placed_page_in_current_spread = self.puzzle_controller.diary_slots.get(active_slot_id)
        dragging_page = self.puzzle_controller.diary_dragging_page

        for page_id in available_pages:
            placed_slot = None
            for s_id, occ in self.puzzle_controller.diary_slots.items():
                if occ == page_id:
                    placed_slot = s_id
                    break

            if page_id == dragging_page:
                rect = target_slot_rect.copy()
                drag_pos = self.puzzle_controller.diary_page_positions.get(page_id)
                if drag_pos is not None:
                    rect.topleft = drag_pos
                drag_rects[page_id] = rect

            elif placed_slot == active_slot_id:
                drag_rects[page_id] = target_slot_rect.copy()

            elif placed_slot is None:
                rect = self.game_ui.scale_rect(screen, home_layout[page_id])
                drag_rects[page_id] = rect

        # 繪製非拖曳中的碎片
        for page_id, rect in drag_rects.items():
            if page_id == dragging_page:
                continue

            asset_path = self.objects.get(page_id, {}).get("ui_asset")
            if page_id == placed_page_in_current_spread:
                piece_surf = self._get_scaled_diary_surface(asset_path, rect.size)
                if piece_surf is not None:
                    screen.blit(piece_surf, piece_surf.get_rect(center=rect.center))
            else:
                pygame.draw.rect(screen, (45, 48, 56), rect, border_radius=6)
                pygame.draw.rect(screen, (180, 185, 198), rect, width=2, border_radius=6)
                thumb_surf = self._get_scaled_diary_surface(asset_path, (rect.width - 10, rect.height - 10))
                if thumb_surf is not None:
                    screen.blit(thumb_surf, thumb_surf.get_rect(center=rect.center))
                else:
                    label = self.objects.get(page_id, {}).get("name", page_id)
                    text = self.game_ui.font_small.render(label, True, (240, 240, 240))
                    screen.blit(text, text.get_rect(center=rect.center))

            buttons["diary_page:" + page_id] = rect

        # 拖曳中的碎片最後畫
        if dragging_page is not None and dragging_page in drag_rects:
            rect = drag_rects[dragging_page]
            asset_path = self.objects.get(dragging_page, {}).get("ui_asset")
            drag_surf = self._get_scaled_diary_surface(asset_path, target_slot_rect.size)
            if drag_surf is not None:
                ghost = drag_surf.copy()
                ghost.set_alpha(220)
                screen.blit(ghost, ghost.get_rect(center=rect.center))
            buttons["diary_page:" + dragging_page] = rect

        # 右下角：確認、重設、退出按鈕
        confirm_rect = self.game_ui.scale_rect(screen, layout["buttons"]["confirm"])
        reset_rect = self.game_ui.scale_rect(screen, layout["buttons"]["reset"])
        exit_rect = self.game_ui.scale_rect(screen, layout["buttons"]["exit"])

        self.game_ui.draw_button(screen, "確認", confirm_rect, confirm_rect.collidepoint(mouse_pos))
        self.game_ui.draw_button(screen, "重設", reset_rect, reset_rect.collidepoint(mouse_pos))
        self.game_ui.draw_button(screen, "退出", exit_rect, exit_rect.collidepoint(mouse_pos))

        buttons["confirm"] = confirm_rect
        buttons["reset"] = reset_rect
        buttons["exit"] = exit_rect
        buttons["_drag_rects"] = drag_rects

        message = (self.result or {}).get("message", "")
        if message:
            message_layout = layout["message"]
            self.draw_multiline_text(
                screen,
                message,
                self.game_ui.scale_x(screen, message_layout["x"]),
                self.game_ui.scale_y(screen, message_layout["y"]),
                self.game_ui.scale_x(screen, message_layout["width"]),
                font=self.game_ui.font_small
            )

        return buttons


    def open_diary_exit_confirmation(
        self
    ):
        """詢問是否清空目前日記排列並離開。"""

        self.mode = (
            "diary_exit_confirmation"
        )


    def draw_diary_exit_confirmation(
        self,
        screen,
        mouse_pos
    ):
        """繪製日記整理退出確認。"""

        modal = self.draw_modal_base(
            screen,
            width=560,
            height=260
        )

        message = (
            "要退出日記整理嗎？\n"
            "若退出將會清空排列，"
            "並將全部的日記紙返回道具欄"
        )

        self.draw_multiline_text(
            screen,
            message,
            modal.x + 40,
            modal.y + 55,
            modal.width - 80,
            font=self.game_ui.font_ui
        )

        confirm_rect = pygame.Rect(
            modal.x + 70,
            modal.bottom - 70,
            160,
            40
        )

        cancel_rect = pygame.Rect(
            modal.right - 230,
            modal.bottom - 70,
            160,
            40
        )

        self.game_ui.draw_button(
            screen,
            "確定退出",
            confirm_rect,
            confirm_rect.collidepoint(
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

        return {
            "confirm": confirm_rect,
            "cancel": cancel_rect
        }


    def open_diary_reader(
        self,
        object_id
    ):
        """開啟完整日記閱讀器。"""

        self.current_object_id = (
            object_id
        )

        self.mode = (
            "diary_reader"
        )

        self.result = {
            "status": "diary_reader"
        }


    def draw_diary_reader(
        self,
        screen,
        mouse_pos
    ):
        """顯示完整陪伴日記目前跨頁圖片。"""

        diary = self.objects.get(
            self.current_object_id,
            {}
        )

        pages = diary.get(
            "pages",
            []
        )

        if not pages:
            return {}

        index = max(
            0,
            min(
                self.puzzle_controller.diary_reader_page,
                len(pages) - 1
            )
        )

        self.puzzle_controller.diary_reader_page = index
        page = pages[index]

        modal = self.draw_modal_base(
            screen,
            width=730,
            height=530
        )

        title = self.game_ui.font_large.render(
            "《陪伴日記》",
            True,
            (255, 220, 140)
        )
        screen.blit(
            title,
            title.get_rect(
                center=(modal.centerx, modal.y + 32)
            )
        )

        page_number = self.game_ui.font_small.render(
            f"{page.get('month', '')}（{index + 1} / {len(pages)}）",
            True,
            (200, 205, 220)
        )
        screen.blit(
            page_number,
            page_number.get_rect(
                center=(modal.centerx, modal.y + 62)
            )
        )

        image_area = pygame.Rect(
            modal.x + 28,
            modal.y + 82,
            modal.width - 56,
            modal.height - 160
        )

        asset_path = page.get("ui_asset")
        page_surf = (
            self._get_scaled_diary_surface(asset_path, image_area.size)
            if asset_path
            else None
        )

        if page_surf is not None:
            screen.blit(
                page_surf,
                page_surf.get_rect(center=image_area.center)
            )
        else:
            # 若圖片尚未載入則退回顯示文字
            self.draw_multiline_text(
                screen,
                page.get("text", ""),
                image_area.x + 20,
                image_area.y + 20,
                image_area.width - 40,
                font=self.game_ui.font_ui
            )

        previous_rect = pygame.Rect(
            modal.x + 55,
            modal.bottom - 58,
            120,
            38
        )

        next_rect = pygame.Rect(
            modal.right - 175,
            modal.bottom - 58,
            120,
            38
        )

        close_rect = pygame.Rect(
            modal.centerx - 60,
            modal.bottom - 58,
            120,
            38
        )

        self.game_ui.draw_button(
            screen,
            "上一頁",
            previous_rect,
            previous_rect.collidepoint(mouse_pos),
            enabled=index > 0
        )

        self.game_ui.draw_button(
            screen,
            "關閉",
            close_rect,
            close_rect.collidepoint(mouse_pos)
        )

        self.game_ui.draw_button(
            screen,
            "下一頁",
            next_rect,
            next_rect.collidepoint(mouse_pos),
            enabled=index < len(pages) - 1
        )

        return {
            "previous": previous_rect,
            "close": close_rect,
            "next": next_rect,
            "can_previous": index > 0,
            "can_next": index < len(pages) - 1
        }

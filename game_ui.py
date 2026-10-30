import pygame


class GameUI:
    """負責一般遊戲介面的繪製，不處理核心遊戲規則。"""

    def __init__(self, ui_layout, levels, objects):
        self.ui_layout = ui_layout
        self.levels = levels
        self.objects = objects

        self.base_width = ui_layout["base_resolution"]["width"]
        self.base_height = ui_layout["base_resolution"]["height"]

        self.font_title = pygame.font.SysFont(
            "microsoftjhenghei",
            40
        )

        self.font_large = pygame.font.SysFont(
            "microsoftjhenghei",
            28
        )

        self.font_ui = pygame.font.SysFont(
            "microsoftjhenghei",
            20
        )

        self.font_small = pygame.font.SysFont(
            "microsoftjhenghei",
            16
        )


    # ========================================================
    # 通用工具
    # ========================================================

    def scale_x(self, screen, value):
        """依照目前視窗寬度縮放X座標。"""

        screen_width = screen.get_width()

        return int(
            value * screen_width / self.base_width
        )


    def scale_y(self, screen, value):
        """依照目前視窗高度縮放Y座標。"""

        screen_height = screen.get_height()

        return int(
            value * screen_height / self.base_height
        )


    def scale_rect(self, screen, layout_data):
        """將ui_layout資料轉成目前視窗使用的Rect。"""

        return pygame.Rect(
            self.scale_x(
                screen,
                layout_data["x"]
            ),

            self.scale_y(
                screen,
                layout_data["y"]
            ),

            self.scale_x(
                screen,
                layout_data["width"]
            ),

            self.scale_y(
                screen,
                layout_data["height"]
            )
        )


    # ========================================================
    # Button
    # ========================================================

    def draw_button(
        self,
        screen,
        text,
        rect,
        hovered=False,
        enabled=True,
        bg_color=(50, 100, 150)
    ):
        """繪製通用按鈕。"""

        if not enabled:
            color = (65, 65, 70)
            text_color = (135, 135, 140)

        else:
            if hovered:
                color = (
                    min(bg_color[0] + 30, 255),
                    min(bg_color[1] + 30, 255),
                    min(bg_color[2] + 30, 255)
                )

            else:
                color = bg_color

            text_color = (255, 255, 255)

        pygame.draw.rect(
            screen,
            color,
            rect,
            border_radius=8
        )

        pygame.draw.rect(
            screen,
            (220, 220, 225),
            rect,
            width=2,
            border_radius=8
        )

        text_surface = self.font_ui.render(
            text,
            True,
            text_color
        )

        screen.blit(
            text_surface,
            text_surface.get_rect(
                center=rect.center
            )
        )


    # ========================================================
    # Placeholder
    # ========================================================

    def draw_placeholder_rect(
        self,
        screen,
        rect,
        label,
        color=(75, 80, 95)
    ):
        """繪製尚未有正式美術素材的Placeholder。"""

        pygame.draw.rect(
            screen,
            color,
            rect,
            border_radius=8
        )

        pygame.draw.rect(
            screen,
            (180, 185, 200),
            rect,
            width=2,
            border_radius=8
        )

        label_surface = self.font_small.render(
            label,
            True,
            (235, 235, 240)
        )

        screen.blit(
            label_surface,
            label_surface.get_rect(
                center=rect.center
            )
        )


    # ========================================================
    # Main Menu
    # ========================================================

    def draw_main_menu(
        self,
        screen,
        mouse_pos
    ):
        """繪製遊戲主選單。"""

        screen_width, screen_height = (
            screen.get_size()
        )

        screen.fill(
            (22, 23, 31)
        )

        title_surface = self.font_title.render(
            "數到100",
            True,
            (245, 245, 250)
        )

        screen.blit(
            title_surface,
            title_surface.get_rect(
                center=(
                    screen_width // 2,
                    110
                )
            )
        )

        button_width = 190
        button_height = 44

        button_x = (
            screen_width // 2
            - button_width // 2
        )

        start_y = 190
        gap = 58

        buttons = {
            "start": pygame.Rect(
                button_x,
                start_y,
                button_width,
                button_height
            ),

            "codex": pygame.Rect(
                button_x,
                start_y + gap,
                button_width,
                button_height
            ),

            "settings": pygame.Rect(
                button_x,
                start_y + gap * 2,
                button_width,
                button_height
            ),

            "save": pygame.Rect(
                button_x,
                start_y + gap * 3,
                button_width,
                button_height
            ),

            "exit": pygame.Rect(
                button_x,
                start_y + gap * 4 + 18,
                button_width,
                button_height
            )
        }

        self.draw_button(
            screen,
            "開始遊戲",
            buttons["start"],
            buttons["start"].collidepoint(
                mouse_pos
            )
        )

        self.draw_button(
            screen,
            "圖鑑",
            buttons["codex"],
            buttons["codex"].collidepoint(
                mouse_pos
            )
        )

        self.draw_button(
            screen,
            "設定",
            buttons["settings"],
            buttons["settings"].collidepoint(
                mouse_pos
            )
        )

        self.draw_button(
            screen,
            "存檔",
            buttons["save"],
            enabled=False
        )

        locked_surface = self.font_small.render(
            "尚未解鎖",
            True,
            (135, 135, 145)
        )

        screen.blit(
            locked_surface,
            locked_surface.get_rect(
                center=(
                    screen_width // 2,
                    buttons["save"].bottom + 12
                )
            )
        )

        self.draw_button(
            screen,
            "退出遊戲",
            buttons["exit"],
            buttons["exit"].collidepoint(
                mouse_pos
            ),
            bg_color=(100, 55, 60)
        )

        version_surface = self.font_small.render(
            "Prototype v0.1",
            True,
            (130, 130, 140)
        )

        screen.blit(
            version_surface,
            (
                screen_width
                - version_surface.get_width()
                - 15,

                screen_height
                - version_surface.get_height()
                - 12
            )
        )

        return buttons


    # ========================================================
    # 307房
    # ========================================================

    def draw_room_307(self, screen):
        """繪製307病房Placeholder場景。"""

        scene_data = self.ui_layout.get(
            "scenes",
            {}
        ).get(
            "room_307"
        )

        screen.fill(
            (115, 118, 125)
        )

        if scene_data is None:
            return

        background_label = scene_data[
            "background"
        ].get(
            "label",
            "307病房"
        )

        title_surface = self.font_large.render(
            background_label,
            True,
            (235, 235, 240)
        )

        screen.blit(
            title_surface,
            title_surface.get_rect(
                center=(
                    screen.get_width() // 2,
                    35
                )
            )
        )

        for character_data in scene_data.get(
            "characters",
            {}
        ).values():

            rect = self.scale_rect(
                screen,
                character_data
            )

            self.draw_placeholder_rect(
                screen,
                rect,
                character_data.get(
                    "label",
                    "Character Placeholder"
                ),
                color=(85, 90, 110)
            )

        for object_data in scene_data.get(
            "objects",
            {}
        ).values():

            rect = self.scale_rect(
                screen,
                object_data
            )

            self.draw_placeholder_rect(
                screen,
                rect,
                object_data.get(
                    "label",
                    "Object Placeholder"
                ),
                color=(90, 95, 100)
            )


    # ========================================================
    # 序章背景
    # ========================================================

    def draw_intro_background(
        self,
        screen,
        dialogue_controller
    ):
        """依照序章進度顯示簡易背景。"""

        index = dialogue_controller.current_index

        if index <= 2:
            screen.fill(
                (28, 32, 45)
            )

            label = (
                "研究所 / Background Placeholder"
            )

        elif index <= 5:
            screen.fill(
                (90, 94, 102)
            )

            label = (
                "醫院走廊 / Background Placeholder"
            )

        else:
            self.draw_room_307(
                screen
            )

            return

        label_surface = self.font_large.render(
            label,
            True,
            (220, 220, 225)
        )

        screen.blit(
            label_surface,
            label_surface.get_rect(
                center=(
                    screen.get_width() // 2,
                    90
                )
            )
        )


    # ========================================================
    # Settings Button
    # ========================================================

    def get_settings_button_rect(
        self,
        screen
    ):
        """取得設定按鈕位置。"""

        layout_data = self.ui_layout[
            "hud"
        ]["settings_button"]

        return self.scale_rect(
            screen,
            layout_data
        )


    def draw_settings_button(
        self,
        screen,
        mouse_pos
    ):
        """繪製遊戲中的設定按鈕。"""

        rect = self.get_settings_button_rect(
            screen
        )

        self.draw_button(
            screen,
            "設定",
            rect,
            rect.collidepoint(
                mouse_pos
            ),
            bg_color=(70, 70, 90)
        )

        return rect


    # ========================================================
    # Space HUD
    # ========================================================

    def draw_space_hud(
        self,
        screen,
        game
    ):
        """顯示目前空間名稱與收斂率。"""

        if game.current_space is None:
            return

        current_level = self.levels.get(
            game.current_space
        )

        if current_level is None:
            return

        hud_data = self.ui_layout[
            "hud"
        ]["space_info"]

        hud_rect = self.scale_rect(
            screen,
            hud_data
        )

        hud_surface = pygame.Surface(
            (
                hud_rect.width,
                hud_rect.height
            ),
            pygame.SRCALPHA
        )

        hud_surface.fill(
            (15, 15, 20, 190)
        )

        screen.blit(
            hud_surface,
            hud_rect.topleft
        )

        y = hud_rect.y + 10

        name_surface = self.font_ui.render(
            current_level["name"],
            True,
            (245, 245, 245)
        )

        screen.blit(
            name_surface,
            (
                hud_rect.x + 12,
                y
            )
        )

        y += 26

        if "convergence_rate" in current_level:

            rate_surface = self.font_small.render(
                (
                    f"收斂率："
                    f"{current_level['convergence_rate']}%"
                ),
                True,
                (225, 225, 225)
            )

            screen.blit(
                rate_surface,
                (
                    hud_rect.x + 12,
                    y
                )
            )

            y += 23

        if "warning" in current_level:

            warning_surface = (
                self.font_small.render(
                    current_level["warning"],
                    True,
                    (255, 180, 120)
                )
            )

            screen.blit(
                warning_surface,
                (
                    hud_rect.x + 12,
                    y
                )
            )


    # ========================================================
    # Exploration
    # ========================================================

    def draw_space(
        self,
        screen,
        game,
        mouse_pos,
        player_color
    ):
        """繪製A/B/C探索Placeholder。"""

        current_space = game.current_space

        space_layout = self.ui_layout[
            "spaces"
        ].get(
            current_space
        )

        if space_layout is None:
            screen.fill(
                (30, 30, 35)
            )

            return {}

        if current_space == "C":
            screen.fill(
                (218, 218, 215)
            )

            text_color = (
                40,
                40,
                45
            )

        else:
            screen.fill(
                (50, 53, 62)
            )

            text_color = (
                225,
                225,
                230
            )

        background = space_layout.get(
            "background",
            {}
        )

        label = background.get(
            "label",
            f"Space {current_space}"
        )

        label_surface = self.font_large.render(
            label,
            True,
            text_color
        )

        screen.blit(
            label_surface,
            label_surface.get_rect(
                center=(
                    screen.get_width() // 2,
                    40
                )
            )
        )

        player_data = space_layout.get(
            "player"
        )

        if player_data is not None:

            player_rect = self.scale_rect(
                screen,
                player_data
            )

            self.draw_placeholder_rect(
                screen,
                player_rect,
                player_data.get(
                    "label",
                    "Player Placeholder"
                ),
                color=player_color
            )

        object_rects = {}

        for (
            object_id,
            object_layout
        ) in space_layout.get(
            "objects",
            {}
        ).items():

            rect = self.scale_rect(
                screen,
                object_layout
            )

            hovered = rect.collidepoint(
                mouse_pos
            )

            color = (
                (120, 125, 145)
                if hovered
                else
                (78, 82, 95)
            )

            self.draw_placeholder_rect(
                screen,
                rect,
                object_layout.get(
                    "label",
                    object_id
                ),
                color=color
            )

            object_rects[
                object_id
            ] = rect

            if hovered:

                object_name = self.objects.get(
                    object_id,
                    {}
                ).get(
                    "name",
                    object_id
                )

                name_surface = (
                    self.font_small.render(
                        object_name,
                        True,
                        (255, 245, 180)
                    )
                )

                screen.blit(
                    name_surface,
                    (
                        rect.centerx
                        - name_surface.get_width()
                        // 2,

                        rect.y - 22
                    )
                )

        self.draw_space_hud(
            screen,
            game
        )

        return object_rects


    # ========================================================
    # Hotbar
    # ========================================================

    def get_visible_inventory(
        self,
        game,
        hotbar_offset
    ):
        """取得目前Hotbar應顯示的物品。"""

        inventory_display = list(
            reversed(game.inventory)
        )

        visible_slots = self.ui_layout[
            "hotbar"
        ].get(
            "visible_slots",
            5
        )

        return inventory_display[
            hotbar_offset:
            hotbar_offset + visible_slots
        ]


    def draw_hotbar(
        self,
        screen,
        game,
        selected_slot,
        hotbar_offset,
        mouse_pos
    ):
        """依照真正的game.inventory繪製Hotbar。"""

        hotbar_data = self.ui_layout[
            "hotbar"
        ]

        visible_slots = hotbar_data.get(
            "visible_slots",
            5
        )

        slot_size = hotbar_data.get(
            "slot_size",
            55
        )

        padding = hotbar_data.get(
            "slot_padding",
            8
        )

        bottom_margin = hotbar_data.get(
            "bottom_margin",
            30
        )

        show_arrows = hotbar_data.get(
            "show_arrows",
            True
        )

        visible_inventory = (
            self.get_visible_inventory(
                game,
                hotbar_offset
            )
        )

        total_width = (
            visible_slots * slot_size
            + (visible_slots - 1) * padding
        )

        if show_arrows:
            total_width += 80

        start_x = (
            screen.get_width()
            - total_width
        ) // 2

        start_y = (
            screen.get_height()
            - slot_size
            - bottom_margin
        )

        current_x = start_x

        arrow_left = None
        arrow_right = None

        if show_arrows:

            arrow_left = pygame.Rect(
                current_x,
                start_y,
                32,
                slot_size
            )

            self.draw_button(
                screen,
                "◀",
                arrow_left,
                arrow_left.collidepoint(
                    mouse_pos
                ),
                bg_color=(55, 55, 65)
            )

            current_x += 40

        slot_rects = []

        for index in range(
            visible_slots
        ):

            rect = pygame.Rect(
                current_x
                + index
                * (slot_size + padding),

                start_y,
                slot_size,
                slot_size
            )

            pygame.draw.rect(
                screen,
                (105, 105, 110),
                rect,
                border_radius=5
            )

            if index == selected_slot:
                border_color = (
                    255,
                    255,
                    255
                )

                border_width = 4

            else:
                border_color = (
                    55,
                    55,
                    60
                )

                border_width = 2

            pygame.draw.rect(
                screen,
                border_color,
                rect,
                width=border_width,
                border_radius=5
            )

            if index < len(
                visible_inventory
            ):

                item_id = visible_inventory[
                    index
                ]

                item_name = self.objects.get(
                    item_id,
                    {}
                ).get(
                    "name",
                    item_id
                )

                text_surface = (
                    self.font_small.render(
                        item_name[:4],
                        True,
                        (245, 245, 245)
                    )
                )

                screen.blit(
                    text_surface,
                    text_surface.get_rect(
                        center=rect.center
                    )
                )

                number_surface = (
                    self.font_small.render(
                        str(index + 1),
                        True,
                        (40, 40, 40)
                    )
                )

                screen.blit(
                    number_surface,
                    (
                        rect.x + 4,
                        rect.y + 2
                    )
                )

            slot_rects.append(
                rect
            )

        if show_arrows:

            arrow_right = pygame.Rect(
                current_x
                + visible_slots
                * (slot_size + padding),

                start_y,
                32,
                slot_size
            )

            self.draw_button(
                screen,
                "▶",
                arrow_right,
                arrow_right.collidepoint(
                    mouse_pos
                ),
                bg_color=(55, 55, 65)
            )

        return (
            slot_rects,
            arrow_left,
            arrow_right,
            visible_inventory
        )


    # ========================================================
    # Settings
    # ========================================================

    def draw_settings_overlay(
        self,
        screen,
        mouse_pos,
        volume,
        current_look_index,
        looks
    ):
        """繪製共用設定Overlay。"""

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
            (0, 0, 0, 175)
        )

        screen.blit(
            overlay,
            (0, 0)
        )

        modal_width = min(
            480,
            screen_width - 50
        )

        modal_height = min(
            430,
            screen_height - 50
        )

        modal_rect = pygame.Rect(
            (
                screen_width
                - modal_width
            ) // 2,

            (
                screen_height
                - modal_height
            ) // 2,

            modal_width,
            modal_height
        )

        pygame.draw.rect(
            screen,
            (45, 45, 60),
            modal_rect,
            border_radius=12
        )

        pygame.draw.rect(
            screen,
            (235, 235, 240),
            modal_rect,
            width=2,
            border_radius=12
        )

        title_surface = self.font_large.render(
            "系統設定",
            True,
            (255, 220, 130)
        )

        screen.blit(
            title_surface,
            title_surface.get_rect(
                center=(
                    modal_rect.centerx,
                    modal_rect.y + 35
                )
            )
        )

        buttons = {}

        buttons["codex"] = pygame.Rect(
            modal_rect.x + 35,
            modal_rect.y + 75,
            110,
            35
        )

        self.draw_button(
            screen,
            "圖鑑",
            buttons["codex"],
            buttons["codex"].collidepoint(
                mouse_pos
            )
        )

        volume_surface = self.font_ui.render(
            f"總音量：{volume}%",
            True,
            (245, 245, 245)
        )

        screen.blit(
            volume_surface,
            (
                modal_rect.x + 35,
                modal_rect.y + 135
            )
        )

        slider_x = modal_rect.x + 175
        slider_y = modal_rect.y + 142

        slider_width = (
            modal_rect.width - 220
        )

        pygame.draw.rect(
            screen,
            (85, 85, 90),
            (
                slider_x,
                slider_y,
                slider_width,
                10
            ),
            border_radius=5
        )

        fill_width = int(
            slider_width
            * volume
            / 100
        )

        if fill_width > 0:

            pygame.draw.rect(
                screen,
                (130, 200, 140),
                (
                    slider_x,
                    slider_y,
                    fill_width,
                    10
                ),
                border_radius=5
            )

        pygame.draw.circle(
            screen,
            (245, 245, 245),
            (
                slider_x + fill_width,
                slider_y + 5
            ),
            9
        )

        buttons["slider"] = pygame.Rect(
            slider_x,
            slider_y - 10,
            slider_width,
            30
        )

        resolution_surface = (
            self.font_ui.render(
                (
                    f"視窗大小："
                    f"{screen_width} × {screen_height}"
                ),
                True,
                (245, 245, 245)
            )
        )

        screen.blit(
            resolution_surface,
            (
                modal_rect.x + 35,
                modal_rect.y + 190
            )
        )

        buttons["800"] = pygame.Rect(
            modal_rect.x + 280,
            modal_rect.y + 185,
            65,
            32
        )

        buttons["1024"] = pygame.Rect(
            modal_rect.x + 355,
            modal_rect.y + 185,
            70,
            32
        )

        self.draw_button(
            screen,
            "800",
            buttons["800"],
            buttons["800"].collidepoint(
                mouse_pos
            )
        )

        self.draw_button(
            screen,
            "1024",
            buttons["1024"],
            buttons["1024"].collidepoint(
                mouse_pos
            )
        )

        look_surface = self.font_ui.render(
            "更換外型 / 顏色：",
            True,
            (245, 245, 245)
        )

        screen.blit(
            look_surface,
            (
                modal_rect.x + 35,
                modal_rect.y + 245
            )
        )

        pygame.draw.rect(
            screen,
            looks[current_look_index],
            (
                modal_rect.x + 205,
                modal_rect.y + 240,
                35,
                35
            ),
            border_radius=5
        )

        buttons["look"] = pygame.Rect(
            modal_rect.x + 260,
            modal_rect.y + 240,
            120,
            35
        )

        self.draw_button(
            screen,
            "切換外型",
            buttons["look"],
            buttons["look"].collidepoint(
                mouse_pos
            )
        )

        buttons["save"] = pygame.Rect(
            modal_rect.x + 35,
            modal_rect.y + 295,
            110,
            35
        )

        self.draw_button(
            screen,
            "存檔",
            buttons["save"],
            enabled=False
        )

        save_text = self.font_small.render(
            "尚未解鎖",
            True,
            (140, 140, 150)
        )

        screen.blit(
            save_text,
            (
                buttons["save"].right + 10,
                buttons["save"].centery
                - save_text.get_height()
                // 2
            )
        )

        buttons["menu"] = pygame.Rect(
            modal_rect.x + 45,
            modal_rect.bottom - 60,
            150,
            38
        )

        buttons["close"] = pygame.Rect(
            modal_rect.right - 195,
            modal_rect.bottom - 60,
            150,
            38
        )

        self.draw_button(
            screen,
            "回到主選單",
            buttons["menu"],
            buttons["menu"].collidepoint(
                mouse_pos
            ),
            bg_color=(90, 90, 105)
        )

        self.draw_button(
            screen,
            "確定關閉",
            buttons["close"],
            buttons["close"].collidepoint(
                mouse_pos
            ),
            bg_color=(120, 70, 70)
        )

        return buttons


    # ========================================================
    # Codex 暫時畫面
    # ========================================================

    def draw_codex_placeholder(
        self,
        screen,
        mouse_pos
    ):
        """正式Codex接入前的暫時畫面。"""

        screen.fill(
            (25, 25, 35)
        )

        title = self.font_title.render(
            "圖鑑",
            True,
            (245, 245, 245)
        )

        screen.blit(
            title,
            title.get_rect(
                center=(
                    screen.get_width() // 2,
                    80
                )
            )
        )

        message = self.font_ui.render(
            "Codex UI 將於後續接入",
            True,
            (180, 180, 190)
        )

        screen.blit(
            message,
            message.get_rect(
                center=(
                    screen.get_width() // 2,
                    screen.get_height() // 2
                )
            )
        )

        back_rect = pygame.Rect(
            30,
            screen.get_height() - 65,
            120,
            40
        )

        self.draw_button(
            screen,
            "返回",
            back_rect,
            back_rect.collidepoint(
                mouse_pos
            )
        )

        return back_rect
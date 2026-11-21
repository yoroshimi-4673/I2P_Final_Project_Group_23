from pathlib import Path

import pygame


class GameUI:
    """負責一般遊戲介面的繪製，不處理核心遊戲規則。"""

    def __init__(self, ui_layout, levels, objects):
        self.ui_layout = ui_layout
        self.levels = levels
        self.objects = objects

        self.project_root = (
            Path(__file__).resolve().parent.parent
        )  # 取得專案根目錄供圖片路徑使用

        self.image_cache = {}  # 快取已載入圖片避免每幀重讀

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


    def load_image(
        self,
        asset_path
    ):
        """載入圖片並快取原始Surface。"""

        if not asset_path:
            return None

        if asset_path in self.image_cache:
            return self.image_cache[
                asset_path
            ]

        full_path = (
            self.project_root
            / asset_path
        )

        if not full_path.exists():
            print(
                f"[GameUI] 找不到圖片：{full_path}"
            )
            self.image_cache[asset_path] = None
            return None

        try:
            image = pygame.image.load(
                str(full_path)
            ).convert_alpha()
        except (pygame.error, OSError):
            self.image_cache[asset_path] = None
            return None

        self.image_cache[
            asset_path
        ] = image

        return image

    def remove_near_white_background(self, image, threshold=245):
        """複製圖片並只清除近白色像素的透明度。"""
        processed = image.copy()
        width, height = processed.get_size()
        for y in range(height):
            for x in range(width):
                red, green, blue, alpha = processed.get_at((x, y))
                if alpha and min(red, green, blue) >= threshold:
                    processed.set_at((x, y), (red, green, blue, 0))
        return processed

    def load_asset_without_white_background(self, asset_path, threshold=245):
        key = ("remove_white_background", asset_path, threshold)
        if key not in self.image_cache:
            image = self.load_image(asset_path)
            self.image_cache[key] = (
                self.remove_near_white_background(image, threshold) if image is not None else None
            )
        return self.image_cache[key]


    def get_item_display_value(self, item_id, key, game=None, default=None):
        item_data = self.objects.get(item_id, {})
        state_event = item_data.get("state_event")
        value = item_data.get(key, default)
        if game is not None and state_event and game.has_event(state_event):
            return item_data.get(f"completed_{key}", value)
        return value

    def draw_item_asset(self, screen, item_id, rect, padding=4, asset_key="ui_asset", game=None):
        """共用道具圖片繪製並保留原始比例。"""

        # 依指定欄位共用正反面圖片快取
        asset_path = self.get_item_display_value(item_id, asset_key, game)
        if not asset_path:
            return False

        image = self.load_image(asset_path)  # 沿用既有圖片快取避免重讀
        target = pygame.Rect(rect).inflate(-2 * padding, -2 * padding)
        if image is None or target.width <= 0 or target.height <= 0:
            return False

        ratio = min(target.width / image.get_width(), target.height / image.get_height())
        size = (
            max(1, min(target.width, round(image.get_width() * ratio))),
            max(1, min(target.height, round(image.get_height() * ratio)))
        )
        scaled = pygame.transform.scale(image, size)  # 使用最近鄰縮放保留像素邊緣
        screen.blit(scaled, scaled.get_rect(center=target.center))
        return True


    def get_fitted_image_rect(self, image, rect):
        width, height = image.get_size()
        scale = min(rect.width / width, rect.height / height)
        fitted = pygame.Rect(0, 0, max(1, round(width * scale)), max(1, round(height * scale)))
        fitted.center = rect.center
        return fitted


    def scale_image_to_fit(
        self,
        image,
        rect
    ):
        """保持原始比例縮放至指定區域。"""

        image_width = image.get_width()
        image_height = image.get_height()

        if (
            image_width <= 0
            or image_height <= 0
        ):
            return image

        return pygame.transform.smoothscale(image, self.get_fitted_image_rect(image, rect).size)


    def draw_asset(
        self,
        screen,
        asset_path,
        rect,
        *,
        remove_white_background=False,
        white_background_threshold=245,
    ):
        """保持比例將素材畫進指定區域。"""

        image = (
            self.load_asset_without_white_background(asset_path, white_background_threshold)
            if remove_white_background
            else self.load_image(asset_path)
        )

        if image is None:
            return False

        scaled_image = (
            self.scale_image_to_fit(
                image,
                rect
            )
        )

        image_rect = scaled_image.get_rect(
            center=rect.center
        )

        screen.blit(
            scaled_image,
            image_rect
        )

        return True


    def draw_decoration(self, screen, decoration, rect):
        """沿用圖片快取繪製單格靜態角色或裝飾。"""

        asset = decoration.get("asset")
        grid = decoration.get("sprite_sheet")
        if not grid:
            return self.draw_asset(screen, asset, rect)
        sheet = self.load_image(asset)
        if sheet is None or rect.width <= 0 or rect.height <= 0:
            return False
        columns, rows = grid.get("columns", 4), grid.get("rows", 3)
        column, row = grid.get("column", 0), grid.get("row", 0)
        if (columns <= 0 or rows <= 0 or not 0 <= column < columns
                or not 0 <= row < rows or sheet.get_width() % columns
                or sheet.get_height() % rows):
            return False
        width, height = sheet.get_width() // columns, sheet.get_height() // rows
        if width <= 0 or height <= 0:
            return False
        key = ("decoration_frame", asset, columns, rows, column, row)
        if key not in self.image_cache:
            # 只快取指定單格，不播放角色移動動畫
            self.image_cache[key] = sheet.subsurface(
                pygame.Rect(column * width, row * height, width, height)
            ).copy()
        frame = self.image_cache[key]
        ratio = min(rect.width / width, rect.height / height)
        size = (max(1, round(width * ratio)), max(1, round(height * ratio)))
        scaled = pygame.transform.scale(frame, size)
        screen.blit(scaled, scaled.get_rect(center=rect.center))
        return True


    def draw_background_asset(
        self,
        screen,
        asset_path
    ):
        """將背景圖片完整鋪滿目前畫面。"""

        image = self.load_image(
            asset_path
        )

        if image is None:
            return False

        scaled_image = (
            pygame.transform.smoothscale(
                image,
                screen.get_size()
            )
        )

        screen.blit(
            scaled_image,
            (0, 0)
        )

        return True


    def draw_debug_collision(
        self,
        screen,
        walkable_polygon,
        collision_rects
    ):
        """顯示Polygon與家具Rect供校正碰撞。"""

        if len(walkable_polygon) >= 3:
            pygame.draw.polygon(
                screen,
                (255, 220, 0),
                walkable_polygon,
                width=3
            )

            for index, point in enumerate(
                walkable_polygon
            ):
                pygame.draw.circle(
                    screen,
                    (255, 220, 0),
                    point,
                    5
                )

                label = self.font_small.render(
                    str(index),
                    True,
                    (255, 245, 150)
                )

                screen.blit(
                    label,
                    (
                        point[0] + 7,
                        point[1] - 8
                    )
                )

        for zone_id, rect in (
            collision_rects.items()
        ):
            pygame.draw.rect(
                screen,
                (255, 70, 70),
                rect,
                width=2
            )

            label = self.font_small.render(
                zone_id,
                True,
                (255, 120, 120)
            )

            screen.blit(
                label,
                (rect.x + 3, rect.y + 3)
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

    def draw_success_end(self, screen, mouse_pos):
        """繪製第二章暫時結束資訊並回傳按鈕範圍。"""
        screen.fill((25, 25, 32))
        center_x, center_y = screen.get_rect().center
        title = self.font_title.render("To be continued", True, (245, 245, 245))
        summary = self.font_ui.render("Chapter 2 已完成。", True, (230, 230, 235))
        screen.blit(title, title.get_rect(center=(center_x, center_y - 100)))
        screen.blit(summary, summary.get_rect(center=(center_x, center_y - 20)))

        buttons = {
            "settings": pygame.Rect(center_x - 175, center_y + 100, 150, 42),
            "menu": pygame.Rect(center_x + 25, center_y + 100, 150, 42),
        }
        for action, label in (("settings", "設定"), ("menu", "回到主畫面")):
            rect = buttons[action]
            self.draw_button(screen, label, rect, rect.collidepoint(mouse_pos))
        return buttons

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

    def get_current_tutorial_text(self, game):
        """依序回傳目前階段的新手教學文字（共 4 步）；全部完成則回傳 None。"""
        if game.current_space not in ("A", "B", "C"):
            return None

        if not game.has_event("tutorial_move_done"):
            return "【操作提示 1/4】\n使用 WASD 鍵或點擊地板移動"

        if not game.has_event("tutorial_interact_done"):
            return "【操作提示 2/4】\n靠近物件時，按 [E] 鍵進行調查"

        if len(game.inventory) > 0 and not game.has_event("tutorial_hotbar_done"):
            return "【操作提示 3/4】\n點擊下方道具欄或按 Enter 鍵\n檢視物品"

        if game.has_event("tutorial_hotbar_done") and not game.has_event("tutorial_codex_done"):
            return "【操作提示 4/4】\n點擊左上角「設定」開啟「圖鑑」\n查看已收集的物品"

        return None

    def draw_tutorial_hint(self, screen, game):
        """在右上角繪製半透明連貫新手教學框。"""
        hint_text = self.get_current_tutorial_text(game)
        if not hint_text:
            return

        lines = hint_text.split("\n")
        layout = dict(self.ui_layout.get("hud", {}).get(
            "tutorial_box",
            {"x": 530, "y": 20, "width": 250, "height": 76}
        ))
        layout["height"] = max(layout.get("height", 76), 24 + len(lines) * 24)
        box_rect = self.scale_rect(screen, layout)

        panel = pygame.Surface(box_rect.size, pygame.SRCALPHA)
        panel.fill((18, 22, 30, 205))
        screen.blit(panel, box_rect.topleft)
        pygame.draw.rect(screen, (140, 175, 220), box_rect, width=2, border_radius=8)

        padding_x = self.scale_x(screen, 12)
        padding_y = self.scale_y(screen, 10)
        line_gap = self.scale_y(screen, 24)

        for idx, line in enumerate(lines):
            color = (255, 225, 130) if idx == 0 else (240, 244, 250)
            text_surf = self.font_small.render(line, True, color)
            screen.blit(
                text_surf,
                (box_rect.left + padding_x, box_rect.top + padding_y + idx * line_gap)
            )

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

        # 依照片劇情事件顯示更新收斂率
        if game.has_event("photo_back_seen"):
            updated_rates = {"A": 81, "B": 55, "C": 37}
            if game.current_space in updated_rates:
                current_level = dict(current_level)
                current_level["convergence_rate"] = updated_rates[game.current_space]

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
        self.draw_tutorial_hint(screen, game)    

    # ========================================================
    # Exploration
    # ========================================================

    def draw_space(
        self,
        screen,
        game,
        mouse_pos
    ):
        """繪製目前探索空間與正式圖片素材。"""

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

        background = space_layout.get(
            "background",
            {}
        )

        background_asset = background.get(
            "asset"
        )

        background_drawn = (
            self.draw_background_asset(
                screen,
                background_asset
            )
        )

        if not background_drawn:
            if current_space == "C":
                screen.fill(
                    (218, 218, 215)
                )
                text_color = (40, 40, 45)
            else:
                screen.fill(
                    (50, 53, 62)
                )
                text_color = (225, 225, 230)

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

        object_rects = {}

        for (
            object_id,
            object_layout
        ) in space_layout.get(
            "objects",
            {}
        ).items():
            # 尚未發現的物件不繪圖或顯示名稱
            required_event = object_layout.get("visible_after_event")
            if required_event and not game.has_event(required_event):
                continue

            rect = self.scale_rect(
                screen,
                object_layout
            )

            hovered = rect.collidepoint(
                mouse_pos
            )

            render_mode = object_layout.get(
                "render_mode",
                "normal"
            )

            # 背景物件僅保留互動範圍不重繪
            if render_mode != "background":
                asset_drawn = self.draw_asset(
                    screen,
                    object_layout.get(
                        "asset"
                    ),
                    rect,
                    remove_white_background=object_layout.get("remove_white_background", False),
                    white_background_threshold=object_layout.get("white_background_threshold", 245),
                )

                if not asset_drawn:
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

                overlay_asset = object_layout.get(
                    "overlay_asset"
                )

                if overlay_asset:
                    self.draw_asset(
                        screen,
                        overlay_asset,
                        rect
                    )

            object_rects[
                object_id
            ] = rect

            if (
                hovered
                and render_mode != "background"
            ):
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

        # 純視覺角色僅繪圖不建立互動範圍
        for decoration in space_layout.get(
            "decorations",
            {}
        ).values():
            rect = self.scale_rect(
                screen,
                decoration
            )

            self.draw_decoration(screen, decoration, rect)

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

                if not self.draw_item_asset(screen, item_id, rect, padding=8, game=game):
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

        return {
            "slots": slot_rects,
            "left": arrow_left,
            "right": arrow_right,
            "visible_items": visible_inventory
        }


    # ========================================================
    # Settings
    # ========================================================

    def draw_settings_overlay(
        self,
        screen,
        mouse_pos,
        volume,
        allow_save=True,
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
        buttons["tutorial"] = pygame.Rect(
            modal_rect.x + 35,
            modal_rect.y + 240,
            130,
            36
        )

        self.draw_button(
            screen,
            "新手教學",
            buttons["tutorial"],
            buttons["tutorial"].collidepoint(
                mouse_pos
            )
        )
        if allow_save:
            buttons["save"] = pygame.Rect(modal_rect.x + 35, modal_rect.y + 295, 110, 35)
            self.draw_button(screen, "存檔", buttons["save"], buttons["save"].collidepoint(mouse_pos))

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
    # Tutorial Guide Modal（從系統設定點開的操作總覽）
    # ========================================================

    def draw_tutorial_guide_overlay(
        self,
        screen,
        mouse_pos
    ):
        """繪製完整操作步驟的新手教學總覽視窗。"""

        screen_width, screen_height = screen.get_size()

        overlay = pygame.Surface(
            (screen_width, screen_height),
            pygame.SRCALPHA
        )
        overlay.fill((0, 0, 0, 185))
        screen.blit(overlay, (0, 0))

        modal_width = min(520, screen_width - 50)
        modal_height = min(410, screen_height - 50)
        modal_rect = pygame.Rect(
            (screen_width - modal_width) // 2,
            (screen_height - modal_height) // 2,
            modal_width,
            modal_height
        )

        pygame.draw.rect(
            screen,
            (38, 42, 56),
            modal_rect,
            border_radius=12
        )
        pygame.draw.rect(
            screen,
            (225, 225, 235),
            modal_rect,
            width=2,
            border_radius=12
        )

        title_surface = self.font_large.render(
            "新手教學・操作說明",
            True,
            (255, 220, 130)
        )
        screen.blit(
            title_surface,
            title_surface.get_rect(
                center=(modal_rect.centerx, modal_rect.y + 36)
            )
        )

        steps = [
            ("1. 角色移動", "使用 WASD 鍵，或直接點擊地板移動"),
            ("2. 調查物件", "靠近可互動物件時，按 [E] 鍵進行調查"),
            ("3. 檢視道具", "點擊下方道具欄（或按數字鍵 / Enter）查看物品"),
            ("4. 圖鑑紀錄", "於設定開啟圖鑑，點擊物品卡查看詳情、ESC 返回"),
        ]

        y = modal_rect.y + 78
        for step_title, step_desc in steps:
            t_surf = self.font_ui.render(step_title, True, (150, 205, 255))
            d_surf = self.font_small.render(step_desc, True, (235, 238, 245))
            screen.blit(t_surf, (modal_rect.x + 36, y))
            screen.blit(d_surf, (modal_rect.x + 54, y + 26))
            y += 62

        close_rect = pygame.Rect(
            modal_rect.centerx - 70,
            modal_rect.bottom - 54,
            140,
            38
        )
        self.draw_button(
            screen,
            "我知道了",
            close_rect,
            close_rect.collidepoint(mouse_pos),
            bg_color=(70, 110, 155)
        )

        return {"close": close_rect}
    
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

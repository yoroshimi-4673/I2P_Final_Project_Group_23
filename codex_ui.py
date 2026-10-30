import pygame

from dialogue_ui import wrap_text


class CodexUI:
    """負責圖鑑顯示、收藏狀態與圖鑑內物品資訊。"""

    def __init__(
        self,
        game_ui,
        codex_data,
        objects
    ):
        self.game_ui = game_ui

        self.codex_data = codex_data

        self.objects = objects

        self.selected_item = None

        self.left_scroll_y = 0

        self.right_scroll_y = 0

        self.dragging_scrollbar = False


    # ========================================================
    # Data
    # ========================================================

    def get_chapters(self):
        """取得全部圖鑑章節資料。"""

        return self.codex_data.get(
            "chapters",
            []
        )


    def is_unlocked(
        self,
        game,
        item_id
    ):
        """判斷指定圖鑑物品是否已被發現。"""

        return (
            item_id
            in game.discovered_items
        )


    def get_progress(
        self,
        game
    ):
        """取得目前圖鑑解鎖進度。"""

        total = 0

        unlocked = 0

        for chapter in self.get_chapters():

            for item_id in chapter.get(
                "items",
                []
            ):

                total += 1

                if self.is_unlocked(
                    game,
                    item_id
                ):

                    unlocked += 1

        return (
            unlocked,
            total
        )


    # ========================================================
    # Scroll
    # ========================================================

    def handle_wheel(
        self,
        event,
        mouse_pos
    ):
        """處理Codex畫面的滑鼠滾輪。"""

        # 左側章節區
        if mouse_pos[0] < 180:

            self.left_scroll_y += (
                event.y * 25
            )

        # 右側內容區
        else:

            self.right_scroll_y += (
                event.y * 35
            )


    # ========================================================
    # Main Draw
    # ========================================================

    def draw(
        self,
        screen,
        game,
        mouse_pos
    ):
        """繪製完整Codex畫面。"""

        width, height = screen.get_size()

        screen.fill(
            (28, 29, 38)
        )

        sidebar_width = 180

        # ----------------------------------------------------
        # 左側章節Sidebar
        # ----------------------------------------------------

        pygame.draw.rect(
            screen,
            (22, 23, 31),
            (
                0,
                0,
                sidebar_width,
                height
            )
        )

        pygame.draw.line(
            screen,
            (65, 65, 80),
            (
                sidebar_width,
                0
            ),
            (
                sidebar_width,
                height
            ),
            width=2
        )

        sidebar_title = (
            self.game_ui.font_ui.render(
                "章節列表",
                True,
                (210, 210, 225)
            )
        )

        screen.blit(
            sidebar_title,
            (
                20,
                15
            )
        )

        chapters = self.get_chapters()

        chapter_buttons = {}

        chapter_height = 45

        available_left_height = (
            height - 120
        )

        total_left_height = (
            len(chapters)
            * chapter_height
        )

        max_left_scroll = min(
            0,
            available_left_height
            - total_left_height
        )

        self.left_scroll_y = max(
            max_left_scroll,
            min(
                0,
                self.left_scroll_y
            )
        )

        for (
            index,
            chapter
        ) in enumerate(
            chapters
        ):

            y = (
                60
                + self.left_scroll_y
                + index
                * chapter_height
            )

            if (
                y < 50
                or y > height - 70
            ):
                continue

            rect = pygame.Rect(
                10,
                y,
                sidebar_width - 20,
                38
            )

            self.game_ui.draw_button(
                screen,
                chapter.get(
                    "title",
                    chapter.get(
                        "id",
                        "Chapter"
                    )
                ),
                rect,
                rect.collidepoint(
                    mouse_pos
                ),
                bg_color=(45, 55, 75)
            )

            chapter_buttons[
                chapter.get(
                    "id",
                    str(index)
                )
            ] = rect


        # ----------------------------------------------------
        # 返回按鈕
        # ----------------------------------------------------

        back_rect = pygame.Rect(
            10,
            height - 50,
            sidebar_width - 20,
            40
        )

        self.game_ui.draw_button(
            screen,
            "返回",
            back_rect,
            back_rect.collidepoint(
                mouse_pos
            ),
            bg_color=(100, 55, 60)
        )


        # ====================================================
        # 右側內容區
        # ====================================================

        content_x = (
            sidebar_width + 25
        )

        content_width = (
            width
            - sidebar_width
            - 65
        )

        card_width = 95

        card_height = 110

        padding = 18

        columns = max(
            1,
            content_width
            // (
                card_width
                + padding
            )
        )


        # ----------------------------------------------------
        # 計算右側內容總高度
        # ----------------------------------------------------

        total_height = 0

        for chapter in chapters:

            item_count = len(
                chapter.get(
                    "items",
                    []
                )
            )

            rows = (
                item_count
                + columns
                - 1
            ) // columns

            total_height += (
                45
                + rows
                * (
                    card_height
                    + padding
                )
                + 25
            )


        visible_height = (
            height - 60
        )

        max_scroll = min(
            0,
            visible_height
            - total_height
        )

        self.right_scroll_y = max(
            max_scroll,
            min(
                0,
                self.right_scroll_y
            )
        )

        current_y = (
            20
            + self.right_scroll_y
        )

        item_buttons = {}


        # ----------------------------------------------------
        # 每一章
        # ----------------------------------------------------

        for chapter in chapters:

            chapter_title = (
                self.game_ui.font_large.render(
                    chapter.get(
                        "title",
                        "Chapter"
                    ),
                    True,
                    (240, 240, 245)
                )
            )

            screen.blit(
                chapter_title,
                (
                    content_x,
                    current_y
                )
            )

            current_y += 45

            items = chapter.get(
                "items",
                []
            )


            # ------------------------------------------------
            # 每個圖鑑物品
            # ------------------------------------------------

            for (
                index,
                item_id
            ) in enumerate(
                items
            ):

                row = (
                    index // columns
                )

                col = (
                    index % columns
                )

                x = (
                    content_x
                    + col
                    * (
                        card_width
                        + padding
                    )
                )

                y = (
                    current_y
                    + row
                    * (
                        card_height
                        + padding
                    )
                )

                # 超出畫面則不繪製
                if (
                    y + card_height < 0
                    or y > height
                ):
                    continue

                rect = pygame.Rect(
                    x,
                    y,
                    card_width,
                    card_height
                )

                hovered = (
                    rect.collidepoint(
                        mouse_pos
                    )
                )

                if hovered:

                    card_color = (
                        55,
                        60,
                        80
                    )

                    border_color = (
                        240,
                        210,
                        120
                    )

                else:

                    card_color = (
                        40,
                        45,
                        60
                    )

                    border_color = (
                        85,
                        85,
                        105
                    )

                pygame.draw.rect(
                    screen,
                    card_color,
                    rect,
                    border_radius=8
                )

                pygame.draw.rect(
                    screen,
                    border_color,
                    rect,
                    width=2,
                    border_radius=8
                )

                unlocked = (
                    self.is_unlocked(
                        game,
                        item_id
                    )
                )


                # --------------------------------------------
                # 物品圖示Placeholder
                # --------------------------------------------

                icon_rect = pygame.Rect(
                    rect.x + 10,
                    rect.y + 10,
                    rect.width - 20,
                    65
                )

                if unlocked:

                    pygame.draw.rect(
                        screen,
                        (
                            95,
                            105,
                            125
                        ),
                        icon_rect,
                        border_radius=6
                    )

                    item_data = (
                        self.objects.get(
                            item_id,
                            {}
                        )
                    )

                    name = item_data.get(
                        "name",
                        item_id
                    )

                    icon_text = (
                        self.game_ui
                        .font_small
                        .render(
                            "Item",
                            True,
                            (
                                225,
                                225,
                                235
                            )
                        )
                    )

                    screen.blit(
                        icon_text,
                        icon_text.get_rect(
                            center=icon_rect.center
                        )
                    )

                else:

                    pygame.draw.rect(
                        screen,
                        (
                            30,
                            34,
                            44
                        ),
                        icon_rect,
                        border_radius=6
                    )

                    question = (
                        self.game_ui
                        .font_title
                        .render(
                            "?",
                            True,
                            (
                                125,
                                125,
                                145
                            )
                        )
                    )

                    screen.blit(
                        question,
                        question.get_rect(
                            center=icon_rect.center
                        )
                    )

                    name = (
                        "未知物品"
                    )


                # --------------------------------------------
                # 物品名稱
                # --------------------------------------------

                name_surface = (
                    self.game_ui
                    .font_small
                    .render(
                        name,
                        True,
                        (
                            235,
                            235,
                            240
                        )
                    )
                )

                screen.blit(
                    name_surface,
                    name_surface.get_rect(
                        center=(
                            rect.centerx,
                            rect.bottom - 17
                        )
                    )
                )

                item_buttons[
                    item_id
                ] = rect


            # ------------------------------------------------
            # 下一章Y座標
            # ------------------------------------------------

            rows = (
                len(items)
                + columns
                - 1
            ) // columns

            current_y += (
                rows
                * (
                    card_height
                    + padding
                )
                + 25
            )


        # ====================================================
        # Scrollbar
        # ====================================================

        scrollbar_x = (
            width - 28
        )

        scrollbar_y = 50

        scrollbar_height = (
            height - 100
        )

        pygame.draw.rect(
            screen,
            (
                20,
                20,
                25
            ),
            (
                scrollbar_x,
                scrollbar_y,
                14,
                scrollbar_height
            ),
            border_radius=4
        )


        if total_height <= visible_height:

            thumb_height = (
                scrollbar_height
            )

            thumb_y = (
                scrollbar_y
            )

        else:

            thumb_height = max(
                35,
                int(
                    scrollbar_height
                    * (
                        visible_height
                        / total_height
                    )
                )
            )

            scroll_range = max(
                1,
                total_height
                - visible_height
            )

            ratio = (
                abs(
                    self.right_scroll_y
                )
                / scroll_range
            )

            ratio = min(
                1.0,
                max(
                    0.0,
                    ratio
                )
            )

            thumb_y = (
                scrollbar_y
                + int(
                    ratio
                    * (
                        scrollbar_height
                        - thumb_height
                    )
                )
            )


        thumb_rect = pygame.Rect(
            scrollbar_x,
            thumb_y,
            14,
            thumb_height
        )

        pygame.draw.rect(
            screen,
            (
                100,
                120,
                160
            ),
            thumb_rect,
            border_radius=4
        )


        # ====================================================
        # Progress
        # ====================================================

        unlocked_count, total_count = (
            self.get_progress(
                game
            )
        )

        progress_surface = (
            self.game_ui.font_ui.render(
                (
                    "蒐集進度："
                    f"{unlocked_count}"
                    f" / {total_count}"
                ),
                True,
                (
                    255,
                    220,
                    120
                )
            )
        )

        screen.blit(
            progress_surface,
            (
                width
                - progress_surface.get_width()
                - 45,

                height - 35
            )
        )


        # ====================================================
        # Item Modal
        # ====================================================

        modal_buttons = {}

        if self.selected_item is not None:

            modal_buttons = (
                self.draw_item_modal(
                    screen,
                    game,
                    mouse_pos
                )
            )


        return {
            "back": back_rect,

            "chapters": (
                chapter_buttons
            ),

            "items": (
                item_buttons
            ),

            "scrollbar": (
                thumb_rect
            ),

            "modal": (
                modal_buttons
            )
        }


    # ========================================================
    # Item Modal
    # ========================================================

    def draw_item_modal(
        self,
        screen,
        game,
        mouse_pos
    ):
        """顯示選中圖鑑項目的詳細資料。"""

        width, height = screen.get_size()

        overlay = pygame.Surface(
            (
                width,
                height
            ),
            pygame.SRCALPHA
        )

        overlay.fill(
            (0, 0, 0, 180)
        )

        screen.blit(
            overlay,
            (0, 0)
        )


        # ----------------------------------------------------
        # Modal大小
        # ----------------------------------------------------

        modal_width = min(
            500,
            width - 50
        )

        modal_height = min(
            330,
            height - 50
        )

        modal = pygame.Rect(
            (
                width
                - modal_width
            ) // 2,

            (
                height
                - modal_height
            ) // 2,

            modal_width,
            modal_height
        )


        pygame.draw.rect(
            screen,
            (
                42,
                45,
                58
            ),
            modal,
            border_radius=12
        )

        pygame.draw.rect(
            screen,
            (
                210,
                210,
                225
            ),
            modal,
            width=2,
            border_radius=12
        )


        item_id = (
            self.selected_item
        )

        unlocked = (
            self.is_unlocked(
                game,
                item_id
            )
        )


        # ====================================================
        # Locked / Unlocked
        # ====================================================

        if unlocked:

            item = self.objects.get(
                item_id,
                {}
            )

            title = item.get(
                "name",
                item_id
            )

            description = item.get(
                "description",
                ""
            )

        else:

            title = (
                "未知物品"
            )

            description = (
                "尚待解鎖"
            )


        # ====================================================
        # Title
        # ====================================================

        title_surface = (
            self.game_ui.font_large.render(
                title,
                True,
                (
                    255,
                    220,
                    140
                )
                if unlocked
                else
                (
                    160,
                    160,
                    170
                )
            )
        )

        screen.blit(
            title_surface,
            (
                modal.x + 30,
                modal.y + 25
            )
        )


        # ====================================================
        # Icon
        # ====================================================

        icon_rect = pygame.Rect(
            modal.x + 30,
            modal.y + 80,
            120,
            120
        )

        pygame.draw.rect(
            screen,
            (
                90,
                100,
                120
            )
            if unlocked
            else
            (
                30,
                34,
                44
            ),
            icon_rect,
            border_radius=8
        )

        pygame.draw.rect(
            screen,
            (
                160,
                165,
                180
            ),
            icon_rect,
            width=2,
            border_radius=8
        )


        if unlocked:

            placeholder = (
                self.game_ui.font_small.render(
                    "Item Placeholder",
                    True,
                    (
                        225,
                        225,
                        235
                    )
                )
            )

            screen.blit(
                placeholder,
                placeholder.get_rect(
                    center=icon_rect.center
                )
            )

        else:

            question = (
                self.game_ui.font_title.render(
                    "?",
                    True,
                    (
                        125,
                        125,
                        145
                    )
                )
            )

            screen.blit(
                question,
                question.get_rect(
                    center=icon_rect.center
                )
            )


        # ====================================================
        # Description
        # ====================================================

        text_x = (
            modal.x + 175
        )

        text_y = (
            modal.y + 85
        )

        text_width = (
            modal.width - 205
        )

        lines = wrap_text(
            description,
            self.game_ui.font_small,
            text_width
        )

        for line in lines:

            surface = (
                self.game_ui
                .font_small
                .render(
                    line,
                    True,
                    (
                        225,
                        225,
                        230
                    )
                )
            )

            screen.blit(
                surface,
                (
                    text_x,
                    text_y
                )
            )

            text_y += (
                self.game_ui
                .font_small
                .get_linesize()
                + 4
            )


        # ====================================================
        # Photo Special Information
        # ====================================================

        if (
            unlocked
            and item_id == "photo_1"
        ):

            photo_hint = (
                self.game_ui.font_small.render(
                    "照片可於Hotbar中查看正反面。",
                    True,
                    (
                        180,
                        190,
                        210
                    )
                )
            )

            screen.blit(
                photo_hint,
                (
                    modal.x + 30,
                    modal.bottom - 95
                )
            )


        # ====================================================
        # Close
        # ====================================================

        close_rect = pygame.Rect(
            modal.centerx - 55,
            modal.bottom - 55,
            110,
            35
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
    # Selection
    # ========================================================

    def select_item(
        self,
        item_id
    ):
        """開啟指定圖鑑物品詳細資料。"""

        self.selected_item = (
            item_id
        )


    def close_item(self):
        """關閉目前圖鑑Item Modal。"""

        self.selected_item = None
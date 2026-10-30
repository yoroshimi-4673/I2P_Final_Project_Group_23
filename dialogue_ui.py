import pygame


# ============================================================
# Dialogue Controller
# ============================================================

class DialogueController:
    """管理目前正在播放的對話。"""

    def __init__(self, typing_speed=35):
        self.dialogue_id = None

        self.lines = []

        self.current_index = 0

        self.visible_characters = 0

        self.typing_speed = typing_speed

        self.typing_timer = 0.0

        self.finished = True


    def start(
        self,
        dialogue_id,
        lines
    ):
        """開始播放新的對話。"""

        self.dialogue_id = dialogue_id

        self.lines = lines

        self.current_index = 0

        self.visible_characters = 0

        self.typing_timer = 0.0

        self.finished = (
            len(lines) == 0
        )


    def get_current_line(self):
        """取得目前對話句子。"""

        if self.finished:
            return None

        if (
            self.current_index
            >= len(self.lines)
        ):
            return None

        return self.lines[
            self.current_index
        ]


    def is_current_line_complete(self):
        """判斷目前文字是否全部顯示。"""

        line = self.get_current_line()

        if line is None:
            return True

        text = line.get(
            "text",
            ""
        )

        return (
            self.visible_characters
            >= len(text)
        )


    def complete_current_line(self):
        """立即顯示目前整句。"""

        line = self.get_current_line()

        if line is None:
            return

        self.visible_characters = len(
            line.get(
                "text",
                ""
            )
        )


    def advance(self):
        """玩家要求繼續對話。"""

        if self.finished:

            return "finished"

        if not self.is_current_line_complete():

            self.complete_current_line()

            return "line_completed"

        self.current_index += 1

        if (
            self.current_index
            >= len(self.lines)
        ):

            self.finished = True

            return "dialogue_finished"

        self.visible_characters = 0

        self.typing_timer = 0.0

        return "next_line"


    def update(self, dt):
        """更新打字機動畫。"""

        if self.finished:
            return

        line = self.get_current_line()

        if line is None:
            return

        text = line.get(
            "text",
            ""
        )

        if (
            self.visible_characters
            >= len(text)
        ):
            return

        self.typing_timer += dt

        count = int(
            self.typing_timer
            * self.typing_speed
        )

        if count <= 0:
            return

        self.visible_characters += count

        self.visible_characters = min(
            self.visible_characters,
            len(text)
        )

        self.typing_timer -= (
            count
            / self.typing_speed
        )


    def get_visible_text(self):
        """取得目前應顯示的部分文字。"""

        line = self.get_current_line()

        if line is None:
            return ""

        text = line.get(
            "text",
            ""
        )

        return text[
            :self.visible_characters
        ]


# ============================================================
# Choice Controller
# ============================================================

class ChoiceController:
    """管理可重複使用的選擇事件。"""

    def __init__(self):
        self.choice_id = None

        self.prompt = ""

        self.options = []

        self.selected_index = 0

        self.finished = True


    def start(
        self,
        choice_id,
        choice_data
    ):
        """載入Choice資料。"""

        self.choice_id = choice_id

        self.prompt = choice_data.get(
            "prompt",
            ""
        )

        self.options = []

        for (
            option_id,
            option_data
        ) in choice_data.get(
            "options",
            {}
        ).items():

            self.options.append(
                {
                    "id": option_id,

                    "text": option_data.get(
                        "text",
                        ""
                    ),

                    "result_text": option_data.get(
                        "result_text",
                        ""
                    ),

                    "target_space": option_data.get(
                        "target_space"
                    )
                }
            )

        self.selected_index = 0

        self.finished = (
            len(self.options) == 0
        )


    def move_up(self):
        """選擇上一個選項。"""

        if not self.options:
            return

        self.selected_index = (
            self.selected_index - 1
        ) % len(self.options)


    def move_down(self):
        """選擇下一個選項。"""

        if not self.options:
            return

        self.selected_index = (
            self.selected_index + 1
        ) % len(self.options)


    def select_current(self):
        """選擇目前反白項目。"""

        if not self.options:
            return None

        self.finished = True

        return self.options[
            self.selected_index
        ]


    def select_by_id(
        self,
        option_id
    ):
        """使用A/B/C等ID直接選擇。"""

        option_id = option_id.upper()

        for (
            index,
            option
        ) in enumerate(
            self.options
        ):

            if (
                option["id"].upper()
                == option_id
            ):

                self.selected_index = index

                self.finished = True

                return option

        return None


# ============================================================
# Text Wrap
# ============================================================

def wrap_text(
    text,
    font,
    max_width
):
    """依照像素寬度自動換行。"""

    lines = []

    current_line = ""

    for character in text:

        if character == "\n":

            lines.append(
                current_line
            )

            current_line = ""

            continue

        test_line = (
            current_line
            + character
        )

        width = font.size(
            test_line
        )[0]

        if (
            width > max_width
            and current_line
        ):

            lines.append(
                current_line
            )

            current_line = character

        else:

            current_line = test_line

    if current_line:

        lines.append(
            current_line
        )

    return lines


# ============================================================
# Dialogue Renderer
# ============================================================

def draw_dialogue_box(
    screen,
    dialogue_controller,
    font_name,
    font_text
):
    """繪製通用Dialogue Box。"""

    width, height = screen.get_size()

    box_width = int(
        width * 0.88
    )

    box_height = int(
        height * 0.27
    )

    box_x = (
        width - box_width
    ) // 2

    box_y = (
        height
        - box_height
        - 25
    )

    surface = pygame.Surface(
        (
            box_width,
            box_height
        ),
        pygame.SRCALPHA
    )

    surface.fill(
        (15, 15, 25, 225)
    )

    screen.blit(
        surface,
        (
            box_x,
            box_y
        )
    )

    pygame.draw.rect(
        screen,
        (210, 210, 220),
        (
            box_x,
            box_y,
            box_width,
            box_height
        ),
        width=2,
        border_radius=10
    )

    line = (
        dialogue_controller
        .get_current_line()
    )

    if line is None:
        return

    speaker = line.get(
        "speaker",
        ""
    )

    if speaker == "旁白":
        speaker = ""

    if speaker:

        name_surface = font_name.render(
            speaker,
            True,
            (255, 220, 140)
        )

        screen.blit(
            name_surface,
            (
                box_x + 25,
                box_y + 18
            )
        )

        text_start_y = (
            box_y + 58
        )

    else:

        text_start_y = (
            box_y + 30
        )

    visible_text = (
        dialogue_controller
        .get_visible_text()
    )

    wrapped = wrap_text(
        visible_text,
        font_text,
        box_width - 50
    )

    line_height = (
        font_text.get_linesize()
    )

    for (
        index,
        text_line
    ) in enumerate(
        wrapped
    ):

        text_surface = font_text.render(
            text_line,
            True,
            (240, 240, 240)
        )

        screen.blit(
            text_surface,
            (
                box_x + 25,

                text_start_y
                + index
                * line_height
            )
        )

    if (
        dialogue_controller
        .is_current_line_complete()
    ):

        continue_surface = (
            font_text.render(
                "▶",
                True,
                (220, 220, 220)
            )
        )

        screen.blit(
            continue_surface,
            (
                box_x
                + box_width
                - 45,

                box_y
                + box_height
                - 40
            )
        )


# ============================================================
# Choice Renderer
# ============================================================

def draw_choice_panel(
    screen,
    controller,
    font_title,
    font_text,
    mouse_pos
):
    """繪製Choice Panel並回傳按鈕Rect。"""

    width, height = screen.get_size()

    panel_width = min(
        540,
        int(width * 0.72)
    )

    option_height = 50
    option_gap = 12

    panel_height = (
        135
        + len(controller.options)
        * (
            option_height
            + option_gap
        )
    )

    panel_x = (
        width - panel_width
    ) // 2

    panel_y = (
        height - panel_height
    ) // 2

    panel = pygame.Surface(
        (
            panel_width,
            panel_height
        ),
        pygame.SRCALPHA
    )

    panel.fill(
        (20, 20, 30, 235)
    )

    screen.blit(
        panel,
        (
            panel_x,
            panel_y
        )
    )

    pygame.draw.rect(
        screen,
        (210, 210, 220),
        (
            panel_x,
            panel_y,
            panel_width,
            panel_height
        ),
        width=2,
        border_radius=12
    )

    prompt_lines = wrap_text(
        controller.prompt,
        font_title,
        panel_width - 60
    )

    prompt_y = (
        panel_y + 25
    )

    for line in prompt_lines:

        surface = font_title.render(
            line,
            True,
            (245, 245, 245)
        )

        screen.blit(
            surface,
            surface.get_rect(
                center=(
                    width // 2,
                    prompt_y
                )
            )
        )

        prompt_y += (
            font_title.get_linesize()
        )

    option_start_y = max(
        panel_y + 95,
        prompt_y + 15
    )

    option_rects = []

    for (
        index,
        option
    ) in enumerate(
        controller.options
    ):

        rect = pygame.Rect(
            panel_x + 40,

            option_start_y
            + index
            * (
                option_height
                + option_gap
            ),

            panel_width - 80,

            option_height
        )

        hovered = rect.collidepoint(
            mouse_pos
        )

        selected = (
            index
            == controller.selected_index
        )

        if (
            hovered
            or selected
        ):

            color = (
                70,
                85,
                110
            )

        else:

            color = (
                40,
                45,
                60
            )

        pygame.draw.rect(
            screen,
            color,
            rect,
            border_radius=8
        )

        pygame.draw.rect(
            screen,
            (230, 230, 240),
            rect,
            width=2,
            border_radius=8
        )

        text = (
            f"{option['id']}. "
            f"{option['text']}"
        )

        surface = font_text.render(
            text,
            True,
            (245, 245, 245)
        )

        screen.blit(
            surface,
            surface.get_rect(
                center=rect.center
            )
        )

        option_rects.append(
            (
                rect,
                option
            )
        )

    return option_rects
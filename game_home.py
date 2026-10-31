import json
import sys
from pathlib import Path

import pygame

from ui.codex_ui import CodexUI

from ui.dialogue_ui import (
    DialogueController,
    ChoiceController,
    draw_dialogue_box,
    draw_choice_panel
)

from game_manager import GameManager

from game_states import (
    DIALOGUE,
    CHOICE,
    SPACE,
    PASSWORD,
    SUCCESS,
    GAME_OVER
)

from ui.game_ui import GameUI

from ui.interaction_ui import InteractionUI

from interaction_manager import (
    finish_photo_story_dialogue,
    leave_puzzle,
    search_object
)


# ============================================================
# 初始化
# ============================================================

pygame.init()

BASE_DIR = Path(__file__).resolve().parent  # 取得目前專案根目錄位置

LEVELS_PATH = (
    BASE_DIR
    / "data"
    / "levels.json"
)

OBJECTS_PATH = (
    BASE_DIR
    / "data"
    / "objects.json"
)

DIALOGUE_PATH = (
    BASE_DIR
    / "data"
    / "dialogue.json"
)

UI_LAYOUT_PATH = (
    BASE_DIR
    / "data"
    / "ui_layout.json"
)

CODEX_PATH = (
    BASE_DIR
    / "data"
    / "codex.json"
)


def load_json(path):
    """讀取指定JSON資料檔案。"""

    with open(
        path,
        "r",
        encoding="utf-8"
    ) as file:

        return json.load(file)


levels = load_json(
    LEVELS_PATH
)

objects = load_json(
    OBJECTS_PATH
)

dialogues = load_json(
    DIALOGUE_PATH
)

ui_layout = load_json(
    UI_LAYOUT_PATH
)

codex_data = load_json(
    CODEX_PATH
)


# ============================================================
# Pygame Window
# ============================================================

screen_width = (
    ui_layout[
        "base_resolution"
    ]["width"]
)

screen_height = (
    ui_layout[
        "base_resolution"
    ]["height"]
)

screen = pygame.display.set_mode(
    (
        screen_width,
        screen_height
    ),
    pygame.RESIZABLE
)

pygame.display.set_caption(
    "數到100"
)

clock = pygame.time.Clock()


# ============================================================
# Managers
# ============================================================

game = GameManager()

game_ui = GameUI(
    ui_layout,
    levels,
    objects
)

dialogue_controller = DialogueController(
    typing_speed=35
)

choice_controller = ChoiceController()

interaction_ui = InteractionUI(
    game_ui,
    game,
    objects,
    levels
)

codex_ui = CodexUI(
    game_ui,
    codex_data,
    objects
)


# ============================================================
# UI State
#
# 注意：
# 這些不是game_states.py的核心遊戲狀態。
# ============================================================

UI_MENU = "menu"
UI_GAME = "game"
UI_CODEX = "codex"

ui_screen = UI_MENU  # 記錄目前主要顯示的UI頁面

ui_overlay = None  # 記錄Settings等覆蓋式介面

previous_ui_screen = UI_MENU  # 圖鑑返回時使用的上一個畫面

codex_return_to_settings = False  # 記錄圖鑑是否由設定頁進入


# ============================================================
# Settings
# ============================================================

volume = 50

looks = [
    (255, 90, 90),
    (90, 220, 120),
    (100, 140, 255)
]

current_look_index = 0

dragging_volume = False


# ============================================================
# Hotbar
# ============================================================

selected_slot = 0

selected_item = None

hotbar_offset = 0


# ============================================================
# Dialogue Flow
# ============================================================

pending_target_space = None  # Choice結果播放後要前往的空間

dialogue_after_action = None  # Dialogue結束後要執行的流程

chapter_end_text = (
    "你只解開了一把鎖。"
    "但你還沒解開自己。"
)


# ============================================================
# Game Flow
# ============================================================

def start_new_game():
    """建立全新的第一章遊戲流程。"""

    global ui_screen
    global ui_overlay

    global selected_slot
    global selected_item
    global hotbar_offset

    global pending_target_space
    global dialogue_after_action

    game.reset_game()

    interaction_ui.close()

    codex_ui.close_item()

    selected_slot = 0
    selected_item = None
    hotbar_offset = 0

    dialogue_controller.start(
        "intro",
        dialogues.get(
            "intro",
            []
        )
    )

    game.game_state = DIALOGUE

    ui_screen = UI_GAME

    ui_overlay = None

    pending_target_space = None

    dialogue_after_action = (
        "start_first_choice"
    )


def start_first_choice():
    """開始307房第一次A/B/C選擇。"""

    game.current_scene = (
        "scene_04_choice"
    )

    game.game_state = CHOICE

    choice_controller.start(
        "scene_04_choice",
        dialogues[
            "scene_04_choice"
        ]
    )


def start_choice_result(
    selected_option
):
    """播放玩家選擇之後的結果文字。"""

    global pending_target_space
    global dialogue_after_action

    pending_target_space = (
        selected_option.get(
            "target_space"
        )
    )

    result_text = (
        selected_option.get(
            "result_text",
            ""
        )
    )

    dialogue_controller.start(
        "scene_04_choice_result",
        [
            {
                "speaker": "",
                "text": result_text
            }
        ]
    )

    game.game_state = DIALOGUE

    dialogue_after_action = (
        "enter_selected_space"
    )


def start_photo_story(
    photo_result
):
    """照片背面事件後播放劇情Dialogue。"""

    global dialogue_after_action

    dialogue_lines = []

    # 第一段黎琛台詞
    dialogue_lines.append(
        {
            "speaker": "黎琛",
            "text": "空間D……還有？"
        }
    )

    # 旁白
    dialogue_lines.append(
        {
            "speaker": "",
            "text": (
                "牆上顯示器突然亮起。"
            )
        }
    )

    system_message = photo_result.get(
        "system_message",
        {}
    )

    values = system_message.get(
        "values",
        {}
    )

    system_text = (
        "【收斂率更新】\n"
        f"空間A：{values.get('A', 81)}%\n"
        f"空間B：{values.get('B', 55)}%\n"
        f"空間C：{values.get('C', 37)}%"
    )

    dialogue_lines.append(
        {
            "speaker": "",
            "text": system_text
        }
    )

    dialogue_lines.append(
        {
            "speaker": "黎琛",
            "text": (
                "收斂率在漲……"
                "這個房間在消失。"
                "我得走。"
            )
        }
    )

    dialogue_controller.start(
        "photo_back_story",
        dialogue_lines
    )

    game.game_state = DIALOGUE

    dialogue_after_action = (
        "finish_photo_story"
    )


def start_chapter_end(
    ending_result
):
    """出口門進入後播放第一章結尾Dialogue。"""

    global dialogue_after_action
    global chapter_end_text

    ending_dialogue = (
        ending_result.get(
            "dialogue",
            []
        )
    )

    chapter_end_text = (
        ending_result.get(
            "ending_text",
            chapter_end_text
        )
    )

    dialogue_controller.start(
        "chapter_1_end",
        ending_dialogue
    )

    # enter_door()已經將狀態改為SUCCESS，
    # 這裡暫時切回DIALOGUE播放結尾內容。
    game.game_state = DIALOGUE

    dialogue_after_action = (
        "show_chapter_end"
    )


def finish_dialogue_action():
    """依照Dialogue用途處理後續遊戲流程。"""

    global dialogue_after_action
    global pending_target_space

    action = dialogue_after_action

    dialogue_after_action = None

    if action == "start_first_choice":

        start_first_choice()

    elif action == "enter_selected_space":

        if pending_target_space is not None:

            game.current_scene = (
                "exploration"
            )

            game.enter_space(
                pending_target_space
            )

        pending_target_space = None

    elif action == "finish_photo_story":

        finish_photo_story_dialogue(
            game
        )

    elif action == "show_chapter_end":

        game.game_state = SUCCESS


# ============================================================
# Choice Keyboard
# ============================================================

def handle_choice_key(event):
    """處理Choice畫面的鍵盤操作。"""

    selected_option = None

    if event.key == pygame.K_UP:

        choice_controller.move_up()

    elif event.key == pygame.K_DOWN:

        choice_controller.move_down()

    elif event.key == pygame.K_RETURN:

        selected_option = (
            choice_controller
            .select_current()
        )

    elif event.key == pygame.K_a:

        selected_option = (
            choice_controller
            .select_by_id(
                "A"
            )
        )

    elif event.key == pygame.K_b:

        selected_option = (
            choice_controller
            .select_by_id(
                "B"
            )
        )

    elif event.key == pygame.K_c:

        selected_option = (
            choice_controller
            .select_by_id(
                "C"
            )
        )

    if selected_option is not None:

        start_choice_result(
            selected_option
        )


# ============================================================
# Container Child
# ============================================================

def open_container_child(
    child_id
):
    """
    開啟Container子物件。

    已搜尋過的Searchable不再顯示是/否，
    而是直接顯示empty_text。
    """

    child = objects[
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
            and game.has_discovered_item(
                item_id
            )
        ):

            interaction_ui.push_current()

            interaction_ui.current_object_id = (
                child_id
            )

            interaction_ui.result = (
                search_object(
                    game,
                    child_id,
                    objects
                )
            )

            interaction_ui.mode = (
                "message"
            )

            return

    interaction_ui.open_child(
        child_id
    )


# ============================================================
# Hotbar
# ============================================================

def get_selected_hotbar_item():
    """取得目前Hotbar真正選中的item_id。"""

    visible_items = (
        game_ui.get_visible_inventory(
            game,
            hotbar_offset
        )
    )

    if (
        selected_slot < 0
        or selected_slot
        >= len(visible_items)
    ):

        return None

    return visible_items[
        selected_slot
    ]


def open_hotbar_item(
    item_id
):
    """從Hotbar開啟物品詳細內容。"""

    if item_id is None:
        return

    if item_id == "photo_1":

        interaction_ui.open_photo(
            item_id,
            mode="inventory"
        )

        return

    interaction_ui.open_object(
        item_id
    )


# ============================================================
# Codex Navigation
# ============================================================

def open_codex(
    from_settings=False
):
    """進入Codex並記錄正確返回位置。"""

    global ui_screen
    global previous_ui_screen
    global ui_overlay
    global codex_return_to_settings

    previous_ui_screen = (
        ui_screen
    )

    codex_return_to_settings = (
        from_settings
    )

    ui_screen = UI_CODEX

    ui_overlay = None


def close_codex():
    """離開Codex並返回原本畫面。"""

    global ui_screen
    global ui_overlay
    global codex_return_to_settings

    codex_ui.close_item()

    ui_screen = (
        previous_ui_screen
    )

    if codex_return_to_settings:

        ui_overlay = "settings"

    codex_return_to_settings = False


# ============================================================
# Game Over UI
# ============================================================

def draw_game_over(
    mouse_pos
):
    """繪製GAME OVER畫面。"""

    screen.fill(
        (25, 15, 18)
    )

    width, height = (
        screen.get_size()
    )

    title = game_ui.font_title.render(
        "GAME OVER",
        True,
        (235, 90, 90)
    )

    screen.blit(
        title,
        title.get_rect(
            center=(
                width // 2,
                height // 2 - 120
            )
        )
    )

    if (
        game.game_over_reason
        == "space_c_locked"
    ):

        message_lines = [
            "空間 C 已永久封鎖。",
            "你將永遠被困在這個空間。"
        ]

    else:

        message_lines = [
            "遊戲結束。"
        ]

    y = (
        height // 2 - 45
    )

    for line in message_lines:

        surface = (
            game_ui.font_ui.render(
                line,
                True,
                (235, 225, 225)
            )
        )

        screen.blit(
            surface,
            surface.get_rect(
                center=(
                    width // 2,
                    y
                )
            )
        )

        y += 30

    button_width = 160
    button_height = 42

    buttons = {
        "restart": pygame.Rect(
            width // 2
            - button_width // 2,

            height // 2 + 45,

            button_width,
            button_height
        ),

        "menu": pygame.Rect(
            width // 2
            - button_width // 2,

            height // 2 + 100,

            button_width,
            button_height
        ),

        "settings": pygame.Rect(
            width // 2
            - button_width // 2,

            height // 2 + 155,

            button_width,
            button_height
        )
    }

    game_ui.draw_button(
        screen,
        "重新開始",
        buttons["restart"],
        buttons["restart"].collidepoint(
            mouse_pos
        )
    )

    game_ui.draw_button(
        screen,
        "回主選單",
        buttons["menu"],
        buttons["menu"].collidepoint(
            mouse_pos
        )
    )

    game_ui.draw_button(
        screen,
        "設定",
        buttons["settings"],
        buttons["settings"].collidepoint(
            mouse_pos
        )
    )

    return buttons


# ============================================================
# Chapter Ending UI
# ============================================================

def draw_chapter_end(
    mouse_pos
):
    """繪製第一章結束畫面。"""

    screen.fill(
        (25, 25, 32)
    )

    width, height = (
        screen.get_size()
    )

    title = game_ui.font_title.render(
        "Chapter 1",
        True,
        (245, 245, 245)
    )

    screen.blit(
        title,
        title.get_rect(
            center=(
                width // 2,
                height // 2 - 120
            )
        )
    )

    end_surface = (
        game_ui.font_large.render(
            "— END —",
            True,
            (220, 220, 225)
        )
    )

    screen.blit(
        end_surface,
        end_surface.get_rect(
            center=(
                width // 2,
                height // 2 - 70
            )
        )
    )

    quote_lines = [
        "「你只解開了一把鎖。",
        "但你還沒解開自己。」"
    ]

    y = (
        height // 2
    )

    for line in quote_lines:

        surface = (
            game_ui.font_ui.render(
                line,
                True,
                (230, 230, 235)
            )
        )

        screen.blit(
            surface,
            surface.get_rect(
                center=(
                    width // 2,
                    y
                )
            )
        )

        y += 32

    buttons = {
        "settings": pygame.Rect(
            width // 2 - 175,
            height // 2 + 100,
            150,
            42
        ),

        "menu": pygame.Rect(
            width // 2 + 25,
            height // 2 + 100,
            150,
            42
        )
    }

    game_ui.draw_button(
        screen,
        "設定",
        buttons["settings"],
        buttons["settings"].collidepoint(
            mouse_pos
        )
    )

    game_ui.draw_button(
        screen,
        "回到主選單",
        buttons["menu"],
        buttons["menu"].collidepoint(
            mouse_pos
        )
    )

    return buttons


# ============================================================
# Interaction Keyboard
# ============================================================

def handle_interaction_key(
    event
):
    """處理Interaction UI的鍵盤輸入。"""

    if not interaction_ui.is_open():

        return

    # --------------------------------------------------------
    # Password
    # --------------------------------------------------------

    if interaction_ui.mode == "password":

        if (
            pygame.K_0
            <= event.key
            <= pygame.K_9
        ):

            digit = (
                event.key
                - pygame.K_0
            )

            interaction_ui.add_password_digit(
                digit
            )

        elif event.key == pygame.K_BACKSPACE:

            interaction_ui.remove_password_digit()

        elif event.key == pygame.K_RETURN:

            interaction_ui.submit_password()

            if (
                interaction_ui.result
                is not None
                and interaction_ui.result.get(
                    "status"
                )
                == "game_over"
            ):

                interaction_ui.close()

        elif event.key == pygame.K_ESCAPE:

            leave_puzzle(
                game
            )

            interaction_ui.close()

        return

    # --------------------------------------------------------
    # General Interaction Escape
    # --------------------------------------------------------

    if event.key == pygame.K_ESCAPE:

        if interaction_ui.parent_stack:

            interaction_ui.go_back()

        else:

            interaction_ui.close()


# ============================================================
# Interaction Mouse
# ============================================================

def handle_interaction_click(
    buttons,
    mouse_pos
):
    """處理所有Interaction Popup滑鼠操作。"""

    if not interaction_ui.is_open():

        return

    mode = interaction_ui.mode

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

            interaction_ui.close()

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

                open_container_child(
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

            interaction_ui.confirm_search()

        elif buttons[
            "no"
        ].collidepoint(
            mouse_pos
        ):

            interaction_ui.go_back()

    # ========================================================
    # Inspectable
    # ========================================================

    elif mode == "inspectable":

        if buttons[
            "back"
        ].collidepoint(
            mouse_pos
        ):

            interaction_ui.go_back()

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
                interaction_ui.result[
                    "status"
                ]
                == "rift_available"
            ):

                interaction_ui.confirm_rift()

        elif buttons[
            "cancel"
        ].collidepoint(
            mouse_pos
        ):

            interaction_ui.close()

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

                interaction_ui.add_password_digit(
                    digit
                )

                return

        if buttons[
            "clear"
        ].collidepoint(
            mouse_pos
        ):

            interaction_ui.clear_password()

        elif buttons[
            "submit"
        ].collidepoint(
            mouse_pos
        ):

            interaction_ui.submit_password()

            if (
                interaction_ui.result
                is not None
                and interaction_ui.result.get(
                    "status"
                )
                == "game_over"
            ):

                interaction_ui.close()

        elif buttons[
            "back"
        ].collidepoint(
            mouse_pos
        ):

            leave_puzzle(
                game
            )

            interaction_ui.close()

    # ========================================================
    # Photo
    # ========================================================

    elif mode == "photo":

        if buttons[
            "front"
        ].collidepoint(
            mouse_pos
        ):

            interaction_ui.view_photo_front()

        elif buttons[
            "back"
        ].collidepoint(
            mouse_pos
        ):

            result = (
                interaction_ui
                .view_photo_back()
            )

            if (
                result.get(
                    "status"
                )
                == "photo_story_triggered"
            ):

                interaction_ui.close()

                start_photo_story(
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

            interaction_ui.close()

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
                interaction_ui
                .confirm_door()
            )

            if (
                result.get(
                    "status"
                )
                == "chapter_end"
            ):

                interaction_ui.close()

                start_chapter_end(
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

            interaction_ui.close()

        elif (
            "close" in buttons
            and buttons[
                "close"
            ].collidepoint(
                mouse_pos
            )
        ):

            interaction_ui.close()

    # ========================================================
    # Item
    # ========================================================

    elif mode == "item":

        if buttons[
            "close"
        ].collidepoint(
            mouse_pos
        ):

            interaction_ui.close()

    # ========================================================
    # Item Notification
    # ========================================================

    elif mode == "item_notification":

        if buttons[
            "ok"
        ].collidepoint(
            mouse_pos
        ):

            interaction_ui.go_back()

    # ========================================================
    # Message
    # ========================================================

    elif mode == "message":

        if buttons[
            "ok"
        ].collidepoint(
            mouse_pos
        ):

            interaction_ui.go_back()


# ============================================================
# Main Loop
# ============================================================

running = True

while running:

    dt = (
        clock.tick(60)
        / 1000.0
    )

    mouse_pos = (
        pygame.mouse.get_pos()
    )

    mouse_clicked = False

    # 每一幀重新建立目前畫面Hitbox資料
    menu_buttons = {}

    settings_buttons = {}

    object_rects = {}

    choice_rects = []

    hotbar_data = None

    settings_button_rect = None

    codex_buttons = {}

    interaction_buttons = {}

    game_over_buttons = {}

    ending_buttons = {}


    # ========================================================
    # Events
    # ========================================================

    for event in pygame.event.get():

        if event.type == pygame.QUIT:

            running = False


        # ====================================================
        # Resize
        # ====================================================

        elif event.type == pygame.VIDEORESIZE:

            screen_width = max(
                640,
                event.w
            )

            screen_height = max(
                480,
                event.h
            )

            screen = pygame.display.set_mode(
                (
                    screen_width,
                    screen_height
                ),
                pygame.RESIZABLE
            )


        # ====================================================
        # Mouse
        # ====================================================

        elif (
            event.type
            == pygame.MOUSEBUTTONDOWN
            and event.button == 1
        ):

            mouse_clicked = True


        elif (
            event.type
            == pygame.MOUSEBUTTONUP
            and event.button == 1
        ):

            dragging_volume = False

            codex_ui.dragging_scrollbar = (
                False
            )


        # ====================================================
        # Mouse Wheel
        # ====================================================

        elif event.type == pygame.MOUSEWHEEL:

            if ui_screen == UI_CODEX:

                codex_ui.handle_wheel(
                    event,
                    mouse_pos
                )

            elif (
                ui_screen == UI_GAME
                and game.game_state == SPACE
                and ui_overlay is None
                and not interaction_ui.is_open()
            ):

                visible_items = (
                    game_ui
                    .get_visible_inventory(
                        game,
                        hotbar_offset
                    )
                )

                if visible_items:

                    if event.y > 0:

                        selected_slot = max(
                            0,
                            selected_slot - 1
                        )

                    elif event.y < 0:

                        selected_slot = min(
                            len(
                                visible_items
                            ) - 1,
                            selected_slot + 1
                        )


        # ====================================================
        # Keyboard
        # ====================================================

        elif event.type == pygame.KEYDOWN:

            # ------------------------------------------------
            # Settings優先
            # ------------------------------------------------

            if ui_overlay == "settings":

                if event.key == pygame.K_ESCAPE:

                    ui_overlay = None

                continue


            # ------------------------------------------------
            # Codex
            # ------------------------------------------------

            if ui_screen == UI_CODEX:

                if codex_ui.selected_item is not None:

                    if event.key == pygame.K_ESCAPE:

                        codex_ui.close_item()

                elif event.key == pygame.K_ESCAPE:

                    close_codex()

                continue


            # ------------------------------------------------
            # Interaction
            # ------------------------------------------------

            if (
                ui_screen == UI_GAME
                and interaction_ui.is_open()
            ):

                handle_interaction_key(
                    event
                )

                continue


            # ------------------------------------------------
            # Dialogue
            # ------------------------------------------------

            if (
                ui_screen == UI_GAME
                and game.game_state
                == DIALOGUE
            ):

                if event.key in (
                    pygame.K_RETURN,
                    pygame.K_SPACE
                ):

                    result = (
                        dialogue_controller
                        .advance()
                    )

                    if (
                        result
                        == "dialogue_finished"
                    ):

                        finish_dialogue_action()

                continue


            # ------------------------------------------------
            # Choice
            # ------------------------------------------------

            if (
                ui_screen == UI_GAME
                and game.game_state
                == CHOICE
            ):

                handle_choice_key(
                    event
                )

                continue


            # ------------------------------------------------
            # Exploration
            # ------------------------------------------------

            if (
                ui_screen == UI_GAME
                and game.game_state
                == SPACE
            ):

                if event.key == pygame.K_ESCAPE:

                    ui_overlay = "settings"

                elif event.key == pygame.K_LEFT:

                    selected_slot = max(
                        0,
                        selected_slot - 1
                    )

                elif event.key == pygame.K_RIGHT:

                    visible_items = (
                        game_ui
                        .get_visible_inventory(
                            game,
                            hotbar_offset
                        )
                    )

                    if visible_items:

                        selected_slot = min(
                            len(
                                visible_items
                            ) - 1,
                            selected_slot + 1
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

                    visible_items = (
                        game_ui
                        .get_visible_inventory(
                            game,
                            hotbar_offset
                        )
                    )

                    if index < len(
                        visible_items
                    ):

                        selected_slot = index

                        selected_item = (
                            visible_items[
                                index
                            ]
                        )

                elif event.key == pygame.K_RETURN:

                    selected_item = (
                        get_selected_hotbar_item()
                    )

                    open_hotbar_item(
                        selected_item
                    )

                continue


            # ------------------------------------------------
            # GAME OVER
            # ------------------------------------------------

            if (
                ui_screen == UI_GAME
                and game.game_state
                == GAME_OVER
            ):

                if event.key == pygame.K_ESCAPE:

                    ui_overlay = "settings"

                continue


            # ------------------------------------------------
            # SUCCESS
            # ------------------------------------------------

            if (
                ui_screen == UI_GAME
                and game.game_state
                == SUCCESS
            ):

                if event.key == pygame.K_ESCAPE:

                    ui_overlay = "settings"

                continue


    # ========================================================
    # Update
    # ========================================================

    if (
        ui_screen == UI_GAME
        and game.game_state
        == DIALOGUE
        and ui_overlay is None
    ):

        dialogue_controller.update(
            dt
        )


    # ========================================================
    # Render Main Menu
    # ========================================================

    if ui_screen == UI_MENU:

        menu_buttons = (
            game_ui.draw_main_menu(
                screen,
                mouse_pos
            )
        )


    # ========================================================
    # Render Codex
    # ========================================================

    elif ui_screen == UI_CODEX:

        codex_buttons = (
            codex_ui.draw(
                screen,
                game,
                mouse_pos
            )
        )


    # ========================================================
    # Render Game
    # ========================================================

    elif ui_screen == UI_GAME:

        # ----------------------------------------------------
        # Dialogue
        # ----------------------------------------------------

        if game.game_state == DIALOGUE:

            dialogue_id = (
                dialogue_controller
                .dialogue_id
            )

            if dialogue_id == "intro":

                game_ui.draw_intro_background(
                    screen,
                    dialogue_controller
                )

            elif dialogue_id in (
                "scene_04_choice_result",
            ):

                game_ui.draw_room_307(
                    screen
                )

            elif dialogue_id == "photo_back_story":

                # 照片劇情仍發生於Space C
                game_ui.draw_space(
                    screen,
                    game,
                    mouse_pos,
                    looks[
                        current_look_index
                    ]
                )

            elif dialogue_id == "chapter_1_end":

                screen.fill(
                    (235, 235, 235)
                )

                corridor_text = (
                    game_ui.font_large
                    .render(
                        (
                            "無限白色走廊 "
                            "/ Background Placeholder"
                        ),
                        True,
                        (45, 45, 50)
                    )
                )

                screen.blit(
                    corridor_text,
                    corridor_text.get_rect(
                        center=(
                            screen.get_width()
                            // 2,

                            80
                        )
                    )
                )

            else:

                game_ui.draw_room_307(
                    screen
                )

            draw_dialogue_box(
                screen,
                dialogue_controller,
                game_ui.font_ui,
                game_ui.font_ui
            )

            settings_button_rect = (
                game_ui
                .draw_settings_button(
                    screen,
                    mouse_pos
                )
            )


        # ----------------------------------------------------
        # Choice
        # ----------------------------------------------------

        elif game.game_state == CHOICE:

            game_ui.draw_room_307(
                screen
            )

            choice_rects = (
                draw_choice_panel(
                    screen,
                    choice_controller,
                    game_ui.font_large,
                    game_ui.font_ui,
                    mouse_pos
                )
            )

            settings_button_rect = (
                game_ui
                .draw_settings_button(
                    screen,
                    mouse_pos
                )
            )


        # ----------------------------------------------------
        # SPACE
        # ----------------------------------------------------

        elif game.game_state == SPACE:

            object_rects = (
                game_ui.draw_space(
                    screen,
                    game,
                    mouse_pos,
                    looks[
                        current_look_index
                    ]
                )
            )

            settings_button_rect = (
                game_ui
                .draw_settings_button(
                    screen,
                    mouse_pos
                )
            )

            hotbar_data = (
                game_ui.draw_hotbar(
                    screen,
                    game,
                    selected_slot,
                    hotbar_offset,
                    mouse_pos
                )
            )


        # ----------------------------------------------------
        # PASSWORD
        #
        # Password本身由InteractionUI顯示，
        # 底層仍保留目前Space畫面。
        # ----------------------------------------------------

        elif game.game_state == PASSWORD:

            object_rects = (
                game_ui.draw_space(
                    screen,
                    game,
                    mouse_pos,
                    looks[
                        current_look_index
                    ]
                )
            )

            hotbar_data = (
                game_ui.draw_hotbar(
                    screen,
                    game,
                    selected_slot,
                    hotbar_offset,
                    mouse_pos
                )
            )


        # ----------------------------------------------------
        # GAME OVER
        # ----------------------------------------------------

        elif game.game_state == GAME_OVER:

            game_over_buttons = (
                draw_game_over(
                    mouse_pos
                )
            )


        # ----------------------------------------------------
        # SUCCESS
        # ----------------------------------------------------

        elif game.game_state == SUCCESS:

            ending_buttons = (
                draw_chapter_end(
                    mouse_pos
                )
            )


        # ====================================================
        # Interaction Overlay
        # ====================================================

        if (
            interaction_ui.is_open()
            and ui_overlay is None
        ):

            interaction_buttons = (
                interaction_ui.draw(
                    screen,
                    mouse_pos
                )
            )


    # ========================================================
    # Settings Overlay
    # ========================================================

    if ui_overlay == "settings":

        settings_buttons = (
            game_ui.draw_settings_overlay(
                screen,
                mouse_pos,
                volume,
                current_look_index,
                looks
            )
        )


    # ========================================================
    # Mouse Click
    # ========================================================

    if mouse_clicked:

        # ----------------------------------------------------
        # Settings Overlay
        # ----------------------------------------------------

        if ui_overlay == "settings":

            if settings_buttons:

                if settings_buttons[
                    "slider"
                ].collidepoint(
                    mouse_pos
                ):

                    dragging_volume = True


                elif settings_buttons[
                    "800"
                ].collidepoint(
                    mouse_pos
                ):

                    screen_width = 800
                    screen_height = 600

                    screen = (
                        pygame.display
                        .set_mode(
                            (
                                screen_width,
                                screen_height
                            ),
                            pygame.RESIZABLE
                        )
                    )


                elif settings_buttons[
                    "1024"
                ].collidepoint(
                    mouse_pos
                ):

                    screen_width = 1024
                    screen_height = 768

                    screen = (
                        pygame.display
                        .set_mode(
                            (
                                screen_width,
                                screen_height
                            ),
                            pygame.RESIZABLE
                        )
                    )


                elif settings_buttons[
                    "look"
                ].collidepoint(
                    mouse_pos
                ):

                    current_look_index = (
                        current_look_index
                        + 1
                    ) % len(looks)


                elif settings_buttons[
                    "codex"
                ].collidepoint(
                    mouse_pos
                ):

                    open_codex(
                        from_settings=True
                    )


                elif settings_buttons[
                    "menu"
                ].collidepoint(
                    mouse_pos
                ):

                    interaction_ui.close()

                    ui_screen = UI_MENU

                    ui_overlay = None


                elif settings_buttons[
                    "close"
                ].collidepoint(
                    mouse_pos
                ):

                    ui_overlay = None


        # ----------------------------------------------------
        # Main Menu
        # ----------------------------------------------------

        elif ui_screen == UI_MENU:

            if menu_buttons[
                "start"
            ].collidepoint(
                mouse_pos
            ):

                start_new_game()


            elif menu_buttons[
                "codex"
            ].collidepoint(
                mouse_pos
            ):

                open_codex(
                    from_settings=False
                )


            elif menu_buttons[
                "settings"
            ].collidepoint(
                mouse_pos
            ):

                ui_overlay = (
                    "settings"
                )


            elif menu_buttons[
                "exit"
            ].collidepoint(
                mouse_pos
            ):

                running = False


        # ----------------------------------------------------
        # Codex
        # ----------------------------------------------------

        elif ui_screen == UI_CODEX:

            modal_buttons = (
                codex_buttons.get(
                    "modal",
                    {}
                )
            )

            # Item Modal優先攔截
            if (
                codex_ui.selected_item
                is not None
            ):

                if (
                    "close"
                    in modal_buttons
                    and modal_buttons[
                        "close"
                    ].collidepoint(
                        mouse_pos
                    )
                ):

                    codex_ui.close_item()

            else:

                if codex_buttons[
                    "back"
                ].collidepoint(
                    mouse_pos
                ):

                    close_codex()

                else:

                    for (
                        item_id,
                        rect
                    ) in codex_buttons[
                        "items"
                    ].items():

                        if rect.collidepoint(
                            mouse_pos
                        ):

                            codex_ui.select_item(
                                item_id
                            )

                            break


        # ----------------------------------------------------
        # Game
        # ----------------------------------------------------

        elif ui_screen == UI_GAME:

            # =================================================
            # Interaction優先於所有底層遊戲點擊
            # =================================================

            if interaction_ui.is_open():

                handle_interaction_click(
                    interaction_buttons,
                    mouse_pos
                )


            # =================================================
            # Settings Button
            # =================================================

            elif (
                settings_button_rect
                is not None
                and settings_button_rect
                .collidepoint(
                    mouse_pos
                )
            ):

                ui_overlay = (
                    "settings"
                )


            # =================================================
            # Dialogue
            # =================================================

            elif game.game_state == DIALOGUE:

                result = (
                    dialogue_controller
                    .advance()
                )

                if (
                    result
                    == "dialogue_finished"
                ):

                    finish_dialogue_action()


            # =================================================
            # Choice
            # =================================================

            elif game.game_state == CHOICE:

                for (
                    option_rect,
                    option
                ) in choice_rects:

                    if (
                        option_rect
                        .collidepoint(
                            mouse_pos
                        )
                    ):

                        start_choice_result(
                            option
                        )

                        break


            # =================================================
            # Space
            # =================================================

            elif game.game_state == SPACE:

                object_clicked = False

                # ---------------------------------------------
                # Scene Object
                # ---------------------------------------------

                for (
                    object_id,
                    rect
                ) in object_rects.items():

                    if rect.collidepoint(
                        mouse_pos
                    ):

                        interaction_ui.open_object(
                            object_id
                        )

                        object_clicked = True

                        break


                # ---------------------------------------------
                # Hotbar
                # ---------------------------------------------

                if (
                    not object_clicked
                    and hotbar_data
                    is not None
                ):

                    slot_rects = (
                        hotbar_data[
                            "slots"
                        ]
                    )

                    visible_items = (
                        hotbar_data[
                            "visible_items"
                        ]
                    )

                    for (
                        index,
                        rect
                    ) in enumerate(
                        slot_rects
                    ):

                        if (
                            rect.collidepoint(
                                mouse_pos
                            )
                            and index
                            < len(
                                visible_items
                            )
                        ):

                            selected_slot = (
                                index
                            )

                            selected_item = (
                                visible_items[
                                    index
                                ]
                            )

                            open_hotbar_item(
                                selected_item
                            )

                            object_clicked = (
                                True
                            )

                            break


                    if not object_clicked:

                        arrow_left = (
                            hotbar_data[
                                "left"
                            ]
                        )

                        arrow_right = (
                            hotbar_data[
                                "right"
                            ]
                        )

                        visible_slots = (
                            ui_layout[
                                "hotbar"
                            ].get(
                                "visible_slots",
                                5
                            )
                        )

                        max_offset = max(
                            0,
                            len(
                                game.inventory
                            )
                            - visible_slots
                        )

                        if (
                            arrow_left
                            is not None
                            and arrow_left
                            .collidepoint(
                                mouse_pos
                            )
                        ):

                            hotbar_offset = max(
                                0,
                                hotbar_offset - 1
                            )

                            selected_slot = 0


                        elif (
                            arrow_right
                            is not None
                            and arrow_right
                            .collidepoint(
                                mouse_pos
                            )
                        ):

                            hotbar_offset = min(
                                max_offset,
                                hotbar_offset + 1
                            )

                            selected_slot = 0


            # =================================================
            # GAME OVER
            # =================================================

            elif game.game_state == GAME_OVER:

                if game_over_buttons[
                    "restart"
                ].collidepoint(
                    mouse_pos
                ):

                    start_new_game()


                elif game_over_buttons[
                    "menu"
                ].collidepoint(
                    mouse_pos
                ):

                    ui_screen = (
                        UI_MENU
                    )


                elif game_over_buttons[
                    "settings"
                ].collidepoint(
                    mouse_pos
                ):

                    ui_overlay = (
                        "settings"
                    )


            # =================================================
            # SUCCESS
            # =================================================

            elif game.game_state == SUCCESS:

                if ending_buttons[
                    "settings"
                ].collidepoint(
                    mouse_pos
                ):

                    ui_overlay = (
                        "settings"
                    )


                elif ending_buttons[
                    "menu"
                ].collidepoint(
                    mouse_pos
                ):

                    ui_screen = (
                        UI_MENU
                    )


    # ========================================================
    # Volume Slider Drag
    # ========================================================

    if (
        dragging_volume
        and ui_overlay == "settings"
        and settings_buttons
    ):

        slider_rect = (
            settings_buttons[
                "slider"
            ]
        )

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

        volume = int(
            relative_x
            / slider_rect.width
            * 100
        )


    pygame.display.flip()


# ============================================================
# Quit
# ============================================================

pygame.quit()

sys.exit()
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

from managers.game_manager import GameManager
from managers.map_manager import MapManager
from managers.story_manager import StoryManager

from player import Player #匯入角色移動模組

from controllers.interaction_controller import InteractionController
from controllers.hotbar_controller import HotbarController
from controllers.codex_controller import CodexController
from controllers.settings_controller import SettingsController

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


# ============================================================
# 初始化
# ============================================================

pygame.init()
pygame.key.stop_text_input()

DEBUG_COLLISION = True  # 顯示Polygon與家具碰撞供校正
POLYGON_EDITOR_ENABLED = True  # Enable mouse and keyboard polygon editing
polygon_editor_active = False  # 記錄目前是否正在繪製Polygon
polygon_editor_points = []  # 暫存本次繪製的Base座標頂點
polygon_editor_space = None  # 記錄目前正在編輯哪一個Space
polygon_editor_cursor = [400.0, 300.0]  # 保存鍵盤繪圖游標Base座標
POLYGON_CURSOR_SPEED = 180  # 設定鍵盤繪圖游標每秒移動速度
POLYGON_CURSOR_HOLD_MS = 1000
polygon_editor_key_started = {}
POLYGON_CURSOR_DIRECTIONS = {
    pygame.K_LEFT: (-1, 0),
    pygame.K_RIGHT: (1, 0),
    pygame.K_UP: (0, -1),
    pygame.K_DOWN: (0, 1)
}

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

# 集中管理Space版面、碰撞、互動範圍與出生點
map_manager = MapManager(
    ui_layout,
    game_ui
)

dialogue_controller = DialogueController(
    typing_speed=35
)

choice_controller = ChoiceController()

# 集中管理第一章劇情流程與Dialogue後續動作
story_manager = StoryManager(
    game,
    dialogue_controller,
    choice_controller,
    dialogues
)

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

interaction_controller = InteractionController(
    interaction_ui,
    story_manager,
    game
)

hotbar_controller = HotbarController(
    game,
    game_ui,
    interaction_ui,
    interaction_controller
)

# 集中管理Codex導覽與輸入
codex_controller = CodexController(
    codex_ui
)

# 集中管理音量、外觀與Settings輸入
settings_controller = SettingsController()

# ============================================================
# Player
# ============================================================

# 建立正式遊戲使用的玩家物件
player = Player(
    x=100,
    y=100,
    width=40,
    height=40,
    speed=300
)

# 儲存目前玩家持續按住的移動按鍵
pressed_keys = set()

# 記錄Player目前已套用出生點的空間
last_player_space = None

def draw_dashed_line(
    surface,
    color,
    start_pos,
    end_pos,
    width=2,
    dash_length=12,
    space_length=14
):
    """繪製滑鼠導航使用的虛線路徑。"""

    start = pygame.Vector2(
        start_pos
    )

    end = pygame.Vector2(
        end_pos
    )

    difference = end - start
    distance = difference.length()

    if distance == 0:
        return

    direction = difference.normalize()
    current_distance = 0.0

    while current_distance < distance:

        dash_start = (
            start
            + direction
            * current_distance
        )

        dash_end_distance = min(
            current_distance
            + dash_length,
            distance
        )

        dash_end = (
            start
            + direction
            * dash_end_distance
        )

        pygame.draw.line(
            surface,
            color,
            dash_start,
            dash_end,
            width
        )

        current_distance += (
            dash_length
            + space_length
        )


def draw_player_navigation_guide(
    surface
):
    """顯示滑鼠自動移動的虛線與終點標記。"""

    if player.mouse_target is None:
        return

    target_color = (
        255,
        215,
        0
    )

    player_center = (
        player.rect.center
    )

    target_center = (
        round(
            player.mouse_target.x
        ),
        round(
            player.mouse_target.y
        )
    )

    draw_dashed_line(
        surface,
        target_color,
        player_center,
        target_center,
        width=2,
        dash_length=12,
        space_length=14
    )

    # 使用空心圓標示角色真正導航終點
    pygame.draw.circle(
        surface,
        target_color,
        target_center,
        15,
        width=2
    )


def get_nearest_interaction_target(
    object_rects,
    interaction_rects
):
    """找出目前互動範圍內距離玩家最近的物件。"""

    nearest_target = None
    nearest_distance = None

    player_center = pygame.Vector2(
        player.rect.center
    )

    for object_id, interaction_rect in (
        interaction_rects.items()
    ):

        # 玩家未進入範圍時不能使用E互動
        if not player.rect.colliderect(
            interaction_rect
        ):
            continue

        object_rect = object_rects.get(
            object_id
        )

        if object_rect is None:
            continue

        object_center = pygame.Vector2(
            object_rect.center
        )

        distance = (
            object_center
            - player_center
        ).length_squared()

        if (
            nearest_distance is None
            or distance < nearest_distance
        ):

            nearest_distance = distance

            nearest_target = {
                "id": object_id,
                "rect": object_rect,
                "interaction_rect": (
                    interaction_rect
                )
            }

    return nearest_target


def draw_interaction_prompt(
    surface,
    target
):
    """在可互動物件旁顯示E鍵提示。"""

    if target is None:
        return

    object_id = target[
        "id"
    ]

    object_name = objects.get(
        object_id,
        {}
    ).get(
        "name",
        object_id
    )

    prompt_surface = (
        game_ui.font_small.render(
            f"[E] 互動：{object_name}",
            True,
            (255, 245, 180)
        )
    )

    prompt_x = (
        player.rect.centerx
        - prompt_surface.get_width()
        // 2
    )

    prompt_y = (
        player.rect.top
        - prompt_surface.get_height()
        - 10
    )

    prompt_x = max(
        8,
        min(
            prompt_x,
            surface.get_width()
            - prompt_surface.get_width()
            - 8
        )
    )

    prompt_y = max(
        8,
        prompt_y
    )

    surface.blit(
        prompt_surface,
        (
            prompt_x,
            prompt_y
        )
    )


# ============================================================
# Polygon Editor Debug Tools
# ============================================================


def screen_to_base(position):
    """將目前視窗座標換算成ui_layout使用的Base座標。"""

    base_width = ui_layout["base_resolution"]["width"]
    base_height = ui_layout["base_resolution"]["height"]

    return (
        round(position[0] * base_width / screen.get_width()),
        round(position[1] * base_height / screen.get_height())
    )


def base_to_screen(point):
    """將Base座標換算成目前視窗使用的座標。"""

    base_width = ui_layout["base_resolution"]["width"]
    base_height = ui_layout["base_resolution"]["height"]

    return (
        round(point[0] * screen.get_width() / base_width),
        round(point[1] * screen.get_height() / base_height)
    )


def draw_polygon_editor(surface, base_points, cursor_base, space_id):
    """繪製鍵盤操作的Polygon邊界編輯器。"""

    screen_points = [
        base_to_screen(point)
        for point in base_points
    ]

    cursor_screen = base_to_screen(
        cursor_base
    )

    if len(screen_points) >= 3:
        overlay = pygame.Surface(
            surface.get_size(),
            pygame.SRCALPHA
        )

        pygame.draw.polygon(
            overlay,
            (0, 200, 255, 45),
            screen_points
        )

        surface.blit(
            overlay,
            (0, 0)
        )

    if len(screen_points) >= 2:
        pygame.draw.lines(
            surface,
            (0, 230, 255),
            False,
            screen_points,
            width=3
        )

    if screen_points:
        pygame.draw.line(
            surface,
            (120, 245, 255),
            screen_points[-1],
            cursor_screen,
            width=2
        )

    if len(screen_points) >= 3:
        pygame.draw.line(
            surface,
            (0, 190, 230),
            screen_points[-1],
            screen_points[0],
            width=2
        )

    for index, (screen_point, base_point) in enumerate(
        zip(screen_points, base_points)
    ):
        pygame.draw.circle(
            surface,
            (0, 245, 255),
            screen_point,
            6
        )

        label = game_ui.font_small.render(
            f"{index}: ({base_point[0]}, {base_point[1]})",
            True,
            (220, 255, 255)
        )

        surface.blit(
            label,
            (screen_point[0] + 8, screen_point[1] - 18)
        )

    pygame.draw.circle(
        surface,
        (255, 230, 60),
        cursor_screen,
        8,
        width=2
    )

    pygame.draw.line(
        surface,
        (255, 230, 60),
        (cursor_screen[0] - 12, cursor_screen[1]),
        (cursor_screen[0] + 12, cursor_screen[1]),
        width=1
    )

    pygame.draw.line(
        surface,
        (255, 230, 60),
        (cursor_screen[0], cursor_screen[1] - 12),
        (cursor_screen[0], cursor_screen[1] + 12),
        width=1
    )

    cursor_x = round(cursor_base[0])
    cursor_y = round(cursor_base[1])

    info_lines = [
        f"Polygon Editor / Space {space_id}",
        f"Cursor: ({cursor_x}, {cursor_y})",
        f"Vertices: {len(base_points)}",
        "Mouse: move; Arrows: 1px, hold 2s to move",
        "Left click / Space: add; Right click / Backspace / Delete: undo",
        "R：清空   Enter：套用並輸出JSON",
        "F2 / Esc：離開編輯模式"
    ]

    panel_width = min(
        500,
        surface.get_width() - 20
    )

    panel_height = 24 + len(info_lines) * 21

    panel_rect = pygame.Rect(
        10,
        10,
        panel_width,
        panel_height
    )

    panel = pygame.Surface(
        panel_rect.size,
        pygame.SRCALPHA
    )

    panel.fill((10, 20, 28, 215))
    surface.blit(panel, panel_rect)

    y = panel_rect.y + 9

    for index, line in enumerate(info_lines):
        font = (
            game_ui.font_ui
            if index == 0
            else game_ui.font_small
        )

        color = (
            (120, 245, 255)
            if index == 0
            else (230, 240, 245)
        )

        text_surface = font.render(
            line,
            True,
            color
        )

        surface.blit(
            text_surface,
            (panel_rect.x + 10, y)
        )

        y += 25 if index == 0 else 21


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

# ============================================================
# Game Flow
# ============================================================

def start_new_game():
    """重設UI暫存狀態並交由StoryManager開始新遊戲。"""

    global ui_screen
    global ui_overlay

    global last_player_space

    interaction_ui.close()
    codex_ui.close_item()

    # 新遊戲開始時清除殘留移動按鍵
    pressed_keys.clear()

    # 下一次進入Space時重新套用出生位置
    last_player_space = None

    # 新遊戲不保留上一局的裂隙入口資料
    interaction_controller.pending_entry_rift = None

    hotbar_controller.reset()

    # 第一章劇情內容與流程交由StoryManager管理
    story_manager.start_new_game()

    ui_screen = UI_GAME
    ui_overlay = None


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

        story_manager.start_choice_result(
            selected_option
        )

# ============================================================
# Codex Navigation
# ============================================================

def open_codex(
    from_settings=False
):
    """進入Codex並記錄正確返回位置。"""

    global ui_screen
    global ui_overlay

    # 將返回來源交由CodexController保存
    codex_controller.open(
        ui_screen,
        from_settings
    )

    ui_screen = UI_CODEX
    ui_overlay = None


def close_codex():
    """離開Codex並返回原本畫面。"""

    global ui_screen
    global ui_overlay

    result = codex_controller.close()

    ui_screen = result[
        "ui_screen"
    ]

    if result[
        "open_settings"
    ]:
        ui_overlay = "settings"


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


# ============================================================
# Interaction Mouse
# ============================================================


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

    # 記錄本幀是否按下E鍵要求互動
    interact_pressed = False

    # 每一幀重新建立目前畫面Hitbox資料
    menu_buttons = {}

    settings_buttons = {}

    object_rects = {}

    collision_rects = {}

    interaction_rects = {}

    walkable_polygon = []

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

            # 視窗縮放後重新套用Space出生座標比例
            last_player_space = None

            # 縮放後取消舊的滑鼠目標座標
            player.cancel_mouse_movement()


        # ====================================================
        # Mouse
        # ====================================================

        elif (
            event.type == pygame.MOUSEMOTION
            and polygon_editor_active
            and event.rel != (0, 0)
        ):
            polygon_editor_cursor = list(screen_to_base(event.pos))

        elif (
            event.type
            == pygame.MOUSEBUTTONDOWN
            and event.button == 1
        ):

            # Polygon編輯中可用一般滑鼠點擊操作
            if polygon_editor_active:

                base_point = screen_to_base(event.pos)

                polygon_editor_cursor = [
                    base_point[0],
                    base_point[1]
                ]

                polygon_editor_points.append(
                    (
                        base_point[0],
                        base_point[1]
                    )
                )

                print(
                    "[Polygon Editor] "
                    f"新增頂點 "
                    f"{len(polygon_editor_points) - 1}: "
                    f"{polygon_editor_points[-1]}"
                )

            else:

                mouse_clicked = True

        elif (
            event.type
            == pygame.MOUSEBUTTONDOWN
            and event.button == 3
            and polygon_editor_active
        ):

            if polygon_editor_points:

                removed_point = (
                    polygon_editor_points.pop()
                )

                print(
                    "[Polygon Editor] "
                    f"撤銷頂點：{removed_point}"
                )

        elif (
            event.type
            == pygame.MOUSEBUTTONUP
            and event.button == 1
        ):

            settings_controller.stop_volume_drag()

            codex_controller.stop_dragging()


        # ====================================================
        # Mouse Wheel
        # ====================================================

        elif event.type == pygame.MOUSEWHEEL:

            if ui_screen == UI_CODEX:

                codex_controller.handle_wheel(
                    event,
                    mouse_pos
                )

            elif (
                ui_screen == UI_GAME
                and game.game_state == SPACE
                and ui_overlay is None
                and not interaction_ui.is_open()
            ):

                hotbar_controller.handle_wheel(
                    event
                )

        # ====================================================
        # Keyboard
        # ====================================================

        elif event.type == pygame.KEYDOWN:

            # Polygon編輯器優先攔截探索模式鍵盤事件
            if (
                POLYGON_EDITOR_ENABLED
                and ui_screen == UI_GAME
                and game.game_state == SPACE
                and ui_overlay is None
                and not interaction_ui.is_open()
            ):

                if event.key == pygame.K_F2:
                    polygon_editor_key_started.clear()
                    polygon_editor_active = not polygon_editor_active

                    if polygon_editor_active:
                        polygon_editor_space = game.current_space
                        polygon_editor_points = []

                        polygon_editor_cursor = [
                            ui_layout["base_resolution"]["width"] / 2,
                            ui_layout["base_resolution"]["height"] / 2
                        ]

                        pressed_keys.clear()
                        player.cancel_mouse_movement()

                        print(
                            "[Polygon Editor] "
                            f"開始編輯 Space {polygon_editor_space}"
                        )

                    else:
                        polygon_editor_points = []
                        polygon_editor_space = None
                        print("[Polygon Editor] 已離開")

                    continue

                if polygon_editor_active:

                    if event.key in POLYGON_CURSOR_DIRECTIONS:
                        if event.key not in polygon_editor_key_started:
                            polygon_editor_key_started[event.key] = pygame.time.get_ticks()
                            dx, dy = POLYGON_CURSOR_DIRECTIONS[event.key]
                            polygon_editor_cursor[0] = max(0, min(
                                polygon_editor_cursor[0] + dx,
                                ui_layout["base_resolution"]["width"]
                            ))
                            polygon_editor_cursor[1] = max(0, min(
                                polygon_editor_cursor[1] + dy,
                                ui_layout["base_resolution"]["height"]
                            ))

                    elif event.key == pygame.K_ESCAPE:
                        polygon_editor_active = False
                        polygon_editor_points = []
                        polygon_editor_space = None
                        print("[Polygon Editor] 已取消")

                    elif event.key == pygame.K_SPACE:
                        new_point = (
                            round(polygon_editor_cursor[0]),
                            round(polygon_editor_cursor[1])
                        )

                        polygon_editor_points.append(new_point)

                        print(
                            "[Polygon Editor] "
                            f"新增頂點 {len(polygon_editor_points) - 1}: "
                            f"{new_point}"
                        )

                    elif event.key in (
                        pygame.K_BACKSPACE,
                        pygame.K_DELETE
                    ):
                        if polygon_editor_points:
                            removed_point = polygon_editor_points.pop()

                            print(
                                "[Polygon Editor] "
                                f"撤銷頂點：{removed_point}"
                            )

                    elif event.key == pygame.K_r:
                        polygon_editor_points = []
                        print("[Polygon Editor] 已清空全部頂點")

                    elif event.key == pygame.K_RETURN:
                        if len(polygon_editor_points) < 3:
                            print("[Polygon Editor] 至少需要3個頂點。")

                        else:
                            polygon_data = [
                                [point[0], point[1]]
                                for point in polygon_editor_points
                            ]

                            ui_layout["spaces"][polygon_editor_space][
                                "walkable_polygon"
                            ] = polygon_data

                            print(
                                "\n[Polygon Editor] 請將以下內容貼入 "
                                f"Space {polygon_editor_space}:"
                            )

                            print(
                                '"walkable_polygon": '
                                + json.dumps(
                                    polygon_data,
                                    ensure_ascii=False,
                                    indent=4
                                )
                            )

                            print(
                                "[Polygon Editor] "
                                "已暫時套用至目前遊戲。\n"
                            )

                            polygon_editor_active = False
                            polygon_editor_points = []
                            polygon_editor_space = None

                    continue

            # 正常探索時才記錄WASD移動按鍵
            if (
                ui_screen == UI_GAME
                and game.game_state == SPACE
                and ui_overlay is None
                and not interaction_ui.is_open()
                and event.key in (
                    pygame.K_w,
                    pygame.K_a,
                    pygame.K_s,
                    pygame.K_d
                )
            ):

                pressed_keys.add(
                    event.key
                )

            # ------------------------------------------------
            # Settings優先
            # ------------------------------------------------

            if ui_overlay == "settings":

                result = (
                    settings_controller.handle_key(
                        event
                    )
                )

                if result == "close_settings":
                    ui_overlay = None

                continue


            # ------------------------------------------------
            # Codex
            # ------------------------------------------------

            if ui_screen == UI_CODEX:

                result = (
                    codex_controller.handle_key(
                        event
                    )
                )

                if result == "close_codex":
                    close_codex()

                continue


            # ------------------------------------------------
            # Interaction
            # ------------------------------------------------

            if (
                ui_screen == UI_GAME
                and interaction_ui.is_open()
            ):

                interaction_controller.handle_key(
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

                        story_manager.finish_dialogue_action()

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

                elif event.key == pygame.K_e:

                    # E鍵會在本幀Space資料建立後尋找最近物件
                    interact_pressed = True

                elif event.key in (
                    pygame.K_LEFT,
                    pygame.K_RIGHT,
                    pygame.K_1,
                    pygame.K_2,
                    pygame.K_3,
                    pygame.K_4,
                    pygame.K_5,
                    pygame.K_RETURN
                ):
                    hotbar_controller.handle_key(
                        event
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



        # ====================================================
        # Keyboard Release
        # ====================================================

        elif event.type == pygame.KEYUP:

            polygon_editor_key_started.pop(event.key, None)

            # WASD放開時移除玩家移動狀態
            if event.key in (
                pygame.K_w,
                pygame.K_a,
                pygame.K_s,
                pygame.K_d
            ):

                pressed_keys.discard(
                    event.key
                )


        # ====================================================
        # Window Focus
        # ====================================================

        elif event.type == pygame.WINDOWFOCUSLOST:

            polygon_editor_key_started.clear()

            # 視窗失焦時清除殘留的移動按鍵
            pressed_keys.clear()


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

    # 非正常探索狀態時清除殘留移動按鍵
    if not (
        ui_screen == UI_GAME
        and game.game_state == SPACE
        and ui_overlay is None
        and not interaction_ui.is_open()
    ):

        pressed_keys.clear()

        # 離開自由探索時取消滑鼠自動移動
        player.cancel_mouse_movement()


    # ========================================================
    # Polygon Editor Cursor
    # ========================================================

    if polygon_editor_active and pygame.key.get_focused():
        now = pygame.time.get_ticks()
        cursor_movement = pygame.Vector2(0, 0)

        for key, started in polygon_editor_key_started.items():
            # Only the portion of this frame after the two-second delay moves.
            move_dt = min(dt, max(0, now - started - POLYGON_CURSOR_HOLD_MS) / 1000)
            cursor_movement += pygame.Vector2(POLYGON_CURSOR_DIRECTIONS[key]) * move_dt

        # Preserve the existing diagonal speed limit.
        if cursor_movement.length() > dt:
            cursor_movement.scale_to_length(dt)

        polygon_editor_cursor[0] += cursor_movement.x * POLYGON_CURSOR_SPEED
        polygon_editor_cursor[1] += cursor_movement.y * POLYGON_CURSOR_SPEED

        base_width = ui_layout[
            "base_resolution"
        ]["width"]

        base_height = ui_layout[
            "base_resolution"
        ]["height"]

        polygon_editor_cursor[0] = max(
            0,
            min(polygon_editor_cursor[0], base_width)
        )

        polygon_editor_cursor[1] = max(
            0,
            min(polygon_editor_cursor[1], base_height)
        )

    else:
        polygon_editor_key_started.clear()

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
                    settings_controller.get_current_look()
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

            # 第一次進入新Space時套用該空間出生點
            if game.current_space != last_player_space:

                map_manager.place_player(
                    player,
                    game.current_space,
                    screen,
                    interaction_controller.pending_entry_rift
                )

                last_player_space = (
                    game.current_space
                )

                # 出生點套用完成後清除一次性入口資訊
                interaction_controller.pending_entry_rift = None

                pressed_keys.clear()

            # GameUI只負責繪製，目前不再提供物理資料
            game_ui.draw_space(
                screen,
                game,
                mouse_pos,
                settings_controller.get_current_look()
            )

            # MapManager集中建立探索模式需要的Rect資料
            space_data = (
                map_manager.build_space_runtime_data(
                    game.current_space,
                    screen
                )
            )

            object_rects = space_data[
                "object_rects"
            ]

            collision_rects = space_data[
                "collision_rects"
            ]

            interaction_rects = space_data[
                "interaction_rects"
            ]

            walkable_polygon = space_data[
                "walkable_polygon"
            ]

            obstacles = list(
                collision_rects.values()
            )

            # 只有正常探索狀態才能控制玩家移動
            if (
                ui_overlay is None
                and not interaction_ui.is_open()
                and not polygon_editor_active
            ):

                # E鍵只和目前範圍內最近的物件互動
                if interact_pressed:

                    nearest_target = (
                        get_nearest_interaction_target(
                            object_rects,
                            interaction_rects
                        )
                    )

                    if nearest_target is not None:

                        player.cancel_mouse_movement()

                        # 每次重新開啟Interaction都從預設控制項開始
                        interaction_controller.reset_interaction_focus()

                        interaction_ui.open_object(
                            nearest_target[
                                "id"
                            ]
                        )

                # Interaction尚未開啟時才更新角色移動
                if not interaction_ui.is_open():

                    player.update(
                        dt,
                        pressed_keys,
                        obstacles,
                        screen_width,
                        screen_height,
                        walkable_polygon
                    )

            # 其他介面開啟時立即停止持續移動
            else:

                pressed_keys.clear()

                # Overlay開啟時停止所有自動移動
                player.cancel_mouse_movement()

            # 滑鼠自動移動時顯示虛線與終點標記
            draw_player_navigation_guide(
                screen
            )

            if DEBUG_COLLISION:
                game_ui.draw_debug_collision(
                    screen,
                    walkable_polygon,
                    collision_rects
                )

            if (
                polygon_editor_active
                and polygon_editor_space == game.current_space
            ):
                draw_polygon_editor(
                    screen,
                    polygon_editor_points,
                    polygon_editor_cursor,
                    polygon_editor_space
                )

            # 繪製正式Player取代舊有Placeholder
            player.draw(
                screen,
                settings_controller.get_current_look()
            )

            # 找出目前E鍵會作用的最近互動物件
            nearby_target = (
                get_nearest_interaction_target(
                    object_rects,
                    interaction_rects
                )
            )

            if (
                ui_overlay is None
                and not interaction_ui.is_open()
            ):

                draw_interaction_prompt(
                    screen,
                    nearby_target
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
                    hotbar_controller.selected_slot,
                    hotbar_controller.offset,
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
                    settings_controller.get_current_look()
                )
            )

            hotbar_data = (
                game_ui.draw_hotbar(
                    screen,
                    game,
                    hotbar_controller.selected_slot,
                    hotbar_controller.offset,
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

            # 保存本幀控制項供下一幀鍵盤操作使用
            interaction_controller.last_buttons = dict(
                interaction_buttons
            )

            # 滑鼠hover同步所有Interaction鍵盤焦點
            interaction_controller.update_interaction_hover_focus(
                interaction_buttons,
                mouse_pos
            )

            # 顯示方向鍵與Enter目前作用的控制項
            interaction_controller.draw_focus(
                screen,
                interaction_buttons
            )

        else:
            interaction_controller.last_buttons = {}


    # ========================================================
    # Settings Overlay
    # ========================================================

    if ui_overlay == "settings":

        settings_buttons = (
            game_ui.draw_settings_overlay(
                screen,
                mouse_pos,
                settings_controller.volume,
                settings_controller.current_look_index,
                settings_controller.looks
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

            result = (
                settings_controller.handle_click(
                    settings_buttons,
                    mouse_pos
                )
            )

            if result == "resolution_800":

                screen_width = 800
                screen_height = 600

                screen = pygame.display.set_mode(
                    (
                        screen_width,
                        screen_height
                    ),
                    pygame.RESIZABLE
                )

                # 視窗縮放後重新套用出生座標比例
                last_player_space = None
                player.cancel_mouse_movement()

            elif result == "resolution_1024":

                screen_width = 1024
                screen_height = 768

                screen = pygame.display.set_mode(
                    (
                        screen_width,
                        screen_height
                    ),
                    pygame.RESIZABLE
                )

                # 視窗縮放後重新套用出生座標比例
                last_player_space = None
                player.cancel_mouse_movement()

            elif result == "open_codex":

                open_codex(
                    from_settings=True
                )

            elif result == "go_menu":

                interaction_ui.close()
                ui_screen = UI_MENU
                ui_overlay = None

            elif result == "close_settings":

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

            result = (
                codex_controller.handle_click(
                    codex_buttons,
                    mouse_pos
                )
            )

            if result == "close_codex":
                close_codex()


        # ----------------------------------------------------
        # Game
        # ----------------------------------------------------

        elif ui_screen == UI_GAME:

            # =================================================
            # Interaction優先於所有底層遊戲點擊
            # =================================================

            if interaction_ui.is_open():

                interaction_controller.handle_click(
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

                    story_manager.finish_dialogue_action()


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

                        story_manager.start_choice_result(
                            option
                        )

                        break


            # =================================================
            # Space
            # =================================================

            elif game.game_state == SPACE:

                click_is_walkable = (
                    len(walkable_polygon) >= 3
                    and player.point_in_polygon(mouse_pos, walkable_polygon)
                )
                click_handled = False

                # ---------------------------------------------
                # Scene Object
                # ---------------------------------------------

                for (
                    object_id,
                    rect
                ) in object_rects.items():

                    if click_is_walkable and rect.collidepoint(
                        mouse_pos
                    ):

                        target = {
                            "id": object_id,
                            "rect": rect,
                            "interaction_rect": (
                                interaction_rects.get(
                                    object_id,
                                    rect
                                )
                            )
                        }

                        # 點物件只負責靠近，不再自動開啟UI
                        player.set_interaction_target(
                            target
                        )

                        click_handled = True

                        break


                # ---------------------------------------------
                # Hotbar
                # ---------------------------------------------

                if (
                    not click_handled
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

                    # Hotbar區域本身優先攔截地面移動
                    for (
                        index,
                        rect
                    ) in enumerate(
                        slot_rects
                    ):

                        if rect.collidepoint(
                            mouse_pos
                        ):

                            click_handled = True

                            if hotbar_controller.select_slot(
                                index,
                                visible_items
                            ):
                                player.cancel_mouse_movement()

                            break


                    if not click_handled:

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

                        if (
                            arrow_left
                            is not None
                            and arrow_left
                            .collidepoint(
                                mouse_pos
                            )
                        ):

                            hotbar_controller.move_page_left()
                            click_handled = True

                            player.cancel_mouse_movement()


                        elif (
                            arrow_right
                            is not None
                            and arrow_right
                            .collidepoint(
                                mouse_pos
                            )
                        ):

                            hotbar_controller.move_page_right(visible_slots)
                            click_handled = True

                            player.cancel_mouse_movement()


                # ---------------------------------------------
                # Empty Ground
                # ---------------------------------------------

                if not click_handled and click_is_walkable:

                    # 點空地時設定一般滑鼠移動目標
                    player.set_mouse_target(
                        mouse_pos
                    )


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
        settings_controller.dragging_volume
        and ui_overlay == "settings"
        and settings_buttons
    ):

        settings_controller.update_volume(
            settings_buttons[
                "slider"
            ],
            mouse_pos
        )


    # 空間資訊最後繪製避免被場景遮擋
    if (
        ui_screen == UI_GAME
        and game.current_space is not None
        and game.game_state in (SPACE, PASSWORD, DIALOGUE)
    ):
        game_ui.draw_space_hud(screen, game)

    pygame.display.flip()


# ============================================================
# Quit
# ============================================================

pygame.quit()

sys.exit()

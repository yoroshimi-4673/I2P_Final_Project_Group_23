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
from managers.puzzle_manager import PuzzleManager
from controllers.puzzle_controller import PuzzleController
from managers.map_manager import MapManager
from managers.interaction_target_manager import InteractionTargetManager
from managers.pathfinding_manager import PathfindingManager
from managers.story_manager import StoryManager

from player import Player #匯入角色移動模組

from controllers.interaction_controller import InteractionController
from controllers.hotbar_controller import HotbarController
from controllers.navigation_controller import NavigationController
from controllers.polygon_editor_controller import PolygonEditorController
from ui.polygon_editor_ui import PolygonEditorUI
from controllers.codex_controller import CodexController
from controllers.settings_controller import SettingsController
from controllers.save_controller import SaveController
from controllers.developer_controller import DeveloperController
from ui.developer_ui import DeveloperUI
from ui.save_ui import SaveUI

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

DEBUG_COLLISION = False  # 正式遊玩預設隱藏碰撞校正圖層
POLYGON_EDITOR_ENABLED = False  # Enable mouse and keyboard polygon editing
DEVELOPER_MODE_ENABLED = False
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

puzzles = load_json(BASE_DIR / "data" / "puzzles.json")

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
puzzle_manager = PuzzleManager(game, puzzles, objects)
puzzle_controller = PuzzleController(puzzle_manager)  # 所有謎題共用單一輸入控制器

game_ui = GameUI(
    ui_layout,
    levels,
    objects
)

# 集中管理Space版面、碰撞、互動範圍與出生點
map_manager = MapManager(
    ui_layout,
    game_ui,
    game
)
polygon_editor_controller = PolygonEditorController(ui_layout)
polygon_editor_ui = PolygonEditorUI(game_ui.font_ui, game_ui.font_small)
pathfinding_manager = PathfindingManager(game_ui)
interaction_target_manager = InteractionTargetManager(ui_layout, game_ui, game)  # 提示與按鍵共用同一套目標選擇

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
    levels,
    puzzle_controller
)

codex_ui = CodexUI(
    game_ui,
    codex_data,
    objects
)

interaction_controller = InteractionController(
    interaction_ui,
    story_manager,
    game,
    puzzle_controller
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

# 集中管理音量與Settings輸入
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
    speed=300,
    sprite_path=BASE_DIR / "assets" / "素材庫" / "角色" / "main_character.png",
    visual_scale = 1.5
)
navigation_controller = NavigationController(
    pathfinding_manager, player, game, interaction_target_manager, interaction_controller
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

    remaining_points = player.path_points[player.path_index:]
    if not remaining_points:
        return

    target_color = (
        255,
        215,
        0
    )

    start = player.rect.center
    for point in remaining_points:
        draw_dashed_line(surface, target_color, start, point, width=2, dash_length=12, space_length=14)
        start = point

    # 使用空心圓標示角色真正導航終點
    pygame.draw.circle(
        surface,
        target_color,
        (round(start.x), round(start.y)),
        15,
        width=2
    )


def handle_hotbar_click(hotbar_data, mouse_pos):
    if hotbar_data is None:
        return False

    for index, rect in enumerate(hotbar_data["slots"]):
        if rect.collidepoint(mouse_pos):
            if hotbar_controller.select_slot(index, hotbar_data["visible_items"]):
                navigation_controller.cancel()
            return True  # 空格也攔截點擊避免觸發移動

    left = hotbar_data["left"]
    right = hotbar_data["right"]
    if left is not None and left.collidepoint(mouse_pos):
        moved = hotbar_controller.move_page_left()
    elif right is not None and right.collidepoint(mouse_pos):
        moved = hotbar_controller.move_page_right()
    else:
        return False

    if moved:
        navigation_controller.cancel()
    return True


def can_navigate_scene():
    return (
        ui_screen == UI_GAME
        and game.game_state == SPACE
        and ui_overlay is None
        and not interaction_ui.is_open()
        and not polygon_editor_controller.active
    )


def handle_exploration_click(
    position, surface, obstacles, walkable_polygon, object_rects, interaction_rects,
    hotbar_data, hide_player_this_frame,
):
    if hide_player_this_frame or not can_navigate_scene():
        return
    # 第二章道具欄可能蓋住房門，優先接收點擊
    hotbar_first = game.chapter >= 2 or not any(
        rect.collidepoint(position) for rect in object_rects.values()
    )
    if hotbar_first and handle_hotbar_click(hotbar_data, position):
        return
    navigation_controller.navigate_to_click(
        position, surface, obstacles, walkable_polygon, object_rects, interaction_rects
    )


def place_player_on_space_change(
    current_space, last_space, map_manager, player, screen, interaction_controller, pressed_keys
):
    """完成本幀的出生點配置，回傳是否應隱藏角色。"""
    if current_space is None or current_space == last_space:
        return False

    map_manager.place_player(
        player,
        current_space,
        screen,
        interaction_controller.pending_entry_rift,
        interaction_controller.pending_entry_object,
    )
    interaction_controller.pending_entry_rift = None  # 套用後清除一次性的裂隙入口
    interaction_controller.pending_entry_object = None  # 套用後清除一次性的房門入口
    pressed_keys.clear()  # 清除切換前殘留的方向鍵狀態
    return True


def draw_t7_power_outage_overlay(surface):
    if (
        game.current_space == "T7"
        and not game.has_event("t7_circuit_completed")
        and story_manager.pending_puzzle_id != "t7_circuit"
    ):
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 204))
        surface.blit(overlay, (0, 0))


def draw_dialogue_background(
    surface,
    mouse_pos,
    draw_player=True
):
    """依目前場景繪製背景，Dialogue Box再獨立疊上。"""

    dialogue_id = (
        dialogue_controller.dialogue_id
    )

    if dialogue_id == "scene_14":
        surface.fill((12, 22, 48))
        return

    # 第一章開場仍保留原本特殊背景
    if dialogue_id == "intro":

        game_ui.draw_intro_background(
            surface,
            dialogue_controller
        )

        return

    # 第一章各選項的結果對話使用純黑背景
    if dialogue_id == "scene_04_choice_result":

        surface.fill((0, 0, 0))

        return

    # 第一章結尾尚未正式切入第二章
    if dialogue_id == "chapter_1_end":

        surface.fill(
            (255, 255, 255)
        )

        return

    # 只要目前存在正式Space，就直接畫真正場景
    if game.current_space is not None:

        game_ui.draw_space(
            surface,
            game,
            mouse_pos
        )

        if draw_player:
            player.draw(surface)

        draw_t7_power_outage_overlay(surface)
        return

    # 沒有Space資料時才使用第一章307備援
    game_ui.draw_room_307(
        surface
    )


def draw_interaction_prompt(
    surface,
    target
):
    """依提示位置背景亮度自動產生高反差E鍵文字。"""

    if target is None:
        return

    object_id = target[
        "id"
    ]

    object_data = objects.get(object_id, {})
    object_name = object_data.get(
        "name",
        object_id
    )

    object_layout = (
        ui_layout
        .get(
            "spaces",
            {}
        )
        .get(
            game.current_space,
            {}
        )
        .get(
            "objects",
            {}
        )
        .get(
            object_id,
            {}
        )
    )

    # 第二章時間門直接顯示門名
    if game.current_space in ("T0", "T7", "T3") and object_data.get("type") == "time_exit":
        prompt_text = "[E]：離開房間"  # 房內出口使用獨立的離開提示

    elif game.current_space == "CH2_CORRIDOR" and object_data.get("type") == "time_door":

        prompt_text = (
            f"[E] {object_name}"
        )

    elif (interaction_label := object_layout.get("interaction_label")):
        prompt_text = f"[E] 互動：{interaction_label}"  # 版面可指定背景物件的互動名稱

    elif object_id in ("t0_height_marks", "t7_height_marks", "t3_height_marks"):
        prompt_text = "[E]互動: 門框"

    # 背景內建物件預設不顯示物件名稱
    elif (
        object_layout.get(
            "render_mode"
        )
        == "background"
    ):

        prompt_text = (
            "[E] 互動"
        )

    else:

        prompt_text = (
            f"[E] 互動：{object_name}"
        )

    # 先用暫時文字取得真正尺寸
    measurement_surface = (
        game_ui.font_small.render(
            prompt_text,
            True,
            (255, 255, 255)
        )
    )

    prompt_x = (
        player.rect.centerx
        - measurement_surface.get_width()
        // 2
    )

    prompt_y = (
        player.rect.top
        - measurement_surface.get_height()
        - 10
    )

    prompt_x = max(
        8,
        min(
            prompt_x,
            surface.get_width()
            - measurement_surface.get_width()
            - 8
        )
    )

    prompt_y = max(
        8,
        prompt_y
    )

    sample_rect = pygame.Rect(
        prompt_x - 5,
        prompt_y - 4,
        measurement_surface.get_width() + 10,
        measurement_surface.get_height() + 8
    )

    # 避免取樣範圍超出螢幕
    sample_rect = sample_rect.clip(surface.get_rect())
    if sample_rect.width <= 0 or sample_rect.height <= 0:
        return

    # 讀取提示文字後方的平均背景顏色
    average_color = (
        pygame.transform.average_color(
            surface.subsurface(
                sample_rect
            )
        )
    )

    red = average_color[0]
    green = average_color[1]
    blue = average_color[2]

    # 使用感知亮度，而不是單純RGB平均
    luminance = (
        0.2126 * red
        + 0.7152 * green
        + 0.0722 * blue
    )

    # 亮背景→黑字；暗背景→白字
    if luminance >= 145:

        text_color = (
            20,
            20,
            25
        )

        outline_color = (
            245,
            245,
            245
        )

        backing_color = (
            255,
            255,
            255,
            80
        )

    else:

        text_color = (
            245,
            245,
            245
        )

        outline_color = (
            15,
            15,
            20
        )

        backing_color = (
            0,
            0,
            0,
            90
        )

    # 加一層半透明底框，處理花紋複雜背景
    backing = pygame.Surface(
        sample_rect.size,
        pygame.SRCALPHA
    )

    backing.fill(
        backing_color
    )

    surface.blit(
        backing,
        sample_rect.topleft
    )

    # 先畫反色外框
    outline_surface = (
        game_ui.font_small.render(
            prompt_text,
            True,
            outline_color
        )
    )

    for offset_x, offset_y in (
        (-1, 0),
        (1, 0),
        (0, -1),
        (0, 1),
        (-1, -1),
        (1, -1),
        (-1, 1),
        (1, 1)
    ):

        surface.blit(
            outline_surface,
            (
                prompt_x + offset_x,
                prompt_y + offset_y
            )
        )

    # 最後畫真正文字
    prompt_surface = (
        game_ui.font_small.render(
            prompt_text,
            True,
            text_color
        )
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
save_controller = SaveController(
    game=game, player=player, hotbar_controller=hotbar_controller,
    dialogue_controller=dialogue_controller, story_manager=story_manager,
)
save_ui = SaveUI(game_ui)
developer_controller = DeveloperController(
    game, story_manager, interaction_controller, enabled=DEVELOPER_MODE_ENABLED
)
developer_ui = DeveloperUI(game_ui)
developer_buttons = {}
MENU_NAVIGATION_KEYS = {
    pygame.K_UP: "up", pygame.K_DOWN: "down",
    pygame.K_LEFT: "left", pygame.K_RIGHT: "right",
    pygame.K_RETURN: "enter", pygame.K_KP_ENTER: "enter",
    pygame.K_ESCAPE: "escape",
}
last_gameplay_frame = None

tutorial_guide_open = False  # 記錄是否開啟新手教學總覽視窗
tutorial_guide_buttons = {}

# ============================================================
# Game Flow
# ============================================================

def advance_current_dialogue():
    line = dialogue_controller.get_current_line() or {}  # 保留剛讀完的節點資料
    result = dialogue_controller.advance()
    if result == "dialogue_finished":
        finish_dialogue_and_open_ready_puzzle()
    elif result == "next_line" and line.get("item_notification"):
        interaction_controller.show_dialogue_item_notification(line["item_notification"])


def finish_dialogue_and_open_ready_puzzle():
    """對話結束後開啟已準備好的謎題介面。"""

    pending_puzzle_id = story_manager.pending_puzzle_id
    action = story_manager.finish_dialogue_action()
    if action == "complete_puzzle":
        interaction_controller.finish_puzzle_success_dialogue(pending_puzzle_id)
    if action in ("first_choice_a", "first_choice_b", "first_choice_c"):
        interaction_controller.pending_entry_rift = action  # 沿用一次性的入口出生配置
    if (
        action == "open_t7_circuit"
        and game.current_space == "T7"
        and game.game_state == SPACE
        and not game.has_event("t7_circuit_completed")
    ):
        interaction_controller.open_t7_circuit()
    if (
        game.game_state == SPACE
        and game.current_space == "CH2_CORRIDOR"
        and game.has_event("anchor_age_puzzle_ready")
        and not game.is_puzzle_solved("anchor_age_verification")
        and not game.has_event("anchor_age_ui_opened")
    ):
        result = interaction_controller.open_anchor_age_verification()
        if result.get("status") == "input_required":
            game.complete_event("anchor_age_ui_opened")
    interaction_controller.finish_interaction_sequence()  # 強制互動先於獎勵與事後反應


def reset_gameplay_ui():
    interaction_ui.close()
    interaction_controller.reset_puzzle_completion()
    interaction_controller.pending_post_interaction_dialogue = None
    interaction_controller.reset_interaction_focus()
    puzzle_controller.reset_anchor_drag_state()
    puzzle_controller.anchor_selected_fragment = None
    codex_ui.close_item()
    pressed_keys.clear()
    navigation_controller.cancel()
    interaction_controller.pending_entry_rift = None
    interaction_controller.pending_entry_object = None


def toggle_developer_menu():
    global ui_overlay, developer_buttons, tutorial_guide_open
    if not developer_controller.enabled:
        return
    if not developer_controller.toggle():
        ui_overlay = None
        return
    if ui_screen == UI_CODEX:
        codex_controller.stop_dragging()
        close_codex()
    if ui_overlay == "save":
        save_controller.close()
    tutorial_guide_open = False
    settings_controller.stop_volume_drag()
    polygon_editor_controller.close()
    pressed_keys.clear()
    navigation_controller.cancel()
    developer_buttons = {}
    ui_overlay = "developer"


def apply_developer_preset(preset_id):
    global ui_screen, ui_overlay, last_player_space, last_gameplay_frame
    if preset_id is None or not developer_controller.enabled:
        return
    reset_gameplay_ui()
    hotbar_controller.reset()
    if developer_controller.apply_preset(preset_id):
        last_player_space = None
        last_gameplay_frame = None
        ui_screen = UI_GAME
        ui_overlay = None


def start_new_game():
    """重設UI暫存狀態並交由StoryManager開始新遊戲。"""
    global ui_screen, ui_overlay, last_player_space, last_gameplay_frame
    reset_gameplay_ui()
    last_player_space = None
    last_gameplay_frame = None
    hotbar_controller.reset()
    story_manager.start_new_game()

    ui_screen = UI_GAME
    ui_overlay = None


def open_game_save(return_after_save=False):
    global ui_overlay
    save_controller.open_ingame(last_gameplay_frame, return_after_save)
    settings_controller.stop_volume_drag()
    ui_overlay = "save"


def get_4_3_window_size(width, height, previous_size=(800, 600)):
    """依變化較大的邊選擇四比三視窗尺寸。"""
    old_width, old_height = previous_size
    width_drives = abs(width - old_width) * 3 >= abs(height - old_height) * 4
    units = max(160, round(width / 4 if width_drives else height / 3))  # 保留最小視窗與整數比例
    return units * 4, units * 3


def scale_player_for_window(old_size, new_size):
    if old_size == new_size:
        return
    scale_x = new_size[0] / old_size[0]
    scale_y = new_size[1] / old_size[1]
    center_x, center_y = player.rect.center
    player.rect.size = (
        max(1, round(player.rect.width * scale_x)),
        max(1, round(player.rect.height * scale_y)),
    )
    player.rect.center = (round(center_x * scale_x), round(center_y * scale_y))
    player.position.update(player.rect.topleft)  # 保留角色在場景中的相對位置


def resize_game_window(width, height):
    global screen, screen_width, screen_height
    old_size = (screen_width, screen_height)
    size = get_4_3_window_size(width, height, old_size)
    if pygame.display.get_window_size() != size or screen.get_size() != size:
        screen = pygame.display.set_mode(size, pygame.RESIZABLE)  # 只修正尚未符合比例的視窗
    if game.current_space is not None and last_player_space == game.current_space:
        scale_player_for_window(old_size, size)
    screen_width, screen_height = size
    if old_size != size:
        navigation_controller.cancel()  # 清除縮放前的滑鼠導航座標


def restore_loaded_session(session):
    global screen, screen_width, screen_height
    global ui_screen, ui_overlay, last_player_space, last_gameplay_frame

    reset_gameplay_ui()
    story_manager.reset_story_state()
    size = session.get("screen_size")
    if size:
        saved_size = tuple(size)
        corrected_size = get_4_3_window_size(*saved_size)
        if session["has_player_position"]:
            scale_player_for_window(saved_size, corrected_size)  # 舊比例存檔保留相對位置
        if pygame.display.get_window_size() != corrected_size or screen.get_size() != corrected_size:
            screen = pygame.display.set_mode(corrected_size, pygame.RESIZABLE)
        screen_width, screen_height = corrected_size
    last_player_space = game.current_space if session["has_player_position"] else None
    last_gameplay_frame = None

    if game.game_state == DIALOGUE:
        dialogue = session.get("dialogue")
        if dialogue:
            dialogue_controller.start(dialogue["id"], dialogue["lines"])
            dialogue_controller.current_index = dialogue["index"]
            dialogue_controller.visible_characters = dialogue["visible_characters"]
            story_manager.dialogue_after_action = dialogue.get("after_action")
            story_manager.pending_target_space = dialogue.get("target_space")
        elif game.current_space is not None:
            game.game_state = SPACE
        else:
            story_manager.start_dialogue("intro", after_action="start_first_choice")
    elif game.game_state == CHOICE:
        story_manager.start_first_choice()

    ui_screen = UI_GAME
    ui_overlay = None


def handle_save_action(action):
    global ui_screen, ui_overlay, last_gameplay_frame
    destination = save_controller.execute_action(  # 存讀操作由控制器執行與回報
        action, screen_size=screen.get_size(),
        restore_loaded_session=restore_loaded_session, start_new_game=start_new_game,
    )
    if destination is None:
        return
    ui_overlay = "settings" if destination == "settings" else None
    if destination == "menu":
        reset_gameplay_ui()
        last_gameplay_frame = None
        ui_screen = UI_MENU


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

    click_pos = None

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

        if event.type == pygame.KEYDOWN and event.key == pygame.K_F8:
            if DEVELOPER_MODE_ENABLED:
                toggle_developer_menu()
                click_pos = None
                interact_pressed = False
            continue
        if developer_controller.is_open and event.type not in (pygame.QUIT, pygame.VIDEORESIZE):
            if event.type == pygame.KEYDOWN:
                apply_developer_preset(developer_controller.handle_navigation(MENU_NAVIGATION_KEYS.get(event.key)))
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for control, rect in developer_buttons.items():
                    if rect.collidepoint(event.pos):
                        apply_developer_preset(developer_controller.handle_click(control))
                        break
            if not developer_controller.is_open:
                ui_overlay = None
            continue

        if (
            event.type == pygame.MOUSEMOTION
            and ui_screen == UI_GAME
            and ui_overlay is None
            and interaction_ui.mode == "password"
            and puzzle_controller.current_puzzle_id == "chapter1_password"
        ):
            interaction_controller.update_interaction_hover_focus(
                interaction_controller.last_buttons, event.pos
            )

        if event.type == pygame.QUIT:

            running = False


        # ====================================================
        # Resize
        # ====================================================

        elif event.type == pygame.VIDEORESIZE:

            resize_game_window(event.w, event.h)  # 拖曳縮放與設定按鈕共用入口


        # ====================================================
        # Mouse
        # ====================================================

        # 日記拖放直接使用上幀的頁面與槽位
        elif (
            interaction_ui.mode in ("diary_drag", "anchor_fragments")
            and ui_overlay is None
            and ui_screen == UI_GAME
            and event.type in (
                pygame.MOUSEMOTION,
                pygame.MOUSEBUTTONDOWN,
                pygame.MOUSEBUTTONUP,
            )
        ):
            if interaction_ui.mode == "anchor_fragments":
                if event.type == pygame.MOUSEMOTION:
                    interaction_controller.update_anchor_drag(event.pos)

                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    interaction_controller.start_anchor_drag(
                        interaction_controller.last_buttons,
                        event.pos,
                    )

                elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    interaction_controller.finish_anchor_drag(
                        interaction_controller.last_buttons,
                        event.pos,
                    )

            else:
                if event.type == pygame.MOUSEMOTION:
                    interaction_controller.update_diary_drag(event.pos)

                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    interaction_controller.handle_click(
                        interaction_controller.last_buttons,
                        event.pos,
                    )

                elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    interaction_controller.update_diary_drag(event.pos)
                    interaction_controller.finish_diary_drag(
                        interaction_controller.last_buttons,
                        event.pos,
                    )

        elif (
            event.type == pygame.MOUSEMOTION
            and polygon_editor_controller.active
            and event.rel != (0, 0)
        ):
            polygon_editor_controller.handle_mouse_motion(
                event.pos,
                screen,
            )

        elif (
            event.type == pygame.MOUSEBUTTONDOWN
            and event.button == 1
            and ui_overlay is None
            and ui_screen == UI_GAME
            and interaction_ui.mode == "dial_password"
        ):
            interaction_controller.handle_click(
                interaction_ui.dial_password_controls(screen),
                event.pos,
            )

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if polygon_editor_controller.active:
                polygon_editor_controller.add_point_from_screen(
                    event.pos,
                    screen,
                )
            else:
                click_pos = event.pos

        elif (
            event.type == pygame.MOUSEBUTTONDOWN
            and event.button == 3
            and polygon_editor_controller.active
        ):
            polygon_editor_controller.undo_point()

        elif (
            event.type == pygame.MOUSEBUTTONUP
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
                    mouse_pos,
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

            if ui_overlay == "save":
                key = "reset" if event.key == pygame.K_r else MENU_NAVIGATION_KEYS.get(event.key)
                if key is not None:
                    handle_save_action(save_controller.handle_navigation(key))
                continue

            # Polygon編輯器優先攔截探索模式鍵盤事件
            if (
                POLYGON_EDITOR_ENABLED
                and ui_screen == UI_GAME
                and game.game_state == SPACE
                and ui_overlay is None
                and not interaction_ui.is_open()
            ):

                if event.key == pygame.K_F2:
                    if polygon_editor_controller.toggle(game.current_space):
                        pressed_keys.clear()
                        navigation_controller.cancel()
                    continue

                if polygon_editor_controller.active:
                    polygon_editor_controller.handle_keydown(event.key, pygame.time.get_ticks())
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
                navigation_controller.cancel()

            # ------------------------------------------------
            # Settings優先
            # ------------------------------------------------

            if ui_overlay == "settings":

                if tutorial_guide_open:
                    if event.key == pygame.K_ESCAPE:
                        tutorial_guide_open = False
                    continue

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

                    advance_current_dialogue()  # 鍵盤與滑鼠共用同一個前進流程

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

            polygon_editor_controller.handle_keyup(event.key)

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

            polygon_editor_controller.clear_held_keys()

            # 視窗失焦時清除殘留的移動按鍵
            pressed_keys.clear()
            navigation_controller.cancel()


    # ========================================================
    # Update
    # ========================================================

    if (
        ui_screen == UI_GAME
        and game.game_state
        == DIALOGUE
        and ui_overlay is None
        and interaction_ui.mode != "item_notification"
    ):

        dialogue_controller.update(
            dt
        )

    if ui_screen == UI_GAME and ui_overlay is None:
        interaction_controller.finish_interaction_sequence()

    # 非正常探索狀態時清除殘留移動按鍵
    if not can_navigate_scene():

        pressed_keys.clear()

        # 離開自由探索時取消滑鼠自動移動
        navigation_controller.cancel()


    # ========================================================
    # Polygon Editor Cursor
    # ========================================================

    polygon_editor_controller.update(dt, pygame.time.get_ticks(), pygame.key.get_focused())

    # ========================================================
    # Render Main Menu
    # ========================================================

    hide_player_this_frame = False  # 每幀預設允許顯示玩家角色
    if ui_screen == UI_GAME:
        hide_player_this_frame = place_player_on_space_change(
            game.current_space, last_player_space, map_manager, player,
            screen, interaction_controller, pressed_keys,
        )
        if hide_player_this_frame:
            navigation_controller.cancel()
            last_player_space = game.current_space  # 記錄已放置角色的目前空間

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

            # 場景背景與對話框分開依序繪製
            draw_dialogue_background(screen, mouse_pos, draw_player=not hide_player_this_frame)

            line = dialogue_controller.get_current_line() or {}  # 取得當前節點的對話框設定
            if (
                interaction_ui.mode != "item_notification"
                and (dialogue_controller.dialogue_id != "intro" or not line.get("hide_dialogue_box", False))
            ):
                draw_dialogue_box(  # 純畫面序章節點略過對話框繪製
                    screen,
                    dialogue_controller,
                    game_ui.font_ui,
                    game_ui.font_ui
                )

            if dialogue_controller.dialogue_id != "scene_14":
                settings_button_rect = game_ui.draw_settings_button(screen, mouse_pos)


        # ----------------------------------------------------
        # Choice
        # ----------------------------------------------------

        elif game.game_state == CHOICE:

            choice_data = story_manager.dialogues.get(choice_controller.choice_id, {})  # 讀取目前選擇場景的版面資料
            if not game_ui.draw_background_asset(screen, choice_data.get("background")):
                game_ui.draw_room_307(screen)  # 無背景素材時沿用病房畫面

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

            # GameUI只負責繪製，目前不再提供物理資料
            game_ui.draw_space(
                screen,
                game,
                mouse_pos
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
            if can_navigate_scene() and not hide_player_this_frame:

                # E鍵與畫面提示使用同一套互動判定
                if interact_pressed:

                    nearest_target = (
                        interaction_target_manager.get_interaction_target(
                            player, game.current_space, object_rects, interaction_rects, screen
                        )
                    )

                    if nearest_target is not None:

                        navigation_controller.cancel()

                        # 每次重新開啟Interaction都從預設控制項開始
                        interaction_controller.reset_interaction_focus()

                        interaction_controller.open_object(
                            nearest_target[
                                "id"
                            ]
                        )

                # 本幀有新點擊時先保留給點擊處理，避免觸發已被替換的目標
                if can_navigate_scene() and (
                    click_pos is None or navigation_controller.pending_interaction is None
                ):

                    navigation_controller.update_player(
                        dt,
                        pressed_keys,
                        obstacles,
                        walkable_polygon,
                        screen,
                        object_rects,
                        interaction_rects,
                    )
                    # 偵測玩家移動（鍵盤 WASD 或滑鼠點擊移動），完成階段 1 教學
                    keys = pygame.key.get_pressed()
                    is_moving = (
                        keys[pygame.K_w]
                        or keys[pygame.K_a]
                        or keys[pygame.K_s]
                        or keys[pygame.K_d]
                        or getattr(player, "mouse_target", None) is not None
                    )
                    if not game.has_event("tutorial_move_done") and is_moving:
                        game.complete_event("tutorial_move_done")
            # 其他介面開啟時立即停止持續移動
            else:

                pressed_keys.clear()

                # Overlay開啟時停止所有自動移動
                navigation_controller.cancel()

            # 滑鼠自動移動時顯示虛線與終點標記
            if not hide_player_this_frame:
                draw_player_navigation_guide(screen)

            if DEBUG_COLLISION:
                game_ui.draw_debug_collision(
                    screen,
                    walkable_polygon,
                    collision_rects
                )
                for rect in interaction_rects.values():
                    pygame.draw.rect(screen, (125, 190, 255), rect, width=1)  # 區分互動外框與實體碰撞範圍

            if (
                polygon_editor_controller.active
                and polygon_editor_controller.space_id == game.current_space
            ):
                polygon_editor_ui.draw(screen, polygon_editor_controller)

            if not hide_player_this_frame:
                player.draw(screen)
                if DEBUG_COLLISION:
                    pygame.draw.rect(screen, (0, 220, 255), player.get_collision_rect(), 2)  # 顯示實際與家具碰撞的腳部

            draw_t7_power_outage_overlay(screen)

            if not hide_player_this_frame and ui_overlay is None and not interaction_ui.is_open():
                nearby_target = interaction_target_manager.get_interaction_target(
                    player, game.current_space, object_rects, interaction_rects, screen
                )
                draw_interaction_prompt(screen, nearby_target)

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
                    mouse_pos
                )
            )

            if not hide_player_this_frame:
                player.draw(screen)  # 謎題開啟時保留角色所在位置

            draw_t7_power_outage_overlay(screen)
            if interaction_ui.mode not in ("circuit", "circuit_exit_confirmation"):
                hotbar_data = game_ui.draw_hotbar(
                    screen,
                    game,
                    hotbar_controller.selected_slot,
                    hotbar_controller.offset,
                    mouse_pos
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

            ending_buttons = game_ui.draw_success_end(screen, mouse_pos)


        # ====================================================
        # Interaction Overlay
        # ====================================================

        if (
            interaction_ui.is_open()
            and ui_overlay in (None, "developer")
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
            if ui_overlay is None:
                interaction_controller.update_interaction_hover_focus(
                    interaction_buttons,
                    mouse_pos,
                    mouse_moved=False
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

    if (
        ui_screen == UI_GAME
        and game.current_space is not None
        and game.game_state in (SPACE, PASSWORD, DIALOGUE)
        and interaction_ui.mode not in ("circuit", "circuit_exit_confirmation")
    ):
        game_ui.draw_space_hud(screen, game)

    if ui_screen == UI_GAME and (
        ui_overlay is None
        or (
            ui_overlay == "settings"
            and (last_gameplay_frame is None or last_gameplay_frame.get_size() != screen.get_size())
        )
    ):
        last_gameplay_frame = screen.copy()

    if ui_overlay == "save":
        save_buttons = save_ui.draw(screen, mouse_pos, save_controller)

    if ui_overlay == "settings":

        settings_buttons = (
            game_ui.draw_settings_overlay(
                screen,
                mouse_pos,
                settings_controller.volume,
                allow_save=ui_screen == UI_GAME,
            )
        )

        if tutorial_guide_open:
            tutorial_guide_buttons = (
                game_ui.draw_tutorial_guide_overlay(
                    screen,
                    mouse_pos
                )
            )


    # ========================================================
    # Mouse Click
    # ========================================================

    if click_pos is not None:
        mouse_pos = click_pos

        # ----------------------------------------------------
        # Settings Overlay
        # ----------------------------------------------------

        if ui_overlay == "save":
            for control, rect in save_buttons.items():
                if rect.collidepoint(mouse_pos):
                    handle_save_action(save_controller.handle_click(control))
                    break

        elif ui_overlay == "settings":

            if tutorial_guide_open:
                close_rect = tutorial_guide_buttons.get("close")
                if close_rect and close_rect.collidepoint(mouse_pos):
                    tutorial_guide_open = False
                continue

            if (
                settings_buttons.get("tutorial")
                and settings_buttons["tutorial"].collidepoint(mouse_pos)
            ):
                tutorial_guide_open = True
                continue

            result = (
                settings_controller.handle_click(
                    settings_buttons,
                    mouse_pos
                )
            )

            if result == "resolution_800":

                resize_game_window(800, 600)  # 套用四比三標準預設解析度

            elif result == "resolution_1024":

                resize_game_window(1024, 768)  # 套用四比三較大預設解析度

            elif result == "open_codex":

                open_codex(
                    from_settings=True
                )

            elif result == "go_menu":

                if ui_screen == UI_GAME:
                    open_game_save(return_after_save=True)
                else:
                    ui_overlay = None

            elif result == "open_save":

                open_game_save()

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

                save_controller.open_start()
                ui_overlay = "save"


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

                advance_current_dialogue()  # 完成一句台詞後檢查道具提示


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
                handle_exploration_click(
                    mouse_pos, screen, obstacles, walkable_polygon, object_rects, interaction_rects,
                    hotbar_data, hide_player_this_frame,
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

                    open_game_save(return_after_save=True)


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

                    open_game_save(return_after_save=True)


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


    if developer_controller.is_open:
        developer_buttons = developer_ui.draw(screen, mouse_pos, developer_controller, game, DEBUG_COLLISION)

    pygame.display.flip()


# ============================================================
# Quit
# ============================================================

pygame.quit()

sys.exit()

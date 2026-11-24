"""Save, load, and play-time management."""

import json
import math
import time
from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile

from game_states import CHOICE, DIALOGUE, GAME_OVER, PASSWORD, SPACE, SUCCESS


BASE_DIR = Path(__file__).resolve().parent  # 取得save_manager.py所在的專案根目錄
SAVE_DIR = BASE_DIR / "data" / "saves"
LEGACY_SAVE_PATH = BASE_DIR / "data" / "save.json"
VALID_SAVE_SLOTS = (1, 2, 3)


def get_save_path(slot):
    if type(slot) is not int or slot not in VALID_SAVE_SLOTS:
        raise ValueError("Save slot must be 1, 2, or 3")
    return SAVE_DIR / f"slot_{slot}.json"


def get_thumbnail_path(slot):
    return get_save_path(slot).with_suffix(".png")


def _slot_source(slot):
    path = get_save_path(slot)
    return LEGACY_SAVE_PATH if slot == 1 and not path.exists() else path


def _read_slot(path):
    with path.open(encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, dict) or not data.keys() & {"game_state", "current_scene", "solved_puzzles"}:
        raise ValueError("Invalid save data")
    for key in ("inventory", "discovered_items", "knowledge", "unlocked_objects",
                "inspected_objects", "solved_puzzles", "story_events"):
        if key in data and not isinstance(data[key], list):
            raise ValueError(f"Invalid save field: {key}")
    for key in ("puzzle_attempts", "scene13_anchor_slots", "player", "hotbar", "session", "save_metadata"):
        if key in data and not isinstance(data[key], dict):
            raise ValueError(f"Invalid save field: {key}")
    if "game_state" in data and data["game_state"] not in (SPACE, PASSWORD, DIALOGUE, CHOICE, GAME_OVER, SUCCESS):
        raise ValueError("Invalid saved game state")
    for key in ("current_scene", "current_space"):
        if data.get(key) is not None and not isinstance(data[key], str):
            raise ValueError(f"Invalid save field: {key}")
    if type(data.get("chapter", 0)) is not int:
        raise ValueError("Invalid chapter")
    if any(type(value) is not int for value in data.get("puzzle_attempts", {}).values()):
        raise ValueError("Invalid puzzle attempts")
    for key in ("x", "y", "width", "height"):
        value = data.get("player", {}).get(key)
        if value is not None and (type(value) is not int or not -(2**31) <= value < 2**31):
            raise ValueError("Invalid player rectangle")
    if any(type(data.get("hotbar", {}).get(key, 0)) is not int for key in ("selected_slot", "offset")):
        raise ValueError("Invalid hotbar state")
    for value in (data.get("play_time", 0), data.get("save_metadata", {}).get("play_time", 0)):
        if type(value) not in (int, float) or not 0 <= value <= 2**53 or not math.isfinite(value):
            raise ValueError("Invalid play time")
    session = data.get("session", {})
    size = session.get("screen_size")
    if size is not None and (
        not isinstance(size, list) or len(size) != 2
        or any(type(value) is not int or not 1 <= value <= 16384 for value in size)
    ):
        raise ValueError("Invalid saved screen size")
    dialogue = session.get("dialogue")
    if dialogue is not None and (
        not isinstance(dialogue, dict)
        or not isinstance(dialogue.get("id"), str)
        or not isinstance(dialogue.get("lines"), list)
        or not dialogue["lines"]
        or any(not isinstance(line, dict) for line in dialogue["lines"])
        or type(dialogue.get("index")) is not int
        or not 0 <= dialogue["index"] < len(dialogue["lines"])
        or type(dialogue.get("visible_characters")) is not int
    ):
        raise ValueError("Invalid saved dialogue")
    return data


def _metadata(data, slot, saved_at, thumbnail=None):
    space = data.get("current_space")
    data_dir = BASE_DIR.parent / "data"
    try:
        levels = json.loads((data_dir / "levels.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        levels = {}
    space_name = levels.get(space, {}).get("name")
    if space and not space_name:
        try:
            layout = json.loads((data_dir / "ui_layout.json").read_text(encoding="utf-8"))
            space_name = layout["spaces"].get(space, {}).get("background", {}).get("label")
        except (OSError, ValueError):
            pass
    chapter = data.get("chapter", 0)
    return {
        "slot": slot,
        "saved_at": saved_at,
        "chapter": chapter,
        "chapter_name": "Chapter 2" if chapter >= 2 else "Chapter 1",
        "space": space,
        "space_name": space_name or space or data.get("current_scene") or "未知區域",
        "play_time": data.get("play_time", 0),
        "thumbnail": thumbnail,
    }


def get_save_slot_info(slot):
    path = _slot_source(slot)
    info = {"slot": slot, "exists": False, "status": "NO DATA",
            "metadata": None, "thumbnail_path": None}
    try:
        data = _read_slot(path)
        metadata = data.get("save_metadata")
        if metadata is None:
            saved_at = datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds")
            metadata = _metadata(data, slot, saved_at)
    except FileNotFoundError:
        return info
    except (OSError, ValueError, TypeError):
        return {**info, "status": "CORRUPTED"}

    thumbnail = get_thumbnail_path(slot)
    return {**info, "exists": True, "status": "DATA", "metadata": metadata,
            "thumbnail_path": thumbnail if metadata.get("thumbnail") == thumbnail.name and thumbnail.is_file() else None}


def _write_slot(path, data, screenshot_surface):
    SAVE_DIR.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(dir=SAVE_DIR, suffix=".json.tmp", delete=False) as file:
        staged_json = Path(file.name)
    staged_png = None
    thumbnail_path = path.with_suffix(".png")
    previous_thumbnail = None
    try:
        staged_json.write_text(json.dumps(data, ensure_ascii=False, indent=4), encoding="utf-8")
        if screenshot_surface is not None:
            import pygame

            width, height = screenshot_surface.get_size()
            ratio = min(320 / width, 240 / height, 1)
            thumbnail = pygame.transform.smoothscale(
                screenshot_surface, (max(1, round(width * ratio)), max(1, round(height * ratio)))
            )
            with NamedTemporaryFile(dir=SAVE_DIR, suffix=".png", delete=False) as file:
                staged_png = Path(file.name)
            pygame.image.save(thumbnail, staged_png)
            try:
                previous_thumbnail = thumbnail_path.read_bytes()
            except FileNotFoundError:
                pass
            staged_png.replace(thumbnail_path)
        try:
            staged_json.replace(path)
        except OSError:
            if screenshot_surface is not None:
                if previous_thumbnail is None:
                    thumbnail_path.unlink(missing_ok=True)
                else:
                    staged_png.write_bytes(previous_thumbnail)
                    staged_png.replace(thumbnail_path)
            raise
    finally:
        staged_json.unlink(missing_ok=True)
        if staged_png is not None:
            staged_png.unlink(missing_ok=True)


LEGACY_PUZZLE_ID_MAP = {
    "password_panel": (
        "chapter1_password"
    )
}


def migrate_legacy_puzzle_state(
    save_data
):
    """將舊版Puzzle物件編號轉成新的Puzzle編號。"""

    solved_puzzles = list(
        save_data.get(
            "solved_puzzles",
            []
        )
    )

    migrated_solved = []

    for puzzle_id in solved_puzzles:

        new_id = (
            LEGACY_PUZZLE_ID_MAP.get(
                puzzle_id,
                puzzle_id
            )
        )

        if new_id not in migrated_solved:

            migrated_solved.append(
                new_id
            )

    puzzle_attempts = dict(
        save_data.get(
            "puzzle_attempts",
            {}
        )
    )

    migrated_attempts = {}

    for puzzle_id, remaining in (
        puzzle_attempts.items()
    ):

        new_id = (
            LEGACY_PUZZLE_ID_MAP.get(
                puzzle_id,
                puzzle_id
            )
        )

        if new_id in migrated_attempts:

            migrated_attempts[
                new_id
            ] = min(
                migrated_attempts[
                    new_id
                ],
                remaining
            )

        else:

            migrated_attempts[
                new_id
            ] = remaining

    save_data[
        "solved_puzzles"
    ] = migrated_solved

    save_data[
        "puzzle_attempts"
    ] = migrated_attempts

    return save_data


def save_game(
    game,
    slot,
    player=None,
    hotbar_controller=None,
    screenshot_surface=None,
    *,
    session=None,
):  # 將目前所有重要遊戲狀態寫入JSON存檔
    path = get_save_path(slot)
    save_data = {
    "game_state": game.game_state,
    "current_scene": game.current_scene,
    "current_space": game.current_space,

    "inventory": game.inventory,
    "discovered_items": game.discovered_items,
    "knowledge": game.knowledge,

    "unlocked_objects": game.unlocked_objects,
    "inspected_objects": game.inspected_objects,
    "solved_puzzles": game.solved_puzzles,

    "story_events": game.story_events,

    "puzzle_attempts": game.puzzle_attempts,
    "scene13_anchor_slots": game.scene13_anchor_slots,  # 保存已固定於時間凹槽的碎片

    "chapter": game.chapter,
    "game_over_reason": game.game_over_reason,

    "play_time": game.get_play_time(),

    "player": {
        "x": player.rect.x if player else None,
        "y": player.rect.y if player else None,
        "width": player.rect.width if player else None,
        "height": player.rect.height if player else None
    },

    "hotbar": {
        "selected_slot": (
            hotbar_controller.selected_slot
            if hotbar_controller
            else 0
        ),
        "offset": (
            hotbar_controller.offset
            if hotbar_controller
            else 0
        )
    }
}
    if session is not None:
        save_data["session"] = session
    thumbnail = get_thumbnail_path(slot).name if screenshot_surface is not None else None
    save_data["save_metadata"] = _metadata(
        save_data, slot, datetime.now().isoformat(timespec="seconds"), thumbnail
    )
    _write_slot(path, save_data, screenshot_surface)


def load_game(
    game,
    slot,
    player=None,
    hotbar_controller=None,
    *,
    restored_session=None,
):  # 從存檔讀取資料並恢復GameManager狀態
    path = _slot_source(slot)
    try:
        save_data = migrate_legacy_puzzle_state(_read_slot(path))

    except (OSError, ValueError, TypeError):  # 沒有存檔或JSON損壞時視為無有效存檔
        return False

    game.game_state = save_data.get(
        "game_state",
        game.game_state
    )

    game.current_scene = save_data.get(
        "current_scene",
        "intro"
    )  # 恢復目前進行到的劇情場景

    game.current_space = save_data.get(
        "current_space",
        None
    )

    # 謎題介面暫存不存檔，讀取後回探索重新開啟
    if game.game_state == PASSWORD and game.current_space is not None:
        game.game_state = SPACE

    game.inventory = save_data.get(
        "inventory",
        []
    )

    game.discovered_items = save_data.get(
        "discovered_items",
        game.inventory.copy()
    )  # 舊存檔沒有此欄時直接由背包補建圖鑑

    game.knowledge = save_data.get(
        "knowledge",
        []
    )  # 舊存檔沒有knowledge時自動使用空清單

    game.unlocked_objects = save_data.get(
        "unlocked_objects",
        []
    )

    game.inspected_objects = save_data.get(
        "inspected_objects",
        []
    )

    game.solved_puzzles = save_data.get(
        "solved_puzzles",
        []
    )

    game.puzzle_attempts = save_data.get(
        "puzzle_attempts",
        {}
    )  # 恢復各個謎題自己的剩餘嘗試次數

    loaded_anchor_slots = save_data.get("scene13_anchor_slots", {})  # 舊存檔缺少此欄位仍可正常載入
    game.scene13_anchor_slots.clear()
    game.scene13_anchor_slots.update({"past": None, "present": None, "future": None})
    game.scene13_anchor_slots.update(loaded_anchor_slots)  # 保留原字典參照供控制器使用

    game.story_events = save_data.get(
        "story_events",
        []
    )  # 恢復已經發生的重要劇情事件紀錄

    # 舊存檔可能只有解謎紀錄，出口門現在也需要完成事件。
    if game.is_puzzle_solved("chapter1_password"):
        game.complete_event("chapter1_password_solved")

    game.chapter = save_data.get(
        "chapter",
        0
    )

    game.game_over_reason = save_data.get(
        "game_over_reason",
        None
    )

    game.play_time = save_data.get(
        "play_time",
        0
    )

    player_data = save_data.get(
        "player",
        {}
    )

    if player is not None:

        player_x = player_data.get("x")
        player_y = player_data.get("y")

        player_width = player_data.get(
            "width"
        )

        player_height = player_data.get(
            "height"
        )

        if (
            player_width is not None
            and player_height is not None
        ):
            # 恢復存檔時的角色碰撞尺寸
            player.rect.size = (
                player_width,
                player_height
            )

        if (
            player_x is not None
            and player_y is not None
        ):
            # 恢復角色當時所在的位置
            player.rect.topleft = (
                player_x,
                player_y
            )

            # 同步角色移動使用的浮點座標
            player.position.update(
                player_x,
                player_y
            )

        player.cancel_mouse_movement()

    hotbar_data = save_data.get(
        "hotbar",
        {}
    )

    if hotbar_controller is not None:

        hotbar_controller.selected_slot = (
            hotbar_data.get(
                "selected_slot",
                0
            )
        )

        hotbar_controller.offset = (
            hotbar_data.get(
                "offset",
                0
            )
        )

        # selected_item可由目前格子重新取得
        hotbar_controller.selected_item = None

    game.session_start = time.time()  # 重新開始計算本次啟動後新增的遊玩時間

    if restored_session is not None:
        restored_session.update(save_data.get("session", {}))
        restored_session["has_player_position"] = all(
            player_data.get(key) is not None for key in ("x", "y")
        )

    return True


def delete_save(slot):
    get_save_path(slot).unlink(missing_ok=True)
    get_thumbnail_path(slot).unlink(missing_ok=True)


def reset_save(slot):
    path = get_save_path(slot)
    get_thumbnail_path(slot).unlink(missing_ok=True)
    if slot == 1:
        LEGACY_SAVE_PATH.unlink(missing_ok=True)
    path.unlink(missing_ok=True)

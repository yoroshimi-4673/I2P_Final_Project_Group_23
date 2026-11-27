"""Save, load, and play-time management."""

import json
import time
from pathlib import Path  # 匯入Path建立穩定可靠的存檔路徑
from game_states import PASSWORD, SPACE


BASE_DIR = Path(__file__).resolve().parent  # 取得save_manager.py所在的專案根目錄
SAVE_PATH = BASE_DIR / "data" / "save.json"  # 建立固定的存檔檔案位置


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
    player = None,
    hotbar_controller = None
):  # 將目前所有重要遊戲狀態寫入JSON存檔
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
    with open(SAVE_PATH, "w", encoding="utf-8") as file:  # 以寫入模式開啟目前玩家存檔
        json.dump(
            save_data,
            file,
            ensure_ascii=False,
            indent=4
        )  # 將完整遊戲狀態格式化寫入JSON


def load_game(
    game,
    player = None,
    hotbar_controller = None
):  # 從存檔讀取資料並恢復GameManager狀態
    try:
        with open(SAVE_PATH, "r", encoding="utf-8") as file:  # 嘗試開啟目前存在的玩家存檔
            save_data = json.load(file)

    except (FileNotFoundError, json.JSONDecodeError):  # 沒有存檔或JSON損壞時視為無有效存檔
        return False

    save_data = migrate_legacy_puzzle_state(save_data)  # 寫入遊戲狀態之前統一遷移舊編號

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

    return True


def delete_save():  # 刪除目前存檔以建立全新的遊戲進度
    if SAVE_PATH.exists():
        SAVE_PATH.unlink()

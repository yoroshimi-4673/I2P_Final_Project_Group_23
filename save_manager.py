"""Save, load, autosave, and play-time management."""

import json
import time
from pathlib import Path  # 匯入Path建立穩定可靠的存檔路徑


BASE_DIR = Path(__file__).resolve().parent  # 取得save_manager.py所在的專案根目錄
SAVE_PATH = BASE_DIR / "data" / "save.json"  # 建立固定的存檔檔案位置


def save_game(game):  # 將目前所有重要遊戲狀態寫入JSON存檔
    save_data = {
        "game_state": game.game_state,
        "current_scene": game.current_scene,
        "current_space": game.current_space,

        "inventory": game.inventory,
        "unlocked_objects": game.unlocked_objects,
        "inspected_objects": game.inspected_objects,
        "solved_puzzles": game.solved_puzzles,

        "puzzle_attempts": game.puzzle_attempts,

        "chapter": game.chapter,
        "game_over_reason": game.game_over_reason,

        "play_time": game.get_play_time()
    }

    with open(SAVE_PATH, "w", encoding="utf-8") as file:  # 以寫入模式開啟目前玩家存檔
        json.dump(
            save_data,
            file,
            ensure_ascii=False,
            indent=4
        )  # 將完整遊戲狀態格式化寫入JSON


def load_game(game):  # 從存檔讀取資料並恢復GameManager狀態
    try:
        with open(SAVE_PATH, "r", encoding="utf-8") as file:  # 嘗試開啟目前存在的玩家存檔
            save_data = json.load(file)

    except (FileNotFoundError, json.JSONDecodeError):  # 沒有存檔或JSON損壞時視為無有效存檔
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

    game.inventory = save_data.get(
        "inventory",
        []
    )

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

    game.session_start = time.time()  # 重新開始計算本次啟動後新增的遊玩時間

    return True


def delete_save():  # 刪除目前存檔以建立全新的遊戲進度
    if SAVE_PATH.exists():
        SAVE_PATH.unlink()
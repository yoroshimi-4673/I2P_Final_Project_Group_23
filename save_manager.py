"""Save, load, autosave, and play-time management."""

import json
import time
from pathlib import Path  # 匯入Path建立可靠的存檔檔案路徑

BASE_DIR = Path(__file__).resolve().parent  # 可以簡單理解為取得save_manager.py所在的專案根目錄
SAVE_PATH = BASE_DIR / "data" / "save.json"  # 建立不受工作目錄影響的存檔路徑

def save_game(game):  # 將目前遊戲狀態整理後寫入存檔檔案
    save_data = {
        "game_state": game.game_state,
        "current_space": game.current_space,
        "inventory": game.inventory,
        "password_attempts": game.password_attempts,
        "play_time": game.get_play_time(),  # 儲存玩家目前累積的總遊玩時間
        "unlocked_objects": game.unlocked_objects  # 儲存目前已經解鎖的特殊物件
    }

    with open(SAVE_PATH, "w", encoding="utf-8") as file:  # 以寫入模式開啟存檔JSON檔案
        json.dump(save_data, file, ensure_ascii=False, indent=4)  # 將遊戲資料格式化寫入JSON檔案


def load_game(game):  # 從存檔檔案讀取資料並恢復遊戲狀態
    try:
        with open(SAVE_PATH, "r", encoding="utf-8") as file:  # 嘗試開啟目前玩家的存檔檔案
            save_data = json.load(file)  # 將JSON資料讀回Python字典格式

    except (FileNotFoundError, json.JSONDecodeError):  # 存檔不存在或格式錯誤時避免程式中斷
        return False

    game.game_state = save_data.get("game_state", game.game_state)  # 恢復先前保存的遊戲流程狀態
    game.current_space = save_data.get("current_space", None)  # 恢復玩家上次所在的遊戲空間
    game.inventory = save_data.get("inventory", [])  # 恢復玩家先前取得的所有道具
    game.password_attempts = save_data.get("password_attempts", 3)  # 恢復玩家剩餘的密碼嘗試次數
    game.play_time = save_data.get("play_time", 0)  # 恢復玩家之前累積的遊玩時間
    game.session_start = time.time()  # 重新記錄這次遊戲啟動的開始時間
    game.unlocked_objects = save_data.get("unlocked_objects", [])  # 恢復已解鎖特殊物件清單

    return True
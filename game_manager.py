import time
from game_states import DIALOGUE, SPACE, SUCCESS, GAME_OVER

class GameManager:
    def __init__(self):
        self.game_state = DIALOGUE
        self.current_space = None

        self.inventory = []  # 使用清單統一記錄玩家目前取得的道具

        self.password_attempts = 3
        self.correct_password = "100101"

        self.play_time = 0  # 記錄玩家先前已累積的總遊玩秒數
        self.session_start = time.time()  # 記錄本次啟動遊戲時的開始時間

        self.unlocked_objects = []  # 記錄已經完成特殊解鎖條件的空間

    def enter_space(self, space_name):
        self.current_space = space_name
        self.game_state = SPACE

    def add_item(self, item_name):  # 新增道具到玩家背包並避免重複取得
        if item_name not in self.inventory:
            self.inventory.append(item_name)
            return True

        return False

    def has_item(self, item_name):  # 檢查玩家目前是否已經擁有指定道具
        return item_name in self.inventory

    def check_password(self, password):
        if password == self.correct_password:
            self.game_state = SUCCESS
            return True

        self.password_attempts -= 1

        if self.password_attempts <= 0:
            self.game_state = GAME_OVER

        return False

    def get_play_time(self):
        current_session = time.time() - self.session_start
        return self.play_time + current_session

    def get_formatted_play_time(self):  # 計算存檔時間加上本次遊戲執行的時間
        total_seconds = int(self.get_play_time())  # 去除小數部分並取得完整遊玩秒數

        hours = total_seconds // 3600  # 計算完整的小時數量
        minutes = (total_seconds % 3600) // 60  # 計算扣除小時後的分鐘數
        seconds = total_seconds % 60  # 計算最後剩餘的秒數

        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"  # 固定以兩位數格式輸出時間

    def unlock_object(self, object_id):  # 將指定物件加入目前已解鎖清單
        if object_id not in self.unlocked_objects:
            self.unlocked_objects.append(object_id)

    def is_object_unlocked(self, object_id):  # 檢查指定物件目前是否已完成解鎖
        return object_id in self.unlocked_objects
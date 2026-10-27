from game_states import DIALOGUE, SPACE, SUCCESS, GAME_OVER

class GameManager:
    def __init__(self):
        self.game_state = DIALOGUE
        self.current_space = None

        self.inventory = []  # 使用清單統一記錄玩家目前取得的道具

        self.password_attempts = 3
        self.correct_password = "100101"

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
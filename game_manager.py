import time

from game_states import DIALOGUE, SPACE, GAME_OVER


class GameManager:
    def __init__(self):
        self.game_state = DIALOGUE  # 記錄目前所處的主要遊戲狀態
        self.current_scene = "intro"  # 記錄目前正在進行的劇情階段
        self.current_space = None  # 記錄玩家目前所在的探索空間

        self.inventory = []  # 記錄玩家目前已經取得的所有道具

        self.unlocked_objects = []  # 保留給未來章節，記錄已解鎖場景物件
        self.inspected_objects = []  # 保留給未來章節，記錄已調查場景物件

        self.solved_puzzles = []  # 記錄玩家目前已經完成的所有謎題
        self.puzzle_attempts = {}  # 分別記錄每一個謎題剩餘的嘗試次數

        self.story_events = []  # 記錄目前已經發生的重要劇情事件

        self.chapter = 0  # 記錄玩家目前完成到哪一個遊戲章節
        self.game_over_reason = None  # 記錄玩家進入失敗狀態的具體原因

        self.play_time = 0
        self.session_start = time.time()


    # ======== 空間管理 ======== #

    def enter_space(self, space_name):  # 將玩家目前所在位置切換到指定空間
        self.current_space = space_name
        self.game_state = SPACE


    # ======== Inventory ======== #

    def add_item(self, item_id):  # 將指定道具加入背包並避免重複取得
        if item_id not in self.inventory:
            self.inventory.append(item_id)
            return True

        return False

    def has_item(self, item_id):  # 檢查玩家目前是否已經擁有指定道具
        return item_id in self.inventory


    # ======== Object Unlock ======== #

    def unlock_object(self, object_id):  # 將指定場景物件記錄為已經完成解鎖
        if object_id not in self.unlocked_objects:
            self.unlocked_objects.append(object_id)

    def is_object_unlocked(self, object_id):  # 檢查指定場景物件是否已經被解鎖
        return object_id in self.unlocked_objects


    # ======== Inspectable Object ======== #

    def inspect_object(self, object_id):  # 將指定場景物件標記成已經調查完成
        if object_id not in self.inspected_objects:
            self.inspected_objects.append(object_id)

    def is_object_inspected(self, object_id):  # 檢查指定場景物件是否曾被調查
        return object_id in self.inspected_objects


    # ======== Puzzle ======== #

    def solve_puzzle(self, puzzle_id):  # 將指定謎題記錄成目前已經成功完成
        if puzzle_id not in self.solved_puzzles:
            self.solved_puzzles.append(puzzle_id)

    def is_puzzle_solved(self, puzzle_id):  # 檢查指定謎題目前是否已經解開
        return puzzle_id in self.solved_puzzles

    def check_password(
        self,
        puzzle_id,
        password,
        correct_password,
        max_attempts=3
    ):  # 檢查謎題答案並管理該謎題自己的嘗試次數

        if puzzle_id not in self.puzzle_attempts:
            self.puzzle_attempts[puzzle_id] = max_attempts  # 第一次互動時建立此謎題剩餘次數

        if password == correct_password:
            return True

        self.puzzle_attempts[puzzle_id] -= 1  # 答錯時只扣除目前這個謎題的次數

        if self.puzzle_attempts[puzzle_id] <= 0:
            self.game_state = GAME_OVER
            self.game_over_reason = "space_c_locked"  # 記錄C空間因密碼失敗永久封鎖

        return False

    def get_puzzle_attempts(
        self,
        puzzle_id,
        max_attempts=3
    ):  # 取得指定謎題目前剩餘的可嘗試次數

        return self.puzzle_attempts.get(
            puzzle_id,
            max_attempts
        )


    # ======== Story Event ======== #

    def complete_event(self, event_id):  # 將指定重要劇情事件記錄為已經發生
        if event_id not in self.story_events:
            self.story_events.append(event_id)

    def has_event(self, event_id):  # 檢查指定重要劇情事件是否已經發生
        return event_id in self.story_events


    # ======== Chapter ======== #

    def complete_chapter(self, chapter_number):  # 更新玩家目前已經完成的最高章節
        self.chapter = chapter_number


    # ======== Play Time ======== #

    def get_play_time(self):  # 計算目前這次執行期間累積的遊戲時間
        current_session = time.time() - self.session_start
        return self.play_time + current_session

    def get_formatted_play_time(self):  # 將累積秒數轉換成時分秒顯示格式
        total_seconds = int(self.get_play_time())

        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60

        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


    # ======== New Game ======== #

    def reset_game(self):  # 將所有遊戲狀態重新恢復成全新遊戲
        self.game_state = DIALOGUE
        self.current_scene = "intro"
        self.current_space = None

        self.inventory = []

        self.unlocked_objects = []
        self.inspected_objects = []

        self.solved_puzzles = []
        self.puzzle_attempts = {}

        self.story_events = []

        self.chapter = 0
        self.game_over_reason = None

        self.play_time = 0
        self.session_start = time.time()
from game_states import PASSWORD, SPACE


class PuzzleController:
    """管理目前Puzzle的輸入與暫時UI狀態。"""

    def __init__(
        self,
        puzzle_manager
    ):
        self.puzzle_manager = (
            puzzle_manager
        )

        self.current_puzzle_id = None

        self.input_text = ""

        self.last_result = None


    @property
    def puzzle(self):
        """取得目前正在操作的Puzzle資料。"""

        return (
            self.puzzle_manager
            .get_puzzle(
                self.current_puzzle_id
            )
            or {}
        )


    @property
    def ui_mode(self):
        """取得目前Puzzle指定的UI模式。"""

        return self.puzzle.get(
            "ui_mode",
            "password"
        )


    @property
    def remaining_attempts(self):
        """取得目前Puzzle剩餘嘗試次數。"""

        return (
            self.puzzle_manager
            .get_remaining_attempts(
                self.current_puzzle_id
            )
        )


    def open_puzzle(
        self,
        puzzle_id
    ):
        """開啟指定Puzzle並建立暫時輸入狀態。"""

        self.close_puzzle()

        self.current_puzzle_id = (
            puzzle_id
        )

        puzzle = self.puzzle

        if not puzzle:

            result = {
                "status": "puzzle_not_found",
                "message": "找不到這個謎題。"
            }

        elif self.puzzle_manager.is_solved(
            puzzle_id
        ):

            result = {
                "status": "puzzle_solved",
                "message": "這個謎題已經完成。"
            }

        elif not self.puzzle_manager.can_attempt(
            puzzle_id
        ):

            result = {
                "status": "puzzle_unavailable",
                "message": "目前無法操作此謎題。",
                "remaining_attempts": (
                    self.remaining_attempts
                )
            }

        else:

            # PASSWORD目前實際扮演通用Puzzle Overlay State，
            # 未來出現非密碼UI後可以再重新命名。
            self.puzzle_manager.game.game_state = (
                PASSWORD
            )

            result = {
                "status": "input_required",
                "remaining_attempts": (
                    self.remaining_attempts
                )
            }

        self.last_result = result

        return result


    def close_puzzle(self):
        """關閉Puzzle並清除暫時輸入資料。"""

        game = self.puzzle_manager.game

        if (
            self.current_puzzle_id
            is not None
            and game.game_state == PASSWORD
            and game.current_space is not None
        ):

            game.game_state = SPACE

        self.current_puzzle_id = None

        self.input_text = ""

        self.last_result = None


    def append_input(
        self,
        value
    ):
        """依Puzzle規則加入玩家輸入內容。"""

        if self.current_puzzle_id is None:
            return

        if not self.puzzle_manager.can_attempt(
            self.current_puzzle_id
        ):
            return

        value = str(
            value
        )

        input_type = self.puzzle.get(
            "input_type",
            "text"
        )

        if (
            input_type == "digits"
            and not value.isdigit()
        ):
            return

        new_text = (
            self.input_text
            + value
        )

        maximum_length = self.puzzle.get(
            "length"
        )

        if maximum_length is not None:

            new_text = new_text[
                :maximum_length
            ]

        self.input_text = new_text


    def remove_input(self):
        """刪除目前輸入內容最後一個字元。"""

        self.input_text = (
            self.input_text[:-1]
        )


    def clear_input(self):
        """清除目前Puzzle的全部輸入。"""

        self.input_text = ""


    def submit(self):
        """提交目前Puzzle輸入內容。"""

        if self.current_puzzle_id is None:

            return {
                "status": "no_puzzle",
                "message": "目前沒有正在操作的謎題。"
            }

        self.last_result = (
            self.puzzle_manager
            .submit_answer(
                self.current_puzzle_id,
                self.input_text
            )
        )

        self.clear_input()

        return self.last_result

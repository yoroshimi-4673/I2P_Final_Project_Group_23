from game_states import GAME_OVER
from managers.interaction_manager import collect_item


class PuzzleManager:
    """管理通用謎題規則，永久進度交由GameManager保存。"""

    def __init__(
        self,
        game,
        puzzles,
        objects
    ):
        self.game = game
        self.puzzles = puzzles
        self.objects = objects

        self.reward_handlers = {
            "item": self._reward_item
        }  # 將不同獎勵類型集中由同一入口處理


    # ========================================================
    # Puzzle Data
    # ========================================================

    def get_puzzle(
        self,
        puzzle_id
    ):
        """取得指定謎題的完整設定資料。"""

        if puzzle_id is None:
            return None

        return self.puzzles.get(
            puzzle_id
        )


    def is_solved(
        self,
        puzzle_id
    ):
        """確認指定謎題是否已經永久完成。"""

        if puzzle_id is None:
            return False

        return self.game.is_puzzle_solved(
            puzzle_id
        )


    # ========================================================
    # Attempts
    # ========================================================

    def get_remaining_attempts(
        self,
        puzzle_id
    ):
        """取得剩餘次數，None代表此謎題不限次數。"""

        puzzle = self.get_puzzle(
            puzzle_id
        )

        if puzzle is None:
            return None

        if puzzle_id in self.game.puzzle_attempts:

            return self.game.puzzle_attempts[
                puzzle_id
            ]

        return puzzle.get(
            "max_attempts"
        )


    # ========================================================
    # Requirements
    # ========================================================

    def can_attempt(
        self,
        puzzle_id
    ):
        """確認目前遊戲狀態是否允許操作指定謎題。"""

        puzzle = self.get_puzzle(
            puzzle_id
        )

        if puzzle is None:
            return False

        if self.is_solved(
            puzzle_id
        ):
            return False

        if self.game.game_state == GAME_OVER:
            return False

        remaining = (
            self.get_remaining_attempts(
                puzzle_id
            )
        )

        if (
            remaining is not None
            and remaining <= 0
        ):
            return False

        requirements = puzzle.get(
            "requirements",
            {}
        )

        for item_id in requirements.get(
            "items",
            []
        ):

            if not self.game.has_item(
                item_id
            ):
                return False

        for flag in requirements.get(
            "flags",
            []
        ):

            if not self.game.has_event(
                flag
            ):
                return False

        for required_puzzle in requirements.get(
            "puzzles",
            []
        ):

            if not self.is_solved(
                required_puzzle
            ):
                return False

        return True


    # ========================================================
    # Input Validation
    # ========================================================

    def validate_input(
        self,
        puzzle_id,
        answer
    ):
        """依照Puzzle設定驗證玩家輸入格式。"""

        puzzle = self.get_puzzle(
            puzzle_id
        )

        if puzzle is None:

            return {
                "status": "puzzle_not_found",
                "message": "找不到這個謎題。"
            }

        answer = str(
            answer
        )

        required_length = puzzle.get(
            "length"
        )

        if (
            required_length is not None
            and len(answer) != required_length
        ):

            return {
                "status": "incomplete_input",
                "message": (
                    f"請輸入完整"
                    f"{required_length}位內容。"
                )
            }

        input_type = puzzle.get(
            "input_type",
            "text"
        )

        if (
            input_type == "digits"
            and not answer.isdigit()
        ):

            return {
                "status": "invalid_input",
                "message": "輸入內容只能包含數字。"
            }

        return {
            "status": "valid"
        }


    def check_answer(
        self,
        puzzle_id,
        answer
    ):
        """只判斷答案是否正確，不修改遊戲狀態。"""

        puzzle = self.get_puzzle(
            puzzle_id
        )

        if puzzle is None:
            return False

        return (
            str(answer)
            == str(
                puzzle.get(
                    "answer",
                    ""
                )
            )
        )


    # ========================================================
    # Rewards
    # ========================================================

    def _reward_item(
        self,
        value
    ):
        """發放Puzzle所指定的一般道具獎勵。"""

        if value not in self.objects:

            raise ValueError(
                f"找不到獎勵道具：{value}"
            )

        return collect_item(
            self.game,
            value,
            self.objects
        )


    def apply_rewards(
        self,
        puzzle
    ):
        """依Puzzle資料套用所有設定的獎勵。"""

        results = []

        for reward in puzzle.get(
            "rewards",
            []
        ):

            reward_type = reward.get(
                "type"
            )

            value = reward.get(
                "value"
            )

            handler = self.reward_handlers.get(
                reward_type
            )

            if handler is None:

                raise ValueError(
                    "尚未支援的Puzzle獎勵類型："
                    f"{reward_type}"
                )

            reward_result = handler(
                value
            )

            results.append(
                {
                    **reward,
                    "result": reward_result
                }
            )

        return results


    # ========================================================
    # Success / Failure
    # ========================================================

    def apply_success(
        self,
        puzzle_id
    ):
        """完成Puzzle並套用永久狀態與獎勵。"""

        if self.is_solved(
            puzzle_id
        ):

            return {
                "status": "puzzle_solved",
                "message": "這個謎題已經完成。"
            }

        puzzle = self.get_puzzle(
            puzzle_id
        )

        if puzzle is None:

            return {
                "status": "puzzle_not_found",
                "message": "找不到這個謎題。"
            }

        # 先保存完成狀態防止獎勵被重複領取
        self.game.solve_puzzle(
            puzzle_id
        )

        solved_flag = puzzle.get(
            "solved_flag"
        )

        if solved_flag is not None:

            self.game.complete_event(
                solved_flag
            )

        rewards = self.apply_rewards(
            puzzle
        )

        return {
            "status": "correct",
            "message": puzzle.get(
                "success_message",
                "解答正確。"
            ),
            "puzzle_id": puzzle_id,
            "rewards": rewards,
            "on_complete": puzzle.get(
                "on_complete"
            )
        }


    def apply_failure(
        self,
        puzzle_id
    ):
        """處理答案錯誤並更新剩餘嘗試次數。"""

        puzzle = self.get_puzzle(
            puzzle_id
        )

        remaining = (
            self.get_remaining_attempts(
                puzzle_id
            )
        )

        # None表示這個Puzzle可以無限次嘗試
        if remaining is not None:

            remaining = max(
                0,
                remaining - 1
            )

            self.game.puzzle_attempts[
                puzzle_id
            ] = remaining

        failure = puzzle.get(
            "failure",
            {}
        )

        if (
            remaining == 0
            and failure.get("type")
            == "game_over"
        ):

            self.game.game_state = (
                GAME_OVER
            )

            self.game.game_over_reason = (
                failure.get(
                    "reason"
                )
            )

            return {
                "status": "game_over",
                "message": failure.get(
                    "message",
                    "錯誤次數已達上限。"
                ),
                "remaining_attempts": 0
            }

        if remaining is None:

            message = puzzle.get(
                "wrong_message",
                "答案錯誤。"
            )

        else:

            message = puzzle.get(
                "wrong_message",
                (
                    "答案錯誤。"
                    f"剩餘嘗試次數：{remaining}"
                )
            )

        return {
            "status": "wrong",
            "message": message,
            "remaining_attempts": remaining
        }


    # ========================================================
    # Submit
    # ========================================================

    def submit_answer(
        self,
        puzzle_id,
        answer
    ):
        """執行一次完整Puzzle提交流程。"""

        puzzle = self.get_puzzle(
            puzzle_id
        )

        if puzzle is None:

            return {
                "status": "puzzle_not_found",
                "message": "找不到這個謎題。"
            }

        if self.is_solved(
            puzzle_id
        ):

            return {
                "status": "puzzle_solved",
                "message": "這個謎題已經完成。"
            }

        if not self.can_attempt(
            puzzle_id
        ):

            return {
                "status": "puzzle_unavailable",
                "message": "目前無法操作此謎題。",
                "remaining_attempts": (
                    self.get_remaining_attempts(
                        puzzle_id
                    )
                )
            }

        validation = self.validate_input(
            puzzle_id,
            answer
        )

        if validation[
            "status"
        ] != "valid":

            validation[
                "remaining_attempts"
            ] = (
                self.get_remaining_attempts(
                    puzzle_id
                )
            )

            return validation

        if self.check_answer(
            puzzle_id,
            answer
        ):

            return self.apply_success(
                puzzle_id
            )

        return self.apply_failure(
            puzzle_id
        )

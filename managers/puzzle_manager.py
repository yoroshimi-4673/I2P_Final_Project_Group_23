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
            "item": self._reward_item,
            "consume_items": self._reward_consume_items
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

        for knowledge_id in requirements.get(
            "knowledge",
            []
        ):

            if not self.game.has_knowledge(
                knowledge_id
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

        # 依介面模式保留排序與多欄格式
        ui_mode = puzzle.get("ui_mode", "password")

        if ui_mode in ("sequence", "diary_drag"):

            if not isinstance(
                answer,
                list
            ):

                return {
                    "status": "invalid_input",
                    "message": "頁面排列資料格式錯誤。"
                }

            expected_length = len(
                puzzle.get(
                    "answer",
                    []
                )
            )

            if len(answer) != expected_length:

                return {
                    "status": "incomplete_input",
                    "message": "還有日記頁尚未放回。"
                }

            return {
                "status": "valid"
            }

        if ui_mode == "multi_input":

            if not isinstance(
                answer,
                dict
            ):

                return {
                    "status": "invalid_input",
                    "message": "輸入資料格式錯誤。"
                }

            fields = puzzle.get(
                "fields",
                []
            )

            for field in fields:

                field_id = field.get(
                    "id"
                )

                value = str(
                    answer.get(
                        field_id,
                        ""
                    )
                )

                if value == "":

                    return {
                        "status": "incomplete_input",
                        "message": "請填寫三個時間的年齡。"
                    }

                if (
                    puzzle.get(
                        "input_type"
                    ) == "digits"
                    and not value.isdigit()
                ):

                    return {
                        "status": "invalid_input",
                        "message": "年齡只能輸入數字。"
                    }

            return {
                "status": "valid"
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
        """依Puzzle UI模式比較玩家答案。"""

        puzzle = self.get_puzzle(
            puzzle_id
        )

        if puzzle is None:
            return False

        ui_mode = puzzle.get(
            "ui_mode",
            "password"
        )

        expected = puzzle.get(
            "answer"
        )

        if ui_mode in ("sequence", "diary_drag"):

            return isinstance(answer, list) and answer == expected

        if ui_mode == "multi_input":

            if not isinstance(
                answer,
                dict
            ):
                return False

            return all(
                str(answer.get(field_id, ""))
                == str(expected_value)
                for field_id, expected_value
                in expected.items()
            )

        return (
            str(answer)
            == str(expected)
        )


    def get_failure_stage(
        self,
        puzzle_id
    ):
        """依剩餘嘗試次數推導Puzzle視覺失敗階段。"""

        if puzzle_id != "anchor_age_verification":
            return None

        remaining = self.get_remaining_attempts(
            puzzle_id
        )

        stages = {
            3: "far",
            2: "middle",
            1: "near",
            0: "consumed"
        }

        return stages.get(
            remaining,
            "far"
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
                reward if reward_type == "consume_items" else value
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
            "reward_notification_order": puzzle.get("reward_notification_order", "after_completion"),
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

            if puzzle_id == "anchor_age_verification":
                self.game.game_over_reason = failure.get("reason")
                return {
                    "status": "final_failure_pending",
                    "message": failure.get("message", "白牆吞沒了整條走廊。"),
                    "remaining_attempts": 0
                }  # 最終白牆先顯示並等待玩家確認

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

        base_message = puzzle.get(
            "wrong_message",
            "答案錯誤。"
        )

        if remaining is None:

            message = base_message

        elif remaining == 1:

            message = (
                f"{base_message}\n"
                "剩餘嘗試次數：1。最後一次。"
            )

        else:

            message = (
                f"{base_message}\n"
                f"剩餘嘗試次數：{remaining}"
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
        answer,
        *,
        defer_success=False
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
                "message": "目前無法操作此謎題。是不是還缺少了什麼情報呢？",
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
            if defer_success:
                return {"status": "success_dialogue", "puzzle_id": puzzle_id}

            return self.apply_success(
                puzzle_id
            )

        return self.apply_failure(
            puzzle_id
        )


    def _reward_consume_items(
        self,
        reward
    ):
        """移除完成Puzzle後被合併使用的背包物品。"""

        item_ids = reward.get(
            "values",
            []
        )

        for item_id in item_ids:

            self.game.remove_item(
                item_id
            )

        return {
            "type": "consume_items",
            "values": item_ids
        }

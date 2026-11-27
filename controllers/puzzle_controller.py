from game_states import PASSWORD, SPACE


ANCHOR_FRAGMENT_TARGETS = {
    "past_fragment": "past",
    "present_fragment": "present",
    "future_fragment": "future"
}


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

        self.sequence_input = []  # 記錄排序類謎題目前選擇順序
        self.multi_input = {}  # 記錄多欄輸入謎題各欄內容
        self.active_field_id = None  # 記錄目前正在輸入的欄位
        self.reset_anchor_slots()

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

        # elif not self.puzzle_manager.can_attempt(
        #     puzzle_id
        # ):

        #     result = {
        #         "status": "puzzle_unavailable",
        #         "message": "目前無法操作此謎題。",
        #         "remaining_attempts": (
        #             self.remaining_attempts
        #         )
        #     }

        else:

            # PASSWORD目前實際扮演通用Puzzle Overlay State，
            # 未來出現非密碼UI後可以再重新命名。
            self.puzzle_manager.game.game_state = (
                PASSWORD
            )

            if self.ui_mode == "multi_input":
                fields = puzzle.get("fields", [])
                self.multi_input = {
                    field["id"]: ""
                    for field in fields
                }
                if fields:
                    self.active_field_id = fields[0]["id"]

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

        self.sequence_input = []
        self.multi_input = {}
        self.active_field_id = None

        self.last_result = None


    def append_input(
        self,
        value
    ):
        """依Puzzle規則加入玩家輸入內容。"""

        if self.ui_mode == "multi_input":
            self.append_multi_input(value)
            return

        if self.ui_mode != "password":
            return

        if self.current_puzzle_id is None:
            return

        # if not self.puzzle_manager.can_attempt(
        #     self.current_puzzle_id
        # ):
        #     return

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

        if self.ui_mode == "multi_input":
            self.remove_multi_input()
            return

        if self.ui_mode != "password":
            return

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

        if self.ui_mode == "sequence":

            answer = list(
                self.sequence_input
            )

        elif self.ui_mode == "multi_input":

            answer = dict(
                self.multi_input
            )

        else:

            answer = self.input_text

        self.last_result = (
            self.puzzle_manager
            .submit_answer(
                self.current_puzzle_id,
                answer
            )
        )

        if self.ui_mode == "sequence":

            if self.last_result.get(
                "status"
            ) != "correct":

                self.clear_sequence()

        elif self.ui_mode == "password":

            self.clear_input()

        return self.last_result


    def append_sequence_item(
        self,
        item_id
    ):
        """將指定項目加入排序Puzzle目前順序。"""

        if self.ui_mode != "sequence":
            return False

        if item_id in self.sequence_input:
            return False

        expected = self.puzzle.get(
            "answer",
            []
        )

        if item_id not in expected:
            return False

        self.sequence_input.append(
            item_id
        )

        return True


    def remove_sequence_item(
        self,
        item_id
    ):
        """從排序Puzzle目前順序移除項目。"""

        if item_id not in self.sequence_input:
            return False

        self.sequence_input.remove(
            item_id
        )

        return True


    def clear_sequence(self):
        """清空目前排序Puzzle內容。"""

        self.sequence_input = []


    def set_active_field(
        self,
        field_id
    ):
        """切換Multi Input目前輸入欄位。"""

        if field_id not in self.multi_input:
            return False

        self.active_field_id = field_id
        return True


    def append_multi_input(
        self,
        value
    ):
        """在目前Multi Input欄位加入內容。"""

        if (
            self.ui_mode != "multi_input"
            or self.active_field_id is None
        ):
            return

        value = str(
            value
        )

        if (
            self.puzzle.get(
                "input_type"
            ) == "digits"
            and not value.isdigit()
        ):
            return

        current = self.multi_input[
            self.active_field_id
        ]

        # 年齡最多兩位即可涵蓋4、7、14
        self.multi_input[
            self.active_field_id
        ] = (
            current + value
        )[:2]


    def clear_active_multi_input(self):
        """只清除目前選取欄位並保留其他年齡。"""

        if self.active_field_id in self.multi_input:
            self.multi_input[self.active_field_id] = ""


    def remove_multi_input(self):
        """刪除目前欄位最後一個字元。"""

        if self.active_field_id is None:
            return

        current = self.multi_input.get(
            self.active_field_id,
            ""
        )

        self.multi_input[
            self.active_field_id
        ] = current[:-1]


    def reset_anchor_slots(self):
        """重設Scene13三個錨點凹槽。"""

        self.anchor_selected_fragment = None

        self.anchor_slots = {
            "past": None,
            "present": None,
            "future": None
        }


    def select_anchor_fragment(
        self,
        item_id
    ):
        """選取一枚尚未放入凹槽的錨點碎片。"""

        if item_id not in ANCHOR_FRAGMENT_TARGETS:
            return False

        if not self.puzzle_manager.game.has_item(
            item_id
        ):
            return False

        if item_id in self.anchor_slots.values():
            return False

        self.anchor_selected_fragment = (
            item_id
        )

        return True


    def place_anchor_fragment(
        self,
        slot_id
    ):
        """將目前選取碎片放入指定凹槽。"""

        item_id = (
            self.anchor_selected_fragment
        )

        if item_id is None:

            return {
                "status": "no_fragment_selected"
            }

        expected_slot = (
            ANCHOR_FRAGMENT_TARGETS.get(
                item_id
            )
        )

        if slot_id != expected_slot:

            self.anchor_selected_fragment = None

            return {
                "status": "wrong_slot",
                "slot": slot_id,
                "item_id": item_id
            }

        self.anchor_slots[
            slot_id
        ] = item_id

        self.anchor_selected_fragment = None

        complete = all(
            value is not None
            for value in self.anchor_slots.values()
        )

        return {
            "status": (
                "anchor_complete"
                if complete
                else "fragment_placed"
            ),
            "slot": slot_id,
            "item_id": item_id
        }

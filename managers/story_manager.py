from game_states import (
    DIALOGUE,
    CHOICE,
    SPACE,
    SUCCESS
)

from managers.interaction_manager import (
    finish_photo_story_dialogue
)


class StoryManager:
    """管理章節劇情流程與Dialogue完成後的後續動作。"""

    def __init__(
        self,
        game,
        dialogue_controller,
        choice_controller,
        dialogues
    ):
        self.game = game
        self.dialogue_controller = dialogue_controller
        self.choice_controller = choice_controller
        self.dialogues = dialogues

        self.chapter2_space_scenes = {
            "CH2_CORRIDOR": "scene_09_corridor",
            "T0": "scene_10_t0",
            "T7": "scene_11_t7",
            "T3": "scene_12_t3"
        }  # 統一保存第二章空間與劇情場景對應

        # 暫存Choice結果播放後要前往的空間
        self.pending_target_space = None

        # 記錄目前Dialogue結束後要執行的流程
        self.dialogue_after_action = None


        # 保存第一章結尾最後顯示的文字內容
        self.chapter_end_text = (
            "你只解開了一把鎖。"
            "但你還沒解開自己。"
        )


    def reset_story_state(self):
        """清除上一局尚未完成的劇情暫存狀態。"""

        self.pending_target_space = None
        self.dialogue_after_action = None

        self.chapter_end_text = (
            "你只解開了一把鎖。"
            "但你還沒解開自己。"
        )


    def start_new_game(self):
        """重設遊戲並開始第一章序章Dialogue。"""

        self.game.reset_game()
        self.reset_story_state()

        self.dialogue_controller.start(
            "intro",
            self.dialogues.get(
                "intro",
                []
            )
        )

        self.game.game_state = DIALOGUE

        self.dialogue_after_action = (
            "start_first_choice"
        )


    def start_first_choice(self):
        """開始307房第一次A/B/C選擇。"""

        self.game.current_scene = (
            "scene_04_choice"
        )

        self.game.game_state = CHOICE

        self.choice_controller.start(
            "scene_04_choice",
            self.dialogues[
                "scene_04_choice"
            ]
        )


    def start_choice_result(
        self,
        selected_option
    ):
        """播放玩家選擇之後的結果文字。"""

        self.pending_target_space = (
            selected_option.get(
                "target_space"
            )
        )

        result_text = (
            selected_option.get(
                "result_text",
                ""
            )
        )

        self.dialogue_controller.start(
            "scene_04_choice_result",
            [
                {
                    "speaker": "",
                    "text": result_text
                }
            ]
        )

        self.game.game_state = DIALOGUE

        self.dialogue_after_action = (
            "enter_selected_space"
        )


    def start_photo_story(
        self,
        photo_result
    ):
        """照片背面事件後播放劇情Dialogue。"""

        dialogue_lines = []

        # 加入照片事件第一段角色台詞
        dialogue_lines.append(
            {
                "speaker": "黎琛",
                "text": "空間D……還有？"
            }
        )

        # 加入顯示器亮起的旁白內容
        dialogue_lines.append(
            {
                "speaker": "",
                "text": (
                    "牆上顯示器突然亮起。"
                )
            }
        )

        system_message = photo_result.get(
            "system_message",
            {}
        )

        values = system_message.get(
            "values",
            {}
        )

        # 將目前三個空間收斂率整理成文字
        system_text = (
            "【收斂率更新】\n"
            f"空間A：{values.get('A', 81)}%\n"
            f"空間B：{values.get('B', 55)}%\n"
            f"空間C：{values.get('C', 37)}%"
        )

        dialogue_lines.append(
            {
                "speaker": "",
                "text": system_text
            }
        )

        dialogue_lines.append(
            {
                "speaker": "黎琛",
                "text": (
                    "收斂率在漲……"
                    "這個房間在消失。"
                    "我得走。"
                )
            }
        )

        self.dialogue_controller.start(
            "photo_back_story",
            dialogue_lines
        )

        self.game.game_state = DIALOGUE

        self.dialogue_after_action = (
            "finish_photo_story"
        )


    def start_chapter_end(
        self,
        ending_result
    ):
        """出口門進入後播放第一章結尾Dialogue。"""

        ending_dialogue = (
            ending_result.get(
                "dialogue",
                []
            )
        )

        self.chapter_end_text = (
            ending_result.get(
                "ending_text",
                self.chapter_end_text
            )
        )

        self.dialogue_controller.start(
            "chapter_1_end",
            ending_dialogue
        )

        # enter_door()已先切到SUCCESS，暫時改回對話狀態
        self.game.game_state = DIALOGUE

        self.dialogue_after_action = (
            "start_chapter2"
        )


    def start_dialogue(
        self,
        dialogue_id,
        after_action=None
    ):
        """播放指定Dialogue並保存結束後流程。"""

        dialogue_lines = self.dialogues.get(
            dialogue_id,
            []
        )

        self.dialogue_controller.start(
            dialogue_id,
            dialogue_lines
        )

        self.game.game_state = DIALOGUE
        self.dialogue_after_action = after_action

    def start_chapter2(self):
        """進入第二章白色通道並播放Scene 09開場。"""

        self.game.chapter = max(
            self.game.chapter,
            2
        )

        self.game.current_scene = (
            "scene_09_corridor"
        )

        self.game.complete_event(
            "t0_unlocked"
        )

        self.game.enter_space(
            "CH2_CORRIDOR"
        )

        self.start_dialogue(
            "scene_09_entry",
            after_action="return_to_space"
        )

    def inspect_chapter2_terminal(self):
        """播放白色通道終端機規則說明。"""

        self.start_dialogue(
            "scene_09_terminal",
            after_action="return_to_space"
        )

    def is_time_door_unlocked(
        self,
        target_space
    ):
        """確認指定時間門目前是否已經解鎖。"""

        required_events = {
            "T0": "t0_unlocked",
            "T7": "t7_unlocked",
            "T3": "t3_unlocked"
        }

        event_id = required_events.get(
            target_space
        )

        if event_id is None:
            return False

        return self.game.has_event(
            event_id
        )

    def enter_t0(self):
        """進入Scene 10目前時間病房。"""

        if not self.is_time_door_unlocked(
            "T0"
        ):
            return False

        self.game.current_scene = (
            "scene_10_t0"
        )

        self.game.enter_space(
            "T0"
        )

        if not self.game.has_event("scene_10_entered_once"):
            self.game.complete_event("scene_10_entered_once")  # 首次播放前記錄進房事件
            if not self.game.has_event("t0_completed"):  # 已完成病房的舊存檔略過進場
                self.start_dialogue("scene_10_entry", after_action="return_to_space")

        return True

    def start_puzzle_event(
        self,
        event_id,
        completion=None
    ):
        """集中處理Puzzle完成後觸發的劇情事件。"""

        if event_id == "t0_completed":

            self.complete_t0()

        elif event_id == "t7_completed":

            self.complete_t7()

        elif event_id == "t7_circuit_completed":

            self.complete_t7_circuit()

        elif event_id == "t3_capsule_opened":

            self.complete_t3_capsule()

        elif event_id == "anchor_verified":

            self.complete_anchor_verification()

        else:
            return False

        return True  # 回報劇情已接手以關閉舊介面


    def complete_t0(self):
        """完成T+0並解鎖未來時間。"""

        self.game.complete_event(
            "t0_completed"
        )

        self.game.complete_event(
            "t7_unlocked"
        )

        self.start_dialogue(
            "scene_10_fragment",
            after_action="return_to_space"
        )

    def enter_t7(self):
        """進入Scene 11未來病房。"""

        if not self.is_time_door_unlocked(
            "T7"
        ):
            return False

        self.game.current_scene = (
            "scene_11_t7"
        )

        self.game.enter_space(
            "T7"
        )

        if not self.game.has_event("t7_circuit_completed"):
            self.start_dialogue("scene_11_circuit_intro", after_action="open_t7_circuit")
        elif not self.game.has_event("scene_11_entered_once"):
            self.game.complete_event("scene_11_entered_once")  # 相容已修好電路的舊版存檔
        return True

    def complete_t7_circuit(self):
        """恢復未來病房供電並播放正式進場台詞。"""
        if not self.game.has_event("t7_circuit_completed"):
            self.game.complete_event("t7_circuit_completed")
            if not self.game.has_event("scene_11_entered_once"):
                self.game.complete_event("scene_11_entered_once")  # 正式進場對話只在首次供電播放
                self.start_dialogue("scene_11_entry", after_action="return_to_space")

    def complete_t7_rubbing(self):
        """保存0347情報並播放拓印劇情。"""

        self.game.learn_knowledge(
            "number_0347"
        )

        self.game.complete_event(
            "t7_rubbing_completed"
        )

        self.start_dialogue(
            "scene_11_rubbing",
            after_action="return_to_space"
        )

    def complete_t7_letter(self):
        """記錄玩家已閱讀十四歲黎念的信。"""

        self.game.learn_knowledge(
            "future_age_14"
        )

        self.game.complete_event(
            "t7_letter_read"
        )

        self.start_dialogue(
            "scene_11_letter",
            after_action="return_to_space"
        )

    def complete_t7(self):
        """完成T+7並解鎖過去時間。"""

        self.game.complete_event(
            "t7_completed"
        )

        self.game.complete_event(
            "t3_unlocked"
        )

        self.start_dialogue(
            "scene_11_fragment",
            after_action="return_to_space"
        )

    def request_enter_t3(self):
        """進入T-3前先播放終端警告。"""

        if not self.is_time_door_unlocked(
            "T3"
        ):
            return False

        self.start_dialogue(
            "scene_12_warning",
            after_action="enter_t3"
        )

        return True

    def enter_t3(self):
        """正式進入過去並移除不可帶回的未來物品。"""

        self.game.current_scene = (
            "scene_12_t3"
        )

        self.game.enter_space(
            "T3"
        )

        if self.game.has_event("scene_12_entered_once"):
            return
        self.game.complete_event("scene_12_entered_once")  # 記錄首次進房以避免再次化灰
        if self.game.has_event("t3_items_turned_to_ash"):
            return  # 舊存檔已化灰時直接恢復探索

        items_to_remove = [
            "rubbing_paper",
            "pencil",
            "t7_letter"
        ]

        for item_id in items_to_remove:

            self.game.remove_item(
                item_id
            )

        self.game.complete_event(
            "t3_items_turned_to_ash"
        )

        self.start_dialogue(
            "scene_12_entry",
            after_action="return_to_space"
        )

    def start_t3_search(self, object_id):
        """記錄已完成的搜尋並播放事後反應。"""

        if object_id not in ("t3_bed", "t3_desk", "t3_wardrobe"):
            return False
        self.game.complete_event(object_id + "_searched")
        self.start_dialogue("scene_12_wrong_search", after_action="return_to_space")
        return True


    def complete_t3_capsule(self):
        """時間膠囊打開後播放字條劇情。"""

        self.game.complete_event(
            "t3_capsule_opened"
        )

        self.start_dialogue(
            "scene_12_note",
            after_action="return_to_space"
        )

    def complete_t3_carving(self):
        """完成時間迴圈中的床板刻字事件。"""

        if not self.game.has_knowledge(
            "number_0347"
        ):
            return False

        if not self.game.has_item(
            "t3_knife"
        ):
            return False

        self.game.complete_event(
            "t3_0347_carved"
        )

        self.game.complete_event(
            "t3_completed"
        )

        self.start_dialogue(
            "scene_12_carving",
            after_action="return_to_space"
        )

        return True

    def return_to_chapter2_corridor(self):
        """由T0/T7/T3返回第二章白色通道。"""

        previous_space = (
            self.game.current_space
        )

        # 記錄返回白色走廊時對應的房門
        return_door_map = {
            "T0": "door_t0",
            "T7": "door_t7",
            "T3": "door_t3"
        }

        return_door_id = (
            return_door_map.get(
                previous_space
            )
        )

        # InteractionController若由外部注入/保存入口狀態，
        # 不要在StoryManager直接操作pixel座標。
        # 若目前StoryManager無法存取InteractionController，
        # 請只回傳return_door_id，並由呼叫端保存。
        #
        # 本函式最後可：
        # return return_door_id

        self.game.enter_space(
            "CH2_CORRIDOR"
        )

        if (
            previous_space == "T3"
            and self.game.has_event(
                "t3_completed"
            )
        ):
            self.game.current_scene = (
                "scene_13_anchor_terminal"
            )

            if not self.game.has_event("scene_13_started"):
                self.game.complete_event("scene_13_started")
                self.start_dialogue("scene_13_entry", after_action="return_to_space")  # 返回走廊後才播放終章開場

        elif self.game.has_event("scene_13_started"):
            self.game.current_scene = "scene_13_anchor_terminal"
        else:
            self.game.current_scene = (
                "scene_09_corridor"
            )

        return return_door_id


    def complete_anchor_fragments(self):
        """三枚碎片全部放入正確凹槽。"""

        self.game.complete_event(
            "anchor_fragments_placed"
        )

        self.start_dialogue(
            "scene_13_terminal",
            after_action="open_anchor_age_verification"
        )

    def complete_anchor_verification(
        self
    ):
        """完成三個時間年齡驗證並解鎖D。"""

        self.game.complete_event(
            "anchor_verified"
        )

        self.game.complete_event(
            "space_d_unlocked"
        )

        self.start_dialogue(
            "scene_13_success",
            after_action="return_to_space"
        )


    def start_scene_14(self):
        """從 D 門進入純對話場景。"""
        self.game.current_scene = "scene_14"
        self.game.current_space = None
        self.start_dialogue("scene_14", after_action="finish_chapter2")

    def inspect_time_door(
        self,
        target_space
    ):
        """顯示時間門名稱與目前狀態。"""

        door_names = {
            "T0": "T+0",
            "T7": "T+7",
            "T3": "T-3"
        }

        door_name = door_names.get(
            target_space,
            target_space
        )

        unlocked = (
            self.is_time_door_unlocked(
                target_space
            )
        )

        if unlocked:

            lines = [
                {
                    "speaker": "",
                    "text": door_name
                }
            ]

            after_actions = {
                "T0": "enter_t0_from_door",
                "T7": "enter_t7_from_door",
                "T3": "request_t3_from_door"
            }

            after_action = (
                after_actions.get(
                    target_space
                )
            )

        else:

            lines = [
                {
                    "speaker": "",
                    "text": door_name
                },
                {
                    "speaker": "黎琛",
                    "text": "還沒到時候。"
                }
            ]

            after_action = (
                "return_to_space"
            )

        self.dialogue_controller.start(
            f"time_door_{target_space}",
            lines
        )

        self.game.game_state = DIALOGUE
        self.dialogue_after_action = (
            after_action
        )

        return unlocked


    def finish_dialogue_action(self):
        """依照Dialogue用途處理後續遊戲流程。"""

        action = self.dialogue_after_action

        # 執行前先清除避免重複觸發
        self.dialogue_after_action = None

        if action == "start_first_choice":

            self.start_first_choice()

        elif action == "enter_selected_space":

            target = self.pending_target_space  # 保存序章選擇的實際目的地
            if target is not None:

                self.game.current_scene = (
                    "exploration"
                )

                self.game.enter_space(
                    target
                )

            # 完成切換後清除暫存目標空間
            self.pending_target_space = None
            if target == "A":
                return "first_choice_a"  # 只在序章選入空間甲時回傳入口

        elif action == "finish_photo_story":

            finish_photo_story_dialogue(
                self.game
            )

        elif action == "finish_chapter2":
            self.game.complete_chapter(2)
            self.game.complete_event("chapter_2_completed")
            self.game.current_scene = "chapter_2_end"
            self.game.current_space = None
            self.game.game_state = SUCCESS

        elif action == "start_chapter2":

            self.start_chapter2()

        elif action == "return_to_space":

            self.game.game_state = SPACE

        elif action == "enter_t3":

            self.enter_t3()

        elif action == "enter_t0_from_door":

            self.enter_t0()

        elif action == "enter_t7_from_door":

            self.enter_t7()

        elif action == "open_t7_circuit":

            self.game.game_state = SPACE
            return action

        elif action == "request_t3_from_door":

            self.request_enter_t3()

        elif action == "open_anchor_age_verification":

            self.game.complete_event(
                "anchor_age_puzzle_ready"
            )

            self.game.game_state = SPACE

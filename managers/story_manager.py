from game_states import (
    DIALOGUE,
    CHOICE,
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
            "show_chapter_end"
        )


    def finish_dialogue_action(self):
        """依照Dialogue用途處理後續遊戲流程。"""

        action = self.dialogue_after_action

        # 執行前先清除避免重複觸發
        self.dialogue_after_action = None

        if action == "start_first_choice":

            self.start_first_choice()

        elif action == "enter_selected_space":

            if self.pending_target_space is not None:

                self.game.current_scene = (
                    "exploration"
                )

                self.game.enter_space(
                    self.pending_target_space
                )

            # 完成切換後清除暫存目標空間
            self.pending_target_space = None

        elif action == "finish_photo_story":

            finish_photo_story_dialogue(
                self.game
            )

        elif action == "show_chapter_end":

            self.game.game_state = SUCCESS
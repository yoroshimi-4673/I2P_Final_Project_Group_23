"""負責interaction的鍵盤焦點與輸入處理"""
import pygame
from game_states import SPACE
from managers.interaction_manager import (
    search_object,
    collect_item
)

class InteractionController:

    def __init__(self, interaction_ui, story_manager, game, puzzle_controller):

        self.interaction_ui = interaction_ui
        self.story_manager = story_manager
        self.game = game
        self.puzzle_controller = puzzle_controller
        self.reset_puzzle_completion()
        self.pending_post_interaction_dialogue = None

        # 紀錄目前鍵盤焦點控制向ID
        self.focus_id = None

        # 紀錄焦點所屬Interaction模式
        self.focus_mode = None

        # 保存上一幀產生的按鈕Rect
        self.last_buttons = {}

        self.pending_entry_rift = None
        self.pending_entry_object = None  # 記錄下個空間的物件型出生來源
        
    def open_object(
        self,
        object_id
    ):
        if not self.game.has_event("tutorial_interact_done"):
            self.game.complete_event("tutorial_interact_done")
        """開啟世界中的指定互動物件。"""

        current_object = (
            self.interaction_ui
            .objects[
                object_id
            ]
        )

        if (
            object_id == "t0_diary"
            and self.game.is_puzzle_solved(
                "t0_diary_restore"
            )
        ):

            self.open_fixed_diary()

            return

        if current_object.get("reader_type") == "diary":
            self.puzzle_controller.diary_reader_page = 0
            self.interaction_ui.open_diary_reader(object_id)
            return

        object_type = current_object["type"]

        # 三個錯誤搜尋位置在互動結束後播放反應
        if self.game.current_space == "T3" and object_id in (
            "t3_bed", "t3_desk", "t3_wardrobe"
        ):
            self.pending_post_interaction_dialogue = object_id
            self.reset_interaction_focus()
            self.interaction_ui.open_object(object_id)
            if object_id == "t3_desk":
                self.open_container_child("t3_knife")
            return


        # 特殊互動交由劇情或既有介面處理
        if object_id == "ch2_terminal":

            if self.game.current_scene == "scene_09_corridor":
                self.interaction_ui.close()
                self.story_manager.inspect_chapter2_terminal()
                return

            if self.game.current_scene == "scene_13_anchor_terminal":
                if self.game.is_puzzle_solved("anchor_age_verification"):
                    self.interaction_ui.open_message("錨點驗證已經完成。", object_id)
                elif self.game.has_event("anchor_age_puzzle_ready"):
                    self.open_anchor_age_verification()
                elif not self.game.has_event("anchor_fragments_placed"):
                    self.interaction_ui.close()
                    self.interaction_ui.current_object_id = object_id
                    self.interaction_ui.mode = "anchor_fragments"
                    self.puzzle_controller.reset_anchor_drag_state()
                else:
                    self.interaction_ui.open_message("請等待終端機完成驗證準備。", object_id)
                return

        if object_type == "time_door":

            target_space = current_object.get(
                "target_space"
            )

            self.interaction_ui.close()

            self.story_manager.inspect_time_door(
                target_space
            )

            return

        if object_type == "time_exit":

            self.interaction_ui.open_exit_confirmation(
                object_id
            )

            return

        if object_type == "rubbing_target":

            required_items = (
                current_object.get(
                    "required_items",
                    []
                )
            )

            has_all_items = all(
                self.game.has_item(item_id)
                for item_id in required_items
            )

            if not has_all_items:

                self.interaction_ui.open_message(
                    "刻痕已經太淡了。需要某種方法把它保存下來。",
                    object_id
                )

                return

            if self.game.has_event(
                "t7_rubbing_completed"
            ):

                self.interaction_ui.open_message(
                    "床板上的刻痕已經完成拓印。",
                    object_id
                )

                return

            self.interaction_ui.close()

            self.story_manager.complete_t7_rubbing()

            return

        if object_type == "readable":

            self.interaction_ui.open_readable(
                object_id
            )

            return

        if object_type == "searchable_location":

            if object_id == "t3_windowsill":

                if not self.game.has_event(
                    "t3_time_capsule_found"
                ):

                    self.game.complete_event("t3_windowsill_searched")
                    self.game.complete_event(
                        "t3_time_capsule_found"
                    )

                    self.interaction_ui.open_message(
                        "夕陽照著窗台。下面藏著一只巴掌大的鐵盒，上面刻著：「給七歲的你」。",
                        object_id
                    )

                else:

                    self.interaction_ui.open_message(
                        "時間膠囊就在窗台下。",
                        object_id
                    )

                return

        if (
            object_id == "t3_time_capsule"
            and not self.game.has_event(
                "t3_time_capsule_found"
            )
        ):

            self.interaction_ui.open_message(
                "現在還沒有發現這個盒子。",
                object_id
            )

            return

        if object_type == "carving_target":

            if not self.game.has_event(
                "t3_capsule_opened"
            ):

                self.interaction_ui.open_message(
                    "床板底部目前沒有什麼值得注意的地方。",
                    object_id
                )

                return

            if not self.game.has_item(
                "t3_knife"
            ):

                self.interaction_ui.open_message(
                    "需要一個能在木板上留下刻痕的工具。",
                    object_id
                )

                return

            if not self.game.has_knowledge(
                "number_0347"
            ):

                self.interaction_ui.open_message(
                    "黎琛想不起該留下什麼數字。",
                    object_id
                )

                return

            if self.game.has_event(
                "t3_0347_carved"
            ):

                self.interaction_ui.open_message(
                    "床板底下已經刻著：0 3 4 7。",
                    object_id
                )

                return

            self.interaction_ui.close()

            self.story_manager.complete_t3_carving()

            return

        puzzle_id = current_object.get("puzzle_id")
        door_needs_puzzle = (
            object_type == "door"
            and puzzle_id is not None
            and not self.game.is_puzzle_solved(puzzle_id)
        )
        if object_type != "puzzle" and not door_needs_puzzle:

            self.interaction_ui.open_object(
                object_id
            )

            return

        self.interaction_ui.current_object_id = (
            object_id
        )

        result = (
            self.puzzle_controller
            .open_puzzle(
                puzzle_id
            )
        )

        self.interaction_ui.result = (
            result
        )

        if result[
            "status"
        ] == "input_required":

            self.interaction_ui.mode = (
                self.puzzle_controller
                .ui_mode
            )

        else:

            self.interaction_ui.mode = (
                "message"
            )

        self.reset_interaction_focus()

    def open_anchor_age_verification(self):
        """共用自動開啟與重新查看年齡謎題入口。"""

        self.interaction_ui.close()
        result = self.puzzle_controller.open_puzzle("anchor_age_verification")
        self.interaction_ui.current_object_id = "ch2_terminal"
        self.interaction_ui.result = result
        self.interaction_ui.mode = (
            self.puzzle_controller.ui_mode
            if result.get("status") == "input_required"
            else "message"
        )
        self.reset_interaction_focus()
        return result


    def submit_puzzle(self):
        """提交目前Puzzle並處理通用完成流程。"""

        diary_drag = self.puzzle_controller.ui_mode == "diary_drag"

        result = (
            self.puzzle_controller
            .submit()
        )

        self.interaction_ui.result = (
            result
        )

        status = result.get(
            "status"
        )

        if status == "correct":

            if diary_drag:
                self.puzzle_controller.reset_diary_drag_state()


            completion = result.get("on_complete")
            rewards = result.get("rewards", [])
            self.puzzle_controller.close_puzzle()

            if any(reward.get("type") == "item" for reward in rewards):
                self.item_notification_queue = self.get_new_item_notifications(rewards)
                self.item_notification_completion = completion
                self.item_notification_result = result
                self.item_notification_object_id = self.interaction_ui.current_object_id
                if result.get("reward_notification_order") == "before_completion":
                    self.puzzle_completion_stage = "before_completion"
                    self.show_next_item_notification()
                else:
                    self.puzzle_completion_stage = "message"
                    self.interaction_ui.mode = "message"
                    self.reset_interaction_focus()
                return result

            if completion is not None:

                self.handle_puzzle_completion(
                    completion
                )

            else:

                self.interaction_ui.mode = (
                    "message"
                )

        elif status == "game_over":

            self.interaction_ui.close()

        return result

    def get_new_item_notifications(self, rewards):
        return [
            reward["result"]
            for reward in rewards
            if reward.get("type") == "item"
            and (reward.get("result") or {}).get("status") == "item_found"
        ]

    def reset_puzzle_completion(self):
        self.item_notification_queue = []
        self.item_notification_completion = None
        self.item_notification_result = None
        self.item_notification_object_id = None
        self.puzzle_completion_stage = None

    def acknowledge_puzzle_success(self):
        completion = self.item_notification_completion
        self.item_notification_completion = None
        self.puzzle_completion_stage = "waiting"  # 劇情接手時保留整批道具通知
        self.interaction_ui.close()
        if completion is not None and not self.handle_puzzle_completion(completion):
            self.interaction_ui.close()
        self.resume_pending_item_notifications()

    def resume_pending_item_notifications(self):
        if (
            self.puzzle_completion_stage == "waiting"
            and self.game.game_state == SPACE
            and not self.interaction_ui.is_open()
        ):
            self.puzzle_completion_stage = "notifications"
            self.show_next_item_notification()

    def finish_interaction_sequence(self):
        """先完成待顯示的獎勵，再處理互動的事後反應。"""
        self.resume_pending_item_notifications()
        if (
            self.pending_post_interaction_dialogue is None
            or self.puzzle_completion_stage is not None
            or self.game.game_state != SPACE
            or self.interaction_ui.is_open()
        ):
            return

        object_id = self.pending_post_interaction_dialogue
        self.pending_post_interaction_dialogue = None  # 播放前清除避免重複觸發反應
        if self.game.current_space == "T3":
            self.story_manager.start_t3_search(object_id)

    def return_from_interaction(self):
        self.interaction_ui.go_back()
        self.finish_interaction_sequence()

    def show_next_item_notification(self):
        if self.item_notification_queue:
            notification = self.item_notification_queue.pop(0)
            self.interaction_ui.notification = notification
            self.interaction_ui.current_object_id = notification["item_id"]
            self.interaction_ui.mode = "item_notification"
            self.reset_interaction_focus()
            return

        if self.puzzle_completion_stage == "before_completion":
            completion = self.item_notification_completion
            self.interaction_ui.result = self.item_notification_result
            self.interaction_ui.current_object_id = self.item_notification_object_id
            self.interaction_ui.notification = None
            self.reset_puzzle_completion()
            if completion is not None:
                self.handle_puzzle_completion(completion)
            else:
                self.interaction_ui.mode = "message"
        else:
            self.reset_puzzle_completion()
            self.interaction_ui.close()
        self.reset_interaction_focus()

    def handle_puzzle_completion(
        self,
        completion
    ):
        """依Puzzle資料執行完成後的通用流程。"""

        action_type = completion.get(
            "type"
        )

        if action_type == "open_photo":

            item_id = completion.get(
                "item_id"
            )

            if item_id is None:

                self.interaction_ui.mode = (
                    "message"
                )

                return False

            self.interaction_ui.open_photo(
                item_id,
                mode=completion.get(
                    "mode",
                    "inventory"
                )
            )

            return True

        if action_type == "story_event":

            # 未來第二章若需要劇情事件可由StoryManager處理
            event_id = completion.get(
                "event"
            )

            if (
                event_id is not None
                and hasattr(
                    self.story_manager,
                    "start_puzzle_event"
                )
            ):

                handled = self.story_manager.start_puzzle_event(
                    event_id,
                    completion
                )

                if handled is True:
                    self.interaction_ui.close()
                    return True

        self.interaction_ui.mode = (
            "message"
        )
        return False

    def reset_interaction_focus(self):
        """重新開啟Interaction時清除上一個鍵盤焦點。"""

        self.focus_id = None
        self.focus_mode = None
        self.last_buttons = {}

    def get_interaction_rect_buttons(self, buttons):
        """只保留Interaction UI中可取得Rect的控制項。"""

        return {
            control_id: rect
            for control_id, rect in buttons.items()
            if isinstance(
                rect,
                pygame.Rect
            )
        }


    def ensure_interaction_focus(self, buttons):
        """確保目前Interaction模式具有有效鍵盤焦點。"""

        mode = self.interaction_ui.mode
        rect_buttons = self.get_interaction_rect_buttons(
            buttons
        )

        # 切換Interaction模式時重新選第一個控制項
        if mode != self.focus_mode:
            self.focus_mode = mode
            self.focus_id = None

        if not rect_buttons:
            self.focus_id = None
            return

        if self.focus_id not in rect_buttons:
            self.focus_id = next(
                iter(
                    rect_buttons
                )
            )


    def update_interaction_hover_focus(self, buttons, mouse_pos):
        """滑鼠移到控制項時同步鍵盤焦點。"""

        self.ensure_interaction_focus(
            buttons
        )

        for control_id, rect in (
            self.get_interaction_rect_buttons(
                buttons
            ).items()
        ):

            if rect.collidepoint(
                mouse_pos
            ):
                self.focus_id = control_id
                break


    def move_interaction_focus(
        self,
        direction_key,
        buttons
        ):
        """依照方向鍵移動Interaction UI目前焦點。"""

        self.ensure_interaction_focus(
            buttons
        )

        rect_buttons = self.get_interaction_rect_buttons(
            buttons
        )

        if (
            not rect_buttons
            or self.focus_id
            not in rect_buttons
        ):
            return

        current_rect = rect_buttons[
            self.focus_id
        ]

        current_center = pygame.Vector2(
            current_rect.center
        )

        candidates = []

        for control_id, rect in rect_buttons.items():

            if control_id == self.focus_id:
                continue

            center = pygame.Vector2(
                rect.center
            )

            delta = center - current_center

            valid = (
                direction_key == pygame.K_LEFT
                and delta.x < 0
            ) or (
                direction_key == pygame.K_RIGHT
                and delta.x > 0
            ) or (
                direction_key == pygame.K_UP
                and delta.y < 0
            ) or (
                direction_key == pygame.K_DOWN
                and delta.y > 0
            )

            if not valid:
                continue

            # 主方向距離優先，垂直偏差作為次要成本
            if direction_key in (
                pygame.K_LEFT,
                pygame.K_RIGHT
            ):
                score = (
                    abs(delta.x)
                    + abs(delta.y) * 1.5
                )

            else:
                score = (
                    abs(delta.y)
                    + abs(delta.x) * 1.5
                )

            candidates.append(
                (
                    score,
                    control_id
                )
            )

        if candidates:
            candidates.sort(
                key=lambda item: item[0]
            )

            self.focus_id = (
                candidates[0][1]
            )

            return

        # 指定方向沒有控制項時從另一側循環
        if direction_key == pygame.K_LEFT:
            self.focus_id = max(
                rect_buttons,
                key=lambda control_id: (
                    rect_buttons[
                        control_id
                    ].centerx
                )
            )

        elif direction_key == pygame.K_RIGHT:
            self.focus_id = min(
                rect_buttons,
                key=lambda control_id: (
                    rect_buttons[
                        control_id
                    ].centerx
                )
            )

        elif direction_key == pygame.K_UP:
            self.focus_id = max(
                rect_buttons,
                key=lambda control_id: (
                    rect_buttons[
                        control_id
                    ].centery
                )
            )

        elif direction_key == pygame.K_DOWN:
            self.focus_id = min(
                rect_buttons,
                key=lambda control_id: (
                    rect_buttons[
                        control_id
                    ].centery
                )
            )
    def activate_interaction_focus(self, buttons):
        """用Enter執行目前Interaction焦點控制項。"""

        self.ensure_interaction_focus(
            buttons
        )

        rect_buttons = self.get_interaction_rect_buttons(
            buttons
        )

        rect = rect_buttons.get(
            self.focus_id
        )

        if rect is None:
            return

        # 重用滑鼠點擊流程避免產生第二套互動邏輯
        self.handle_click(
            buttons,
            rect.center
        )

    def handle_key(self, event):

        """處理所有Interaction UI共用鍵盤操作。"""

        if not self.interaction_ui.is_open():
            return

        if self.interaction_ui.mode == "multi_input" and (self.puzzle_controller.last_result or {}).get("status") == "final_failure_pending":
            if event.key == pygame.K_RETURN:
                self.acknowledge_anchor_final_failure()
            return  # 最終失敗確認前不接受其他輸入

        if event.key == pygame.K_ESCAPE and self.interaction_ui.mode == "anchor_fragments":
            self.puzzle_controller.reset_anchor_drag_state()
            self.interaction_ui.close()
            return

        # 密碼介面仍保留數字鍵與Backspace快速輸入
        if self.interaction_ui.mode in ("password", "multi_input"):

            if (
                pygame.K_0
                <= event.key
                <= pygame.K_9
            ):
                digit = (
                    event.key
                    - pygame.K_0
                )

                self.puzzle_controller.append_input(
                    digit
                )
                return

            if event.key == pygame.K_BACKSPACE:
                self.puzzle_controller.remove_input()
                return
        # 陪伴日記拖放介面支援左右方向鍵直接翻頁
        if self.interaction_ui.mode == "diary_drag":
            if event.key == pygame.K_LEFT:
                self.puzzle_controller.previous_diary_spread()
                return
            if event.key == pygame.K_RIGHT:
                self.puzzle_controller.next_diary_spread()
                return
        # 四方向鍵統一移動目前Interaction焦點
        if event.key in (
            pygame.K_UP,
            pygame.K_DOWN,
            pygame.K_LEFT,
            pygame.K_RIGHT
        ):
            self.move_interaction_focus(
                event.key,
                self.last_buttons
            )
            return

        # Enter等同點擊目前鍵盤焦點控制項
        if event.key == pygame.K_RETURN:
            self.activate_interaction_focus(
                self.last_buttons
            )
            return

        # Escape統一處理返回或關閉互動視窗
        if event.key == pygame.K_ESCAPE:

            if self.interaction_ui.mode == "photo" and self.interaction_ui.photo_mode == "story":
                return  # 劇情照片需查看背面才能離開

            if (
                self.interaction_ui.mode == "item_notification"
                and (
                    self.puzzle_completion_stage in ("before_completion", "notifications")
                    or self.pending_post_interaction_dialogue is not None
                )
            ) or (
                self.puzzle_completion_stage == "message"
                and self.interaction_ui.result is self.item_notification_result
            ):
                return  # 確認成功訊息後才能繼續獎勵流程

            if self.interaction_ui.mode == "diary_drag":
                self.interaction_ui.open_diary_exit_confirmation()
                return
            if self.interaction_ui.mode == "diary_exit_confirmation":
                self.interaction_ui.mode = "diary_drag"
                return


            if self.interaction_ui.mode == "readable":
                self.close_readable()

            elif self.interaction_ui.mode == "password":
                self.interaction_ui.close()

            elif self.interaction_ui.parent_stack:
                self.return_from_interaction()

            else:
                self.interaction_ui.close()
                self.finish_interaction_sequence()

    def close_readable(self):
        """關閉文件並僅於首次閱讀後播放劇情。"""

        object_id = self.interaction_ui.current_object_id
        self.interaction_ui.close()

        if object_id == "t7_letter" and not self.game.has_event("t7_letter_read"):
            self.story_manager.complete_t7_letter()


    def handle_click(
        self,
        buttons,
        mouse_pos
        ):
        """處理所有Interaction Popup滑鼠操作。"""

        if not self.interaction_ui.is_open():

            return

        mode = self.interaction_ui.mode

        # ========================================================
        # Container
        # ========================================================

        if mode == "container":

            if (
                "close" in buttons
                and buttons[
                    "close"
                ].collidepoint(
                    mouse_pos
                )
            ):

                self.interaction_ui.close()
                self.finish_interaction_sequence()

                return

            for (
                child_id,
                rect
            ) in buttons.items():

                if child_id == "close":

                    continue

                if rect.collidepoint(
                    mouse_pos
                ):

                    self.open_container_child(
                        child_id
                    )

                    return

        # ========================================================
        # Searchable
        # ========================================================

        elif mode == "searchable":

            if buttons[
                "yes"
            ].collidepoint(
                mouse_pos
            ):

                self.interaction_ui.confirm_search()

            elif buttons[
                "no"
            ].collidepoint(
                mouse_pos
            ):

                self.interaction_ui.go_back()

        # ========================================================
        # Inspectable
        # ========================================================

        elif mode == "inspectable":

            if buttons[
                "back"
            ].collidepoint(
                mouse_pos
            ):

                self.return_from_interaction()

        # ========================================================
        # Rift
        # ========================================================

        elif mode == "rift":

            if buttons[
                "enter"
            ].collidepoint(
                mouse_pos
            ):

                if (
                    self.interaction_ui.result[
                        "status"
                    ]
                    == "rift_available"
                ):

                    # 切換前先保存來源裂隙與預期目的空間
                    source_rift_id = (
                        self.interaction_ui.current_object_id
                    )

                    target_space = (
                        self.interaction_ui.result.get(
                            "target_space"
                        )
                    )

                    self.interaction_ui.confirm_rift()

                    # 成功切換後交給新Space使用對應入口出生點
                    if self.game.current_space == target_space:
                        self.pending_entry_rift = (
                            source_rift_id
                        )

            elif buttons[
                "cancel"
            ].collidepoint(
                mouse_pos
            ):

                self.interaction_ui.close()

        # ========================================================
        # Password
        # ========================================================

        elif mode == "exit_confirmation":

            if buttons["leave"].collidepoint(
                mouse_pos
            ):

                self.confirm_time_room_exit()
                return

            if buttons["cancel"].collidepoint(
                mouse_pos
            ):

                self.interaction_ui.close()
                return

        elif mode == "diary_drag":

            if "_drag_rects" not in buttons:
                return

            # 翻頁按鈕 (< / >)
            if (
                "diary_prev_page" in buttons
                and buttons["diary_prev_page"].collidepoint(mouse_pos)
            ):
                self.puzzle_controller.previous_diary_spread()
                return

            if (
                "diary_next_page" in buttons
                and buttons["diary_next_page"].collidepoint(mouse_pos)
            ):
                self.puzzle_controller.next_diary_spread()
                return

            drag_rects = buttons.get(
                "_drag_rects",
                {}
            )

            # 先判斷頁面，避免按鈕區搶事件
            for page_id, rect in reversed(
                list(
                    drag_rects.items()
                )
            ):

                if rect.collidepoint(
                    mouse_pos
                ):

                    self.start_diary_drag(
                        page_id,
                        rect,
                        mouse_pos
                    )

                    return

            if buttons["confirm"].collidepoint(
                mouse_pos
            ):

                result = (
                    self.submit_puzzle()
                )

                self.interaction_ui.result = (
                    result
                )

                return

            if buttons["reset"].collidepoint(
                mouse_pos
            ):

                self.puzzle_controller.reset_diary_drag_state()

                self.interaction_ui.result = {
                    "status": "input_required",
                    "message": ""
                }

                return

            if buttons["exit"].collidepoint(
                mouse_pos
            ):

                self.interaction_ui.open_diary_exit_confirmation()

                return

        elif mode == "diary_exit_confirmation":

            if buttons["cancel"].collidepoint(
                mouse_pos
            ):

                self.interaction_ui.mode = "diary_drag"

                return

            if buttons["confirm"].collidepoint(
                mouse_pos
            ):

                self.puzzle_controller.discard_diary_drag()

                self.interaction_ui.close()

                return

        elif mode == "diary_reader":

            if (
                buttons.get(
                    "can_previous"
                )
                and buttons[
                    "previous"
                ].collidepoint(
                    mouse_pos
                )
            ):

                self.puzzle_controller.diary_reader_page -= 1
                return

            if (
                buttons.get(
                    "can_next"
                )
                and buttons[
                    "next"
                ].collidepoint(
                    mouse_pos
                )
            ):

                self.puzzle_controller.diary_reader_page += 1
                return

            if buttons[
                "close"
            ].collidepoint(
                mouse_pos
            ):

                self.interaction_ui.close()
                return

        elif mode == "sequence":

            for button_id, rect in buttons.items():
                if button_id.startswith("page:") and rect.collidepoint(mouse_pos):
                    item_id = button_id.split(":", 1)[1]
                    if item_id in self.puzzle_controller.sequence_input:
                        self.puzzle_controller.remove_sequence_item(item_id)
                    else:
                        self.puzzle_controller.append_sequence_item(item_id)
                    return

            if buttons["clear"].collidepoint(mouse_pos):
                self.puzzle_controller.clear_sequence()
            elif buttons["submit"].collidepoint(mouse_pos):
                self.submit_puzzle()
            elif buttons["back"].collidepoint(mouse_pos):
                self.interaction_ui.close()

        elif mode == "anchor_fragments":
            if buttons["close"].collidepoint(mouse_pos):
                self.puzzle_controller.reset_anchor_drag_state()
                self.interaction_ui.close()
            return

        elif mode == "multi_input":

            if (self.puzzle_controller.last_result or {}).get("status") == "final_failure_pending":
                if buttons["ack_failure"].collidepoint(mouse_pos):
                    self.acknowledge_anchor_final_failure()
                return

            for button_id, rect in buttons.items():
                if button_id.startswith("field:") and rect.collidepoint(mouse_pos):
                    self.puzzle_controller.set_active_field(button_id.split(":", 1)[1])
                    return
            for digit in map(str, range(10)):
                if buttons[digit].collidepoint(mouse_pos):
                    self.puzzle_controller.append_input(digit)
                    return
            if buttons["clear"].collidepoint(mouse_pos):
                self.puzzle_controller.clear_active_multi_input()
            elif buttons["submit"].collidepoint(mouse_pos):
                self.submit_puzzle()
            elif buttons["back"].collidepoint(mouse_pos):
                self.interaction_ui.close()

        elif mode == "password":

            for digit in (
                "0", "1", "2", "3", "4",
                "5", "6", "7", "8", "9"
            ):

                if (
                    digit in buttons
                    and buttons[
                        digit
                    ].collidepoint(
                        mouse_pos
                    )
                ):

                    self.puzzle_controller.append_input(
                        digit
                    )

                    return

            if buttons[
                "clear"
            ].collidepoint(
                mouse_pos
            ):

                self.puzzle_controller.clear_input()

            elif buttons[
                "submit"
            ].collidepoint(
                mouse_pos
            ):

                self.submit_puzzle()

            elif buttons[
                "back"
            ].collidepoint(
                mouse_pos
            ):

                self.interaction_ui.close()

        # ========================================================
        # Photo
        # ========================================================

        elif mode == "photo":

            if buttons[
                "front"
            ].collidepoint(
                mouse_pos
            ):

                self.interaction_ui.view_photo_front()

            elif buttons[
                "back"
            ].collidepoint(
                mouse_pos
            ):

                result = (
                    self.interaction_ui
                    .view_photo_back()
                )

                if (
                    result.get(
                        "status"
                    )
                    == "photo_story_triggered"
                ):

                    self.interaction_ui.close()

                    self.story_manager.start_photo_story(
                        result
                    )

            elif (
                buttons[
                    "allow_close"
                ]
                and buttons[
                    "close"
                ].collidepoint(
                    mouse_pos
                )
            ):

                self.interaction_ui.close()

        # ========================================================
        # Door
        # ========================================================

        elif mode == "door":

            if (
                "enter" in buttons
                and buttons[
                    "enter"
                ].collidepoint(
                    mouse_pos
                )
            ):

                result = (
                    self.interaction_ui
                    .confirm_door()
                )

                if (
                    result.get(
                        "status"
                    )
                    == "chapter_end"
                ):

                    self.interaction_ui.close()

                    self.story_manager.start_chapter_end(
                        result
                    )

                elif result.get("status") == "scene_transition" and result.get("target_scene") == "scene_14":
                    self.interaction_ui.close()
                    self.reset_interaction_focus()
                    self.story_manager.start_scene_14()

            elif (
                "cancel" in buttons
                and buttons[
                    "cancel"
                ].collidepoint(
                    mouse_pos
                )
            ):

                self.interaction_ui.close()

            elif (
                "close" in buttons
                and buttons[
                    "close"
                ].collidepoint(
                    mouse_pos
                )
            ):

                self.interaction_ui.close()

        # ========================================================
        # Item
        # ========================================================

        elif mode == "readable":

            if buttons["close"].collidepoint(mouse_pos):
                self.close_readable()

        elif mode == "item":

            if buttons[
                "close"
            ].collidepoint(
                mouse_pos
            ):

                self.interaction_ui.close()

        # ========================================================
        # Item Notification
        # ========================================================

        elif mode == "item_notification":

            if buttons[
                "ok"
            ].collidepoint(
                mouse_pos
            ):

                if self.puzzle_completion_stage in ("before_completion", "notifications"):
                    self.show_next_item_notification()
                    self.finish_interaction_sequence()
                else:
                    self.return_from_interaction()

        # ========================================================
        # Message
        # ========================================================

        elif mode == "message":

            if buttons[
                "ok"
            ].collidepoint(
                mouse_pos
            ):

                if (
                    self.puzzle_completion_stage == "message"
                    and self.interaction_ui.result is self.item_notification_result
                ):
                    self.acknowledge_puzzle_success()
                else:
                    self.return_from_interaction()


    def open_container_child(
        self,
        child_id
    ):
        """
        開啟Container子物件。

        已搜尋過的Searchable不再顯示是/否，
        而是直接顯示empty_text。
        """

        child = self.interaction_ui.objects[
            child_id
        ]

        # 美工刀只能從書桌容器的子道具取得
        if child_id == "t3_knife" and self.interaction_ui.current_object_id == "t3_desk":
            self.interaction_ui.push_current()
            if self.game.has_discovered_item(child_id):
                self.interaction_ui.open_message(
                    "美工刀已經被拿走了。", child_id
                )
            else:
                result = collect_item(self.game, child_id, self.interaction_ui.objects)
                self.interaction_ui.current_object_id = child_id
                self.interaction_ui.result = result
                self.interaction_ui.notification = result
                self.interaction_ui.mode = "item_notification"
            return

        if child[
            "type"
        ] == "searchable":

            item_id = child.get(
                "item"
            )

            if (
                item_id is not None
                and self.game.has_discovered_item(
                    item_id
                )
            ):

                self.interaction_ui.push_current()

                self.interaction_ui.current_object_id = (
                    child_id
                )

                self.interaction_ui.result = (
                    search_object(
                        self.game,
                        child_id,
                        self.interaction_ui.objects
                    )
                )

                self.interaction_ui.mode = (
                    "message"
                )

                return

        if child["type"] in ("puzzle", "carving_target"):
            if child["type"] == "carving_target":
                self.interaction_ui.push_current()  # 床板提示結束後先回到床的容器
            self.open_object(child_id)
        else:
            self.interaction_ui.open_child(child_id)

    def draw_focus(
        self,
        screen,
        buttons
    ):
        """繪製方向鍵與Enter目前作用的控制項外框。"""

        self.ensure_interaction_focus(
            buttons
        )

        rect = self.get_interaction_rect_buttons(
            buttons
        ).get(
            self.focus_id
        )

        if rect is None:
            return

        pygame.draw.rect(
            screen,
            (255, 225, 120),
            rect.inflate(6, 6),
            width=3,
            border_radius=9
        )


    def confirm_time_room_exit(self):
        """確認離開時間房並保存返回白色走廊的出生門。"""

        self.interaction_ui.close()

        entry_object = (
            self.story_manager
            .return_to_chapter2_corridor()
        )

        self.pending_entry_object = (
            entry_object
        )

        return entry_object


    def start_anchor_drag(self, buttons, mouse_pos):
        """開始拖曳尚未固定於凹槽的時間碎片。"""
        if buttons.get("close") and buttons["close"].collidepoint(mouse_pos):
            self.puzzle_controller.reset_anchor_drag_state()
            self.interaction_ui.close()
            return True
        pc = self.puzzle_controller
        for key, rect in buttons.items():
            if key.startswith("fragment:") and rect.collidepoint(mouse_pos):
                item_id = key.split(":", 1)[1]
                if not self.game.has_item(item_id) or item_id in pc.anchor_slots.values():
                    return False
                pc.anchor_dragging_fragment = item_id
                pc.anchor_drag_offset = (mouse_pos[0] - rect.x, mouse_pos[1] - rect.y)
                pc.anchor_fragment_positions[item_id] = rect.topleft
                return True
        return False

    def update_anchor_drag(self, mouse_pos):
        """滑鼠移動只更新碎片的暫時畫面座標。"""
        pc = self.puzzle_controller
        if pc.anchor_dragging_fragment:
            pc.anchor_fragment_positions[pc.anchor_dragging_fragment] = (
                mouse_pos[0] - pc.anchor_drag_offset[0], mouse_pos[1] - pc.anchor_drag_offset[1]
            )

    def finish_anchor_drag(self, buttons, mouse_pos):
        """放對凹槽才固定碎片並保存放置狀態。"""
        pc = self.puzzle_controller
        item_id = pc.anchor_dragging_fragment
        if item_id is None:
            return
        result = None
        for key, rect in buttons.items():
            if key.startswith("slot:") and rect.collidepoint(mouse_pos):
                result = pc.place_anchor_fragment(item_id, key.split(":", 1)[1])
                break
        pc.reset_anchor_drag_state()  # 空白與錯槽放置皆回到原本位置
        if result:
            self.interaction_ui.result = result
            if result["status"] == "anchor_complete":
                self.interaction_ui.close()
                self.story_manager.complete_anchor_fragments()

    def acknowledge_anchor_final_failure(self):
        """確認白牆完全吞沒走廊後結束遊戲。"""
        from game_states import GAME_OVER
        if (self.puzzle_controller.last_result or {}).get("status") == "final_failure_pending":
            self.interaction_ui.close()
            self.game.game_state = GAME_OVER

    def start_diary_drag(self, page_id, page_rect, mouse_pos):
        self.puzzle_controller.start_diary_drag(page_id, page_rect.topleft, mouse_pos)

    def update_diary_drag(self, mouse_pos):
        self.puzzle_controller.update_diary_drag(mouse_pos)

    def finish_diary_drag(self, buttons, mouse_pos):
        for name, rect in buttons.items():
            if name.startswith("diary_slot:") and rect.collidepoint(mouse_pos):
                self.puzzle_controller.finish_diary_drag(name.split(":", 1)[1])
                return

        self.puzzle_controller.finish_diary_drag(None)


    def open_fixed_diary(self):
        """開啟完成後的陪伴日記閱讀器。"""

        self.puzzle_controller.diary_reader_page = (
            0
        )

        self.interaction_ui.open_diary_reader(
            "t0_fixed_diary"
        )

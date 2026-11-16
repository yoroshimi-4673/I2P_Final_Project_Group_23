"""負責interaction的鍵盤焦點與輸入處理"""
import pygame
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

        # 紀錄目前鍵盤焦點控制向ID
        self.focus_id = None

        # 紀錄焦點所屬Interaction模式
        self.focus_mode = None

        # 保存上一幀產生的按鈕Rect
        self.last_buttons = {}

        self.pending_entry_rift = None
        
    def open_object(
        self,
        object_id
    ):
        """開啟世界中的指定互動物件。"""

        current_object = (
            self.interaction_ui
            .objects[
                object_id
            ]
        )

        object_type = current_object["type"]

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
                    if not any(self.puzzle_controller.anchor_slots.values()):
                        self.puzzle_controller.reset_anchor_slots()
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

            self.interaction_ui.close()

            self.story_manager.return_to_chapter2_corridor()

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

        if object_id == "t3_knife":

            if self.game.has_discovered_item(
                "t3_knife"
            ):

                self.interaction_ui.open_message(
                    "這把美工刀已經拿走了。",
                    object_id
                )

                return

            result = collect_item(
                self.game,
                "t3_knife",
                self.interaction_ui.objects
            )

            self.interaction_ui.current_object_id = (
                "t3_knife"
            )

            self.interaction_ui.result = result
            self.interaction_ui.notification = result
            self.interaction_ui.mode = (
                "item_notification"
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

        if object_type != "puzzle":

            self.interaction_ui.open_object(
                object_id
            )

            return

        self.interaction_ui.current_object_id = (
            object_id
        )

        puzzle_id = current_object.get(
            "puzzle_id"
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

            completion = result.get(
                "on_complete"
            )

            self.puzzle_controller.close_puzzle()

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

                return

            self.interaction_ui.open_photo(
                item_id,
                mode=completion.get(
                    "mode",
                    "inventory"
                )
            )

            return

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
                    return

        self.interaction_ui.mode = (
            "message"
        )

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

            if self.interaction_ui.mode == "readable":
                self.close_readable()

            elif self.interaction_ui.mode == "password":
                self.interaction_ui.close()

            elif self.interaction_ui.parent_stack:
                self.interaction_ui.go_back()

            else:
                self.interaction_ui.close()

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

                self.interaction_ui.go_back()

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

            for button_id, rect in buttons.items():
                if not rect.collidepoint(mouse_pos):
                    continue
                if button_id.startswith("fragment:"):
                    self.puzzle_controller.select_anchor_fragment(button_id.split(":", 1)[1])
                    return
                if button_id.startswith("slot:"):
                    result = self.puzzle_controller.place_anchor_fragment(
                        button_id.split(":", 1)[1]
                    )
                    self.interaction_ui.result = result
                    if result["status"] == "wrong_slot":
                        result["message"] = "碎片與這個凹槽無法吻合。"
                    elif result["status"] == "anchor_complete":
                        self.interaction_ui.close()
                        self.story_manager.complete_anchor_fragments()
                    return
                if button_id == "close":
                    self.interaction_ui.close()
                    return

        elif mode == "multi_input":

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

                self.interaction_ui.go_back()

        # ========================================================
        # Message
        # ========================================================

        elif mode == "message":

            if buttons[
                "ok"
            ].collidepoint(
                mouse_pos
            ):

                self.interaction_ui.go_back()

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

        if child["type"] == "puzzle":
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

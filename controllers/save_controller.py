import pygame

import managers.save_manager as save_manager
from game_states import DIALOGUE
from managers.save_manager import VALID_SAVE_SLOTS, get_save_slot_info


class SaveController:
    """管理選擇欄位、確認與回到遊戲的介面流程。"""

    START_ACTIONS = (("new", "新遊戲"), ("load", "讀取遊戲"), ("back", "返回"))

    def __init__(self, *, game=None, player=None, hotbar_controller=None,
                 dialogue_controller=None, story_manager=None):
        self.game = game
        self.player = player
        self.hotbar_controller = hotbar_controller
        self.dialogue_controller = dialogue_controller
        self.story_manager = story_manager
        self.active_save_slot = None
        self.close()

    def execute_action(self, action, *, screen_size=None, restore_loaded_session=None, start_new_game=None):
        """執行已確認的存讀檔操作，並回傳主畫面切換指令。"""
        if action is None:
            return None

        operation, slot = action
        if operation == "save":
            try:
                self._save(slot, screen_size)
            except (OSError, ValueError, pygame.error):
                self.complete("save", False)
            else:
                self.complete("save", True)
        elif operation == "load":
            session = {}
            success = save_manager.load_game(
                self.game, slot, self.player, self.hotbar_controller, restored_session=session,
            )
            if success:
                restore_loaded_session(session)  # 由遊戲主程式還原畫面與執行狀態
            self.complete("load", success)
        elif operation == "reset":
            try:
                save_manager.reset_save(slot)
            except OSError:
                self.complete("reset", False)
            else:
                self.complete("reset", True)
        elif operation == "new":
            self.active_save_slot = slot
            self.close()
            start_new_game()
        else:
            self.close()
            return operation
        return None

    def _save(self, slot, screen_size):
        session = {"screen_size": list(screen_size)}
        dialogue = self.dialogue_controller
        if self.game.game_state == DIALOGUE and not dialogue.finished:
            session["dialogue"] = {  # 保留原有對話存檔的欄位與結構
                "id": dialogue.dialogue_id,
                "lines": dialogue.lines,
                "index": dialogue.current_index,
                "visible_characters": dialogue.visible_characters,
                "after_action": self.story_manager.dialogue_after_action,
                "target_space": self.story_manager.pending_target_space,
            }
        save_manager.save_game(
            self.game, slot, self.player, self.hotbar_controller, self.screenshot, session=session,
        )

    def close(self):
        self.mode = None
        self.operation = None
        self.selected_slot = None
        self.delete_click_slot = None
        self.focused_slot = VALID_SAVE_SLOTS[0]
        self.focused_action = None
        self.slots = {}
        self.screenshot = None
        self.return_after_save = False
        self.message = ""

    def open_start(self):
        self.close()
        self.show("start")

    def open_ingame(self, screenshot, return_after_save=False):
        self.close()
        self.screenshot = screenshot
        self.return_after_save = return_after_save
        if return_after_save:
            self.show("return")
        else:
            self.open_slots("save")

    def open_slots(self, operation, preferred_slot=None):
        self.operation = operation
        self.slots = {slot: get_save_slot_info(slot) for slot in VALID_SAVE_SLOTS}
        self.focused_slot = preferred_slot or self.active_save_slot or VALID_SAVE_SLOTS[0]
        self.show("slots")

    def show(self, mode):
        self.mode = mode
        choices = self.action_choices()
        self.focused_action = "cancel" if mode in ("delete_confirm_1", "delete_confirm_2") else (
            choices[0][0] if choices else None
        )

    def action_choices(self):
        if self.mode == "start":
            return self.START_ACTIONS
        if self.mode in ("return", "confirm", "overwrite", "saved", "error",
                         "delete_confirm_1", "delete_confirm_2", "deleted", "delete_error"):
            return self.confirmation()[1]
        return ()

    def handle_navigation(self, key):
        if key == "reset" and self.mode == "slots" and self.operation == "load":
            self.selected_slot = None
            self.delete_click_slot = None
            self.show("delete_select")
            return None
        if key == "escape":
            return self.back()
        selecting_slot = self.mode in ("slots", "delete_select")
        if key == "enter":
            return self.activate(self.focused_slot if selecting_slot else self.focused_action)

        if selecting_slot and key in ("up", "down"):
            self.delete_click_slot = None
            index = VALID_SAVE_SLOTS.index(self.focused_slot)
            step = 1 if key == "down" else -1
            self.focused_slot = VALID_SAVE_SLOTS[(index + step) % len(VALID_SAVE_SLOTS)]
        elif (
            (self.mode == "start" and key in ("up", "down"))
            or (not selecting_slot and self.mode != "start" and key in ("left", "right"))
        ):
            controls = [control for control, _ in self.action_choices()]
            if controls:
                step = 1 if key in ("right", "down") else -1
                self.focused_action = controls[(controls.index(self.focused_action) + step) % len(controls)]
        return None

    def complete(self, operation, success):
        if operation == "reset":
            if success and self.selected_slot == self.active_save_slot:
                self.active_save_slot = None
            self.message = f"SLOT {self.selected_slot} 已刪除。" if success else "無法刪除存檔，請重試。"
            self.show("deleted" if success else "delete_error")
            return
        if success:
            self.active_save_slot = self.selected_slot
        if success and operation == "load":
            self.close()
        else:
            self.message = "存檔完成。" if success else "無法完成存讀檔，請重試。"
            self.show("saved" if success else "error")

    def handle_click(self, control):
        if self.mode == "delete_select" and control in self.slots:
            self.focused_slot = control
            if self.delete_click_slot != control:
                self.delete_click_slot = control
                return None
        return self.activate(control)

    def activate(self, control):
        if self.mode == "delete_select" and control in self.slots:
            if self.slots[control]["status"] != "NO DATA":
                self.focused_slot = control
                self.selected_slot = control
                self.show("delete_confirm_1")
            return None
        if self.mode == "delete_confirm_1" and control == "delete":
            self.show("delete_confirm_2")
            return None
        if self.mode == "delete_confirm_2" and control == "delete":
            return "reset", self.selected_slot
        if self.mode in ("deleted", "delete_error") and control == "yes":
            return self.back()
        if self.mode == "start" and control in ("new", "load"):
            self.open_slots(control)
        elif self.mode == "return" and control == "save":
            self.open_slots("save")
        elif self.mode == "return" and control == "discard":
            return "menu", None
        elif self.mode == "slots" and control in self.slots:
            self.focused_slot = control
            self.selected_slot = control
            if self.operation == "load" and self.slots[control]["status"] == "CORRUPTED":
                self.message = "此欄位的存檔已損毀，無法讀取。"
                self.show("error")
            else:
                self.show("confirm")
        elif self.mode in ("confirm", "overwrite") and control == "yes":
            slot = self.selected_slot
            status = self.slots[slot]["status"]
            if self.operation == "save":
                if status != "NO DATA" and self.mode == "confirm":
                    self.show("overwrite")
                else:
                    return "save", slot
            elif self.operation == "new" or status == "NO DATA":
                return "new", slot
            else:
                return "load", slot
        elif self.mode == "saved" and control == "yes":
            return ("menu" if self.return_after_save else "game"), None
        elif control in ("back", "no", "cancel"):
            return self.back()
        elif self.mode == "error" and control == "yes":
            self.open_slots(self.operation, self.selected_slot)
        return None

    def back(self):
        if self.mode == "delete_confirm_2":
            self.show("delete_confirm_1")
        elif self.mode == "delete_confirm_1":
            self.selected_slot = None
            self.delete_click_slot = None
            self.show("delete_select")
        elif self.mode in ("delete_select", "deleted", "delete_error"):
            slot = self.focused_slot
            self.selected_slot = None
            self.delete_click_slot = None
            self.open_slots("load", slot)
        elif self.mode == "saved":
            return ("menu" if self.return_after_save else "game"), None
        elif self.mode in ("confirm", "overwrite", "error"):
            self.open_slots(self.operation, self.selected_slot)
        elif self.mode == "slots" and self.operation != "save":
            operation = self.operation
            self.open_start()
            self.focused_action = operation
        elif self.mode == "start":
            return "menu", None
        else:
            return "settings", None
        return None

    def confirmation(self):
        if self.mode == "delete_confirm_1":
            return f"確定要刪除 SLOT {self.selected_slot} 嗎？", (("delete", "刪除"), ("cancel", "取消"))
        if self.mode == "delete_confirm_2":
            return "你真的確定要刪除嗎？請注意此操作無法復原。", (("delete", "確定刪除"), ("cancel", "取消"))
        if self.mode == "return":
            return "是否要在返回主畫面前存檔？", (("save", "存檔後返回"), ("discard", "不存檔"), ("no", "取消"))
        if self.mode == "overwrite":
            return "此存檔欄位已有資料，確定要覆蓋嗎？", (("yes", "覆蓋"), ("no", "取消"))
        if self.mode in ("saved", "error", "deleted", "delete_error"):
            return self.message, (("yes", "確定"),)
        status = self.slots[self.selected_slot]["status"]
        if self.operation == "save":
            message = "是否要將目前進度存入此存檔欄位？"
        elif status == "NO DATA":
            message = "此欄位無資料，是否開始新遊戲？"
        elif self.operation == "new":
            message = "此存檔欄位已有資料。開始新遊戲後，之後存檔可能覆蓋原有進度，是否繼續？"
        else:
            message = "是否要讀取這個存檔？"
        return message, (("yes", "是"), ("no", "否"))

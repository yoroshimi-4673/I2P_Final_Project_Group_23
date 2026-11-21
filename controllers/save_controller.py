from save_manager import VALID_SAVE_SLOTS, get_save_slot_info


class SaveController:
    """管理選擇欄位、確認與回到遊戲的介面流程。"""

    def __init__(self):
        self.active_save_slot = None
        self.close()

    def close(self):
        self.mode = None
        self.operation = None
        self.selected_slot = None
        self.slots = {}
        self.screenshot = None
        self.return_after_save = False
        self.message = ""

    def open_start(self):
        self.close()
        self.mode = "start"

    def open_ingame(self, screenshot, return_after_save=False):
        self.close()
        self.screenshot = screenshot
        self.return_after_save = return_after_save
        if return_after_save:
            self.mode = "return"
        else:
            self.open_slots("save")

    def open_slots(self, operation):
        self.operation = operation
        self.slots = {slot: get_save_slot_info(slot) for slot in VALID_SAVE_SLOTS}
        self.mode = "slots"

    def complete(self, operation, success):
        if success:
            self.active_save_slot = self.selected_slot
        if success and operation == "load":
            self.close()
        else:
            self.message = "存檔完成。" if success else "無法完成存讀檔，請重試。"
            self.mode = "saved" if success else "error"

    def activate(self, control):
        if self.mode == "start" and control in ("new", "load"):
            self.open_slots(control)
        elif self.mode == "return" and control == "save":
            self.open_slots("save")
        elif self.mode == "return" and control == "discard":
            return "menu", None
        elif self.mode == "slots" and control in self.slots:
            self.selected_slot = control
            if self.operation == "load" and self.slots[control]["status"] == "CORRUPTED":
                self.message = "此欄位的存檔已損毀，無法讀取。"
                self.mode = "error"
            else:
                self.mode = "confirm"
        elif self.mode in ("confirm", "overwrite") and control == "yes":
            slot = self.selected_slot
            status = self.slots[slot]["status"]
            if self.operation == "save":
                if status != "NO DATA" and self.mode == "confirm":
                    self.mode = "overwrite"
                else:
                    return "save", slot
            elif self.operation == "new" or status == "NO DATA":
                return "new", slot
            else:
                return "load", slot
        elif self.mode == "saved" and control == "yes":
            return ("menu" if self.return_after_save else "game"), None
        elif control in ("back", "no"):
            return self.back()
        elif self.mode == "error" and control == "yes":
            self.open_slots(self.operation)
        return None

    def back(self):
        if self.mode == "saved":
            return ("menu" if self.return_after_save else "game"), None
        if self.mode in ("confirm", "overwrite", "error"):
            self.open_slots(self.operation)
        elif self.mode == "slots" and self.operation != "save":
            self.open_start()
        elif self.mode == "start":
            return "menu", None
        else:
            return "settings", None
        return None

    def confirmation(self):
        if self.mode == "return":
            return "是否要在返回主畫面前存檔？", (("save", "存檔後返回"), ("discard", "不存檔"), ("no", "取消"))
        if self.mode == "overwrite":
            return "此存檔欄位已有資料，確定要覆蓋嗎？", (("yes", "覆蓋"), ("no", "取消"))
        if self.mode in ("saved", "error"):
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

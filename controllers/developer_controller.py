from managers.interaction_manager import enter_door


DEV_PRESETS = {
    "Chapter 1": (
        ("chapter1_intro", "Chapter 1 - Intro"),
        ("chapter1_choice", "Scene 04 · A / B / C 選擇"),
        ("chapter1_space_a", "Space A · 初始探索"),
        ("chapter1_space_b", "Space B · 初始探索"),
        ("chapter1_space_c", "Space C · 出口密碼鎖"),
        ("chapter1_ending", "Chapter 1 - Ending"),
    ),
    "Chapter 2": (
        ("chapter2_corridor", "白色走廊 · 初次進入"),
        ("chapter2_t0", "T+0 · 初次進入"),
        ("chapter2_t7_power_off", "T+7 · 停電與修電"),
        ("chapter2_t7_power_on", "T+7 · 供電後探索"),
        ("chapter2_t7_entry_dialogue", "T+7 · 修復後台詞"),
        ("chapter2_t3", "T-3 · 初次進入"),
        ("chapter2_t3_capsule_found", "T-3 · 已找到時間膠囊"),
        ("chapter2_t3_before_carving", "T-3 · 刻字前"),
        ("chapter2_scene13_start", "Scene 13 · 進場對話"),
        ("chapter2_scene13_fragments", "Scene 13 · 碎片拼合"),
        ("chapter2_scene13_age", "Scene 13 · 年齡驗證"),
        ("chapter2_scene13_completed", "Scene 13 · 空間 D 已解鎖"),
        ("chapter2_scene14", "Scene 14 · 結尾對話"),
    ),
}


class DeveloperController:
    def __init__(self, game, story_manager, interaction_controller, *, enabled):
        self.game = game
        self.story = story_manager
        self.interaction = interaction_controller
        self.enabled = enabled
        self.is_open = False
        self.category = "Chapter 1"
        self.focused_index = 0

    @property
    def presets(self):
        return DEV_PRESETS[self.category]

    def open(self):
        self.is_open = self.enabled
        return self.is_open

    def close(self):
        self.is_open = False

    def toggle(self):
        if self.is_open:
            self.close()
            return False
        return self.open()

    def select_category(self, category):
        if category in DEV_PRESETS and category != self.category:
            self.category = category
            self.focused_index = 0

    def move_focus(self, delta):
        self.focused_index = (self.focused_index + delta) % len(self.presets)

    def handle_navigation(self, key):
        if not self.is_open:
            return None
        if key in ("up", "down"):
            self.move_focus(1 if key == "down" else -1)
        elif key in ("left", "right"):
            other = "Chapter 2" if self.category == "Chapter 1" else "Chapter 1"
            self.select_category(other)
        elif key == "enter":
            return self.presets[self.focused_index][0]
        elif key == "escape":
            self.close()
        return None

    def handle_click(self, control):
        if not self.is_open:
            return None
        if control in DEV_PRESETS:
            self.select_category(control)
        elif control == "close":
            self.close()
        elif control in {preset_id for preset_id, _ in self.presets}:
            return control
        return None

    def apply_preset(self, preset_id):
        if not self.enabled or preset_id not in {
            key for presets in DEV_PRESETS.values() for key, _ in presets
        }:
            return False

        if preset_id == "chapter1_intro":
            self.story.start_new_game()
        else:
            self.game.reset_game()
            self.story.reset_story_state()
            getattr(self, f"_{preset_id}")()
        self.close()
        return True

    def _progress(self, *, events=(), items=(), knowledge=(), puzzles=(), discovered=()):
        for event in events:
            self.game.complete_event(event)
        for item in items:
            self.game.add_item(item)
        for detail in knowledge:
            self.game.learn_knowledge(detail)
        for puzzle in puzzles:
            self.game.solve_puzzle(puzzle)
        for item in discovered:
            self.game.discover_item(item)

    def _chapter1_choice(self):
        self.story.start_first_choice()

    def _chapter1_space(self, space):
        self.game.chapter = 1
        self.game.current_scene = "exploration"
        self.game.enter_space(space)

    def _chapter1_space_a(self):
        self._chapter1_space("A")

    def _chapter1_space_b(self):
        self._chapter1_space("B")

    def _chapter1_space_c(self):
        self._chapter1_space("C")

    def _chapter1_complete(self):
        self._progress(
            events=("chapter1_password_solved", "photo_back_seen"),
            items=("photo_1",),
            puzzles=("chapter1_password",),
        )

    def _chapter1_ending(self):
        self._chapter1_space("C")
        self._chapter1_complete()
        result = enter_door(self.game, "exit_door", self.interaction.interaction_ui.objects)
        self.story.start_chapter_end(result)

    def _chapter2_corridor(self):
        self._chapter1_complete()
        self.story.start_chapter2()

    def _chapter2_t0(self):
        self.game.chapter = 2
        self._chapter1_complete()
        self._progress(events=("t0_unlocked",))
        self.story.enter_t0()

    def _t0_complete(self):
        self.game.chapter = 2
        self._chapter1_complete()
        self._progress(
            events=("t0_unlocked", "t0_completed", "t7_unlocked"),
            items=("pencil", "t0_fixed_diary", "present_fragment", "rubbing_paper"),
            puzzles=("t0_bedside_drawer", "t0_diary_restore", "t0_child_safe"),
            discovered=("t0_diary_page_2", "t0_diary_page_4", "t0_diary_page_5"),
        )

    def _power_on(self):
        self._progress(events=("t7_circuit_completed",), puzzles=("t7_circuit",))

    def _chapter2_t7_power_off(self):
        self._t0_complete()
        self.story.enter_t7()

    def _chapter2_t7_power_on(self):
        self._t0_complete()
        self._power_on()
        self.story.enter_t7()

    def _chapter2_t7_entry_dialogue(self):
        self._chapter2_t7_power_on()
        self.story.start_dialogue("scene_11_entry", after_action="return_to_space")

    def _chapter2_t3(self):
        self._t0_complete()
        self._power_on()
        self._progress(
            events=("t7_rubbing_completed", "t7_letter_read", "t7_completed", "t3_unlocked"),
            items=("t7_letter", "future_fragment"),
            knowledge=("number_0347", "future_age_14"),
            puzzles=("t7_desk_drawer",),
        )
        self.story.enter_t3()

    def _chapter2_t3_capsule_found(self):
        self._chapter2_t3()
        self.story.finish_dialogue_action()
        self._progress(events=("t3_windowsill_searched", "t3_time_capsule_found"))

    def _chapter2_t3_before_carving(self):
        self._chapter2_t3_capsule_found()
        self._progress(
            events=("t3_capsule_opened",),
            items=("past_fragment", "t3_note", "t3_knife"),
            puzzles=("t3_time_capsule",),
        )

    def _chapter2_scene13_start(self):
        self._chapter2_t3_before_carving()
        self._progress(events=("t3_0347_carved", "t3_completed"))
        self.story.return_to_chapter2_corridor()

    def _chapter2_scene13_fragments(self):
        self._chapter2_scene13_start()
        self.story.finish_dialogue_action()

    def _anchor_fragments_placed(self):
        self._chapter2_scene13_fragments()
        self.game.scene13_anchor_slots.update({
            slot: f"{slot}_fragment" for slot in ("past", "present", "future")
        })
        self._progress(events=("anchor_fragments_placed", "anchor_age_puzzle_ready", "anchor_age_ui_opened"))

    def _chapter2_scene13_age(self):
        self._anchor_fragments_placed()
        self.interaction.open_anchor_age_verification()

    def _chapter2_scene13_completed(self):
        self._anchor_fragments_placed()
        self._progress(events=("anchor_verified", "space_d_unlocked"), puzzles=("anchor_age_verification",))

    def _chapter2_scene14(self):
        self._chapter2_scene13_completed()
        self.story.start_scene_14()

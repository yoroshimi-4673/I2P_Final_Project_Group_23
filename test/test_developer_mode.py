import unittest
from unittest.mock import Mock

from controllers.developer_controller import DEV_PRESETS, DeveloperController
from game_states import CHOICE, DIALOGUE, PASSWORD, SPACE
from test import test_chapter2_flow as flow


class DeveloperModeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        flow.Chapter2FlowTests.setUpClass()

    @classmethod
    def tearDownClass(cls):
        flow.Chapter2FlowTests.tearDownClass()

    def setUp(self):
        self.fixture = flow.Chapter2FlowTests()
        self.fixture.setUp()
        self.game = self.fixture.game
        self.story = self.fixture.story
        self.dev = DeveloperController(self.game, self.story, self.fixture.interaction, enabled=True)

    def apply(self, preset_id, *, space, state, dialogue=None):
        self.assertTrue(self.dev.apply_preset(preset_id))
        self.assertFalse(self.dev.is_open)
        self.assertEqual((self.game.current_space, self.game.game_state), (space, state))
        if dialogue is not None:
            self.assertEqual(self.fixture.dialogue.start.call_args.args[0], dialogue)

    def test_disabled_f8_toggle_cannot_open_or_apply(self):
        self.dev.enabled = False
        self.assertFalse(self.dev.toggle())
        self.assertFalse(self.dev.apply_preset("chapter2_t3"))
        self.assertIsNone(self.game.current_space)
        toggle = flow.home_function("toggle_developer_menu", {"developer_controller": self.dev})
        toggle()  # Disabled path returns before touching any game/UI globals.
        self.assertFalse(self.dev.is_open)

    def test_navigation_wrap_and_mouse_controls(self):
        self.assertTrue(self.dev.toggle())
        self.dev.handle_navigation("up")
        self.assertEqual(self.dev.handle_navigation("enter"), "chapter1_ending")
        self.dev.handle_navigation("down")
        self.assertEqual(self.dev.handle_navigation("enter"), "chapter1_intro")
        self.dev.handle_navigation("right")
        self.assertEqual((self.dev.category, self.dev.focused_index), ("Chapter 2", 0))
        self.assertEqual(self.dev.handle_click("chapter2_scene14"), "chapter2_scene14")
        self.dev.handle_click("Chapter 1")
        self.dev.handle_navigation("escape")
        self.assertFalse(self.dev.is_open)
        self.assertIsNone(self.dev.handle_navigation("enter"))
        self.assertTrue(self.dev.open())
        self.assertFalse(self.dev.toggle())

    def test_chapter_one_intro_choice_spaces_and_ending(self):
        self.apply("chapter1_intro", space=None, state=DIALOGUE, dialogue="intro")
        self.assertEqual(self.game.current_scene, "intro")
        self.apply("chapter1_choice", space=None, state=CHOICE)
        self.assertEqual(self.game.current_scene, "scene_04_choice")
        for space in "ABC":
            with self.subTest(space=space):
                self.apply(f"chapter1_space_{space.lower()}", space=space, state=SPACE)
                self.assertFalse(self.game.inventory)
                self.assertFalse(self.game.is_puzzle_solved("chapter1_password"))
        self.fixture.interaction.open_object("exit_door")
        self.assertEqual(self.fixture.ui.mode, "password")
        self.fixture.ui.close()
        self.apply("chapter1_ending", space="C", state=DIALOGUE, dialogue="chapter_1_end")
        self.assertEqual(self.game.current_scene, "chapter_1_end")
        self.assertIn("photo_1", self.game.inventory)
        self.story.finish_dialogue_action()
        self.assertEqual(self.game.current_space, "CH2_CORRIDOR")

    def test_corridor_t0_and_t7_power_variants(self):
        self.apply("chapter2_corridor", space="CH2_CORRIDOR", state=DIALOGUE, dialogue="scene_09_entry")
        self.assertEqual(self.game.chapter, 2)
        self.assertTrue(self.game.has_event("t0_unlocked"))
        self.apply("chapter2_t0", space="T0", state=DIALOGUE, dialogue="scene_10_entry")
        self.assertFalse(self.game.is_puzzle_solved("t0_child_safe"))
        self.apply("chapter2_t7_power_off", space="T7", state=DIALOGUE, dialogue="scene_11_circuit_intro")
        self.assertTrue(self.game.has_event("t7_unlocked"))
        self.assertFalse(self.game.has_event("t7_circuit_completed"))
        self.assertFalse(self.game.is_puzzle_solved("t7_circuit"))
        self.fixture.finish()
        self.assertEqual(self.fixture.ui.mode, "circuit")
        self.fixture.ui.close()
        self.fixture.dialogue.start.reset_mock()
        self.apply("chapter2_t7_power_on", space="T7", state=SPACE)
        self.fixture.dialogue.start.assert_not_called()
        self.assertTrue(self.game.has_event("t7_circuit_completed"))
        self.assertTrue(self.game.is_puzzle_solved("t7_circuit"))
        self.apply("chapter2_t7_entry_dialogue", space="T7", state=DIALOGUE, dialogue="scene_11_entry")

    def test_t3_checkpoints_and_reset_isolation(self):
        self.apply("chapter2_t3", space="T3", state=DIALOGUE, dialogue="scene_12_entry")
        self.assertTrue(self.game.has_event("t3_unlocked"))
        self.assertTrue(self.game.has_event("t3_items_turned_to_ash"))
        self.assertTrue(self.game.has_knowledge("number_0347"))
        self.assertTrue({"present_fragment", "future_fragment"} <= set(self.game.inventory))
        self.assertFalse({"rubbing_paper", "pencil", "t7_letter", "t3_knife", "past_fragment", "t3_note"} & set(self.game.inventory))
        self.assertTrue(self.game.has_discovered_item("t7_letter"))
        self.apply("chapter2_t3_capsule_found", space="T3", state=SPACE)
        self.assertTrue(self.game.has_event("t3_time_capsule_found"))
        self.assertFalse(self.game.has_event("t3_capsule_opened"))
        self.fixture.interaction.open_object("t3_time_capsule")
        self.assertEqual(self.fixture.ui.mode, "dial_password")
        self.fixture.ui.close()
        self.apply("chapter2_t3_before_carving", space="T3", state=SPACE)
        self.assertTrue({"t3_knife", "past_fragment", "t3_note"} <= set(self.game.inventory))
        self.assertTrue(self.game.has_event("t3_capsule_opened"))
        self.assertFalse(self.game.has_event("t3_completed"))
        self.fixture.interaction.open_object("t3_bed_board")
        self.assertTrue(self.game.has_event("t3_0347_carved"))
        self.apply("chapter1_space_a", space="A", state=SPACE)
        self.assertEqual(self.game.chapter, 1)
        for field in ("inventory", "discovered_items", "knowledge", "story_events", "solved_puzzles"):
            self.assertFalse(getattr(self.game, field))
        self.assertEqual(self.game.play_time, 0)

    def test_scene13_stages_and_scene14(self):
        self.apply("chapter2_scene13_start", space="CH2_CORRIDOR", state=DIALOGUE, dialogue="scene_13_entry")
        self.assertTrue(self.game.has_event("scene_13_started"))
        self.assertEqual(self.game.current_scene, "scene_13_anchor_terminal")
        self.apply("chapter2_scene13_fragments", space="CH2_CORRIDOR", state=SPACE)
        slots = {slot: f"{slot}_fragment" for slot in ("past", "present", "future")}
        self.assertTrue(set(slots.values()) <= set(self.game.inventory))
        self.assertEqual(self.game.scene13_anchor_slots, dict.fromkeys(slots))
        self.assertFalse(self.game.has_event("anchor_fragments_placed"))
        self.apply("chapter2_scene13_age", space="CH2_CORRIDOR", state=PASSWORD)
        self.assertEqual(self.game.scene13_anchor_slots, slots)
        self.assertTrue(self.game.has_event("anchor_fragments_placed"))
        self.assertTrue(self.game.has_event("anchor_age_puzzle_ready"))
        self.assertEqual(self.fixture.puzzle.current_puzzle_id, "anchor_age_verification")
        self.fixture.ui.close()
        self.apply("chapter2_scene13_completed", space="CH2_CORRIDOR", state=SPACE)
        self.assertTrue(self.game.has_event("anchor_verified"))
        self.assertTrue(self.game.has_event("space_d_unlocked"))
        self.assertTrue(self.game.is_puzzle_solved("anchor_age_verification"))
        self.apply("chapter2_scene14", space=None, state=DIALOGUE, dialogue="scene_14")
        self.assertEqual(self.game.current_scene, "scene_14")

    def test_home_application_resets_ui_and_leaves_active_save_slot_alone(self):
        reset = Mock()
        hotbar = Mock()
        active_slot = Mock(active_save_slot=2)
        state = {
            "developer_controller": self.dev, "reset_gameplay_ui": reset,
            "hotbar_controller": hotbar, "save_controller": active_slot,
            "UI_GAME": "game", "last_player_space": "T3",
        }
        apply = flow.home_function("apply_developer_preset", state)
        self.assertEqual(sum(map(len, DEV_PRESETS.values())), 19)
        apply("chapter1_space_b")
        reset.assert_called_once_with()
        hotbar.reset.assert_called_once_with()
        self.assertEqual(active_slot.active_save_slot, 2)
        self.assertEqual(state["ui_screen"], "game")
        self.assertIsNone(state["last_player_space"])

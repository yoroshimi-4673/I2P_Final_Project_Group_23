"""謎題核心與第一章互動流程的回歸驗證。"""
import copy
import io
import json
import os
from pathlib import Path
import unittest
from unittest.mock import Mock, mock_open, patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from controllers.interaction_controller import InteractionController
from controllers.hotbar_controller import HotbarController
from controllers.puzzle_controller import PuzzleController
from game_states import DIALOGUE, GAME_OVER, PASSWORD, SPACE
from managers.game_manager import GameManager
from managers.interaction_manager import get_door_info, interact_with_puzzle
from managers.puzzle_manager import PuzzleManager
from managers.story_manager import StoryManager
import save_manager
from ui.dialogue_ui import ChoiceController, DialogueController
from ui.game_ui import GameUI
from ui.codex_ui import CodexUI
from ui.interaction_ui import InteractionUI

ROOT = Path(__file__).resolve().parent.parent


def load_data(name):
    return json.loads((ROOT / "data" / name).read_text(encoding="utf-8"))


class PuzzleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.font.init()
        pygame.display.init()
        cls.screen = pygame.display.set_mode((800, 600))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        self.objects = load_data("objects.json")
        self.puzzles = load_data("puzzles.json")
        self.puzzle_id = self.objects["password_panel"]["puzzle_id"]
        self.answer = self.puzzles[self.puzzle_id]["answer"]
        self.wrong = "9" * self.puzzles[self.puzzle_id]["length"]
        self.game = GameManager()
        self.game.enter_space("C")
        self.manager = PuzzleManager(self.game, self.puzzles, self.objects)
        self.controller = PuzzleController(self.manager)

    def make_ui(self):
        levels = load_data("levels.json")
        game_ui = GameUI(load_data("ui_layout.json"), levels, self.objects)
        ui = InteractionUI(game_ui, self.game, self.objects, levels, self.controller)
        story = StoryManager(self.game, DialogueController(), ChoiceController(), load_data("dialogue.json"))
        interaction = InteractionController(ui, story, self.game, self.controller)
        return ui, interaction, story

    def test_invalid_format_does_not_consume_attempts(self):
        self.assertEqual(self.manager.submit_answer(self.puzzle_id, "1")["status"], "incomplete_input")
        self.assertEqual(self.manager.submit_answer(self.puzzle_id, "abcdef")["status"], "invalid_input")
        self.assertEqual(self.manager.get_remaining_attempts(self.puzzle_id), 3)
        self.assertEqual(self.game.puzzle_attempts, {})

    def test_three_failures_permanently_lock_until_new_game(self):
        for expected in (2, 1, 0):
            result = self.manager.submit_answer(self.puzzle_id, self.wrong)
            self.assertEqual(result["remaining_attempts"], expected)
        self.assertEqual(result["status"], "game_over")
        self.assertEqual(self.game.game_state, GAME_OVER)
        self.assertEqual(self.game.game_over_reason, self.puzzles[self.puzzle_id]["failure"]["reason"])
        self.assertEqual(self.manager.submit_answer(self.puzzle_id, self.answer)["status"], "puzzle_unavailable")
        self.assertFalse(self.game.inventory)
        self.game.reset_game()
        self.assertFalse(self.game.solved_puzzles)
        self.assertFalse(self.game.puzzle_attempts)
        self.assertEqual(self.manager.get_remaining_attempts(self.puzzle_id), 3)

    def test_success_rewards_once_even_after_item_removed(self):
        result = self.manager.submit_answer(self.puzzle_id, self.answer)
        item_id = result["rewards"][0]["value"]
        self.assertTrue(self.manager.is_solved(self.puzzle_id))
        self.assertTrue(self.game.has_event(self.puzzles[self.puzzle_id]["solved_flag"]))
        self.assertTrue(self.game.has_item(item_id))
        self.assertTrue(self.game.has_discovered_item(item_id))
        self.game.remove_item(item_id)
        self.assertEqual(self.manager.submit_answer(self.puzzle_id, self.answer)["status"], "puzzle_solved")
        self.assertFalse(self.game.has_item(item_id))
        self.game.reset_game()
        self.assertFalse(self.manager.is_solved(self.puzzle_id))

    def test_controller_input_uses_config_and_close_preserves_attempts(self):
        self.puzzles[self.puzzle_id]["length"] = 4
        self.controller.open_puzzle(self.puzzle_id)
        self.controller.append_input("a")
        self.assertEqual(self.controller.input_text, "")
        self.controller.append_input("987654")
        self.assertEqual(self.controller.input_text, "9876")
        self.assertEqual(self.controller.submit()["remaining_attempts"], 2)
        self.assertEqual(self.controller.input_text, "")
        self.controller.append_input("12")
        self.controller.remove_input()
        self.assertEqual(self.controller.input_text, "1")
        self.controller.clear_input()
        self.controller.close_puzzle()
        self.assertEqual(self.game.game_state, SPACE)
        self.controller.open_puzzle(self.puzzle_id)
        self.assertEqual(self.controller.remaining_attempts, 2)

    def test_requirements_and_independent_puzzles(self):
        extra = copy.deepcopy(self.puzzles[self.puzzle_id])
        extra["requirements"] = {"items": ["photo_1"], "flags": ["ready"], "puzzles": [self.puzzle_id]}
        extra["rewards"] = []
        self.puzzles["another_puzzle"] = extra
        self.assertFalse(self.manager.can_attempt("another_puzzle"))
        self.manager.submit_answer(self.puzzle_id, self.answer)
        self.game.complete_event("ready")
        self.assertTrue(self.manager.can_attempt("another_puzzle"))
        self.manager.submit_answer("another_puzzle", self.wrong)
        self.assertEqual(self.manager.get_remaining_attempts(self.puzzle_id), 3)
        self.assertEqual(self.manager.get_remaining_attempts("another_puzzle"), 2)

    def round_trip_save(self):
        # 使用記憶體檔案驗證真實存讀流程避免碰玩家存檔
        with patch("save_manager.open", mock_open(), create=True) as file:
            save_manager.save_game(self.game)
            serialized = "".join(call.args[0] for call in file().write.call_args_list)
        self.game.reset_game()
        with patch("save_manager.open", mock_open(read_data=serialized), create=True):
            self.assertTrue(save_manager.load_game(self.game))
        return json.loads(serialized)

    def test_save_load_round_trip(self):
        self.manager.submit_answer(self.puzzle_id, self.wrong)
        self.round_trip_save()
        self.assertEqual(self.game.puzzle_attempts, {self.puzzle_id: 2})
        self.manager.submit_answer(self.puzzle_id, self.answer)
        serialized = self.round_trip_save()
        self.assertTrue(self.manager.is_solved(self.puzzle_id))
        self.assertEqual(serialized["solved_puzzles"], [self.puzzle_id])
        self.assertEqual(self.controller.open_puzzle(self.puzzle_id)["status"], "puzzle_solved")

    def test_legacy_save_migration(self):
        old_save = {
            "solved_puzzles": ["password_panel"],
            "puzzle_attempts": {"password_panel": 2}
        }
        with patch("save_manager.open", mock_open(read_data=json.dumps(old_save)), create=True):
            self.assertTrue(save_manager.load_game(self.game))
        self.assertEqual(self.game.solved_puzzles, [self.puzzle_id])
        self.assertEqual(self.game.puzzle_attempts, {self.puzzle_id: 2})
        self.assertTrue(self.manager.is_solved(self.puzzle_id))
        self.assertFalse(self.manager.is_solved("password_panel"))
        serialized = self.round_trip_save()
        self.assertNotIn("password_panel", serialized["solved_puzzles"])
        self.assertNotIn("password_panel", serialized["puzzle_attempts"])

    def test_migration_merges_duplicates_and_keeps_lowest_attempts(self):
        for attempts in (
            {"password_panel": 2, self.puzzle_id: 1},
            {self.puzzle_id: 1, "password_panel": 2}
        ):
            with self.subTest(attempts=attempts):
                data = {
                    "solved_puzzles": ["password_panel", self.puzzle_id, "other"],
                    "puzzle_attempts": dict(attempts, other=5)
                }
                expected = {"solved_puzzles": [self.puzzle_id, "other"],
                            "puzzle_attempts": {self.puzzle_id: 1, "other": 5}}
                self.assertEqual(save_manager.migrate_legacy_puzzle_state(data), expected)
                self.assertEqual(save_manager.migrate_legacy_puzzle_state(data), expected)

    def test_unlimited_attempts(self):
        self.puzzles["unlimited"] = {"answer": "121", "input_type": "digits", "length": 3}
        for _ in range(10):
            result = self.manager.submit_answer("unlimited", "999")
            self.assertEqual(result["status"], "wrong")
            self.assertIsNone(result["remaining_attempts"])
            self.assertNotIn("None", result["message"])
        self.assertIsNone(self.manager.get_remaining_attempts("unlimited"))
        self.assertNotIn("unlimited", self.game.puzzle_attempts)
        self.assertTrue(self.manager.can_attempt("unlimited"))

    def test_text_puzzle_without_length(self):
        self.puzzles["greeting"] = {"answer": "hello", "input_type": "text"}
        self.assertEqual(self.controller.open_puzzle("greeting")["status"], "input_required")
        self.controller.append_input("hel")
        self.controller.append_input("lo")
        self.assertEqual(self.controller.input_text, "hello")
        self.assertEqual(self.controller.submit()["status"], "correct")
        self.assertTrue(self.manager.is_solved("greeting"))

    def test_unknown_and_inactive_puzzle(self):
        self.assertEqual(self.controller.submit()["status"], "no_puzzle")
        self.assertFalse(self.manager.is_solved(None))
        self.assertIsNone(self.manager.get_remaining_attempts(None))
        self.assertFalse(self.manager.check_answer("missing", "anything"))
        self.assertEqual(self.controller.open_puzzle("missing")["status"], "puzzle_not_found")
        self.assertEqual(self.manager.submit_answer("missing", "anything")["status"], "puzzle_not_found")

    def test_completion_action_is_explicit(self):
        result = self.manager.submit_answer(self.puzzle_id, self.answer)
        self.assertEqual(result["status"], "correct")
        self.assertEqual(result["on_complete"], {
            "type": "open_photo", "item_id": "photo_1", "mode": "story"
        })

    def test_photo_reward_without_completion_stays_message(self):
        self.puzzles[self.puzzle_id].pop("on_complete")
        ui, interaction, _ = self.make_ui()
        interaction.open_object("password_panel")
        self.controller.append_input(self.answer)
        interaction.submit_puzzle()
        self.assertTrue(self.game.has_item("photo_1"))
        self.assertEqual(ui.mode, "message")
        self.assertIsNone(ui.photo_id)
        self.assertEqual(ui.result["message"], "ACCESS GRANTED")

    def test_completion_opens_photo_without_using_back_text(self):
        self.objects["photo_1"].pop("back_text")
        ui, interaction, _ = self.make_ui()
        interaction.open_object("password_panel")
        self.controller.append_input(self.answer)
        interaction.submit_puzzle()
        self.assertEqual((ui.mode, ui.photo_id, ui.photo_mode), ("photo", "photo_1", "story"))

    def test_completion_fallback_and_optional_story_event(self):
        ui, interaction, _ = self.make_ui()
        for completion in ({"type": "unknown"}, {"type": "open_photo"},
                           {"type": "story_event", "event": "example"}):
            interaction.handle_puzzle_completion(completion)
            self.assertEqual(ui.mode, "message")
        interaction.story_manager = Mock()
        completion = {"type": "story_event", "event": "example"}
        interaction.handle_puzzle_completion(completion)
        interaction.story_manager.start_puzzle_event.assert_called_once_with("example", completion)

    def test_ui_mode_comes_from_data(self):
        self.puzzles[self.puzzle_id]["ui_mode"] = "custom_mode"
        ui, interaction, _ = self.make_ui()
        interaction.open_object("password_panel")
        self.assertEqual(ui.mode, "custom_mode")
        self.assertEqual(self.controller.ui_mode, "custom_mode")

    def test_unlimited_ui_omits_attempts_and_uses_configured_length(self):
        self.puzzles[self.puzzle_id].pop("max_attempts")
        self.puzzles[self.puzzle_id]["length"] = 4
        ui, interaction, _ = self.make_ui()
        interaction.open_object("password_panel")
        original_font = ui.game_ui.font_small
        font = Mock(wraps=original_font)
        ui.game_ui.font_small = font
        with patch("ui.interaction_ui.pygame.draw.rect", wraps=pygame.draw.rect) as draw_rect:
            ui.draw(self.screen, (0, 0))
        rendered = [call.args[0] for call in font.render.call_args_list]
        self.assertFalse(any("剩餘嘗試次數" in text or "None" in text for text in rendered))
        boxes = [call for call in draw_rect.call_args_list
                 if call.args[1] == (30, 32, 40)]
        self.assertEqual(len(boxes), 4)
        self.puzzles[self.puzzle_id].pop("length")
        ui.draw(self.screen, (0, 0))  # 缺少長度設定仍可安全繪製既有介面

    def test_ui_photo_story_and_exit_unlock(self):
        ui, interaction, story = self.make_ui()
        interaction.open_object("password_panel")
        self.assertEqual(ui.mode, "password")
        self.assertEqual(self.game.game_state, PASSWORD)
        buttons = ui.draw(self.screen, (0, 0))
        self.assertTrue(all(key in buttons for key in ("0", "9", "clear", "submit", "back")))
        interaction.handle_click(buttons, buttons["9"].center)
        interaction.handle_key(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_BACKSPACE))
        self.assertEqual(self.controller.input_text, "")
        self.controller.append_input(self.wrong)
        interaction.handle_click(buttons, buttons["submit"].center)
        self.assertEqual(self.controller.remaining_attempts, 2)
        self.controller.append_input(self.answer)
        interaction.handle_click(buttons, buttons["submit"].center)
        self.assertEqual((ui.mode, ui.photo_id, ui.photo_mode, ui.photo_side), ("photo", "photo_1", "story", "front"))
        self.assertEqual(get_door_info(self.game, "exit_door", self.objects)["status"], "door_locked")
        buttons = ui.draw(self.screen, (0, 0))
        self.assertFalse(buttons["allow_close"])
        interaction.handle_click(buttons, buttons["back"].center)
        self.assertTrue(self.game.has_event("photo_back_seen"))
        self.assertEqual(self.game.game_state, DIALOGUE)
        self.assertEqual(story.dialogue_after_action, "finish_photo_story")
        story.finish_dialogue_action()
        self.assertEqual(self.game.game_state, SPACE)
        self.assertEqual(get_door_info(self.game, "exit_door", self.objects)["status"], "door_available")
        interaction.open_object("password_panel")
        self.assertEqual(ui.mode, "message")

    def test_ui_escape_and_game_over_close(self):
        ui, interaction, _ = self.make_ui()
        interaction.open_object("password_panel")
        interaction.handle_key(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
        self.assertFalse(ui.is_open())
        self.assertIsNone(self.controller.current_puzzle_id)
        self.assertEqual(self.game.game_state, SPACE)
        interaction.open_object("password_panel")
        for _ in range(3):
            self.controller.append_input(self.wrong)
            interaction.submit_puzzle()
        self.assertFalse(ui.is_open())
        self.assertEqual(self.game.game_state, GAME_OVER)

    def test_text_entry_uses_same_rules(self):
        with patch("builtins.input", return_value=self.answer), patch("sys.stdout", new_callable=io.StringIO):
            with patch("managers.interaction_manager.interact_with_photo") as photo:
                interact_with_puzzle(self.game, "password_panel", self.objects, self.manager)
                photo.assert_called_once_with(self.game, "photo_1", self.objects, mode="story")
        self.assertTrue(self.manager.is_solved(self.puzzle_id))

    def test_ab_fragments_hotbar_codex_and_rifts(self):
        ui, interaction, _ = self.make_ui()
        codex = CodexUI(ui.game_ui, load_data("codex.json"), self.objects)
        hotbar = HotbarController(self.game, ui.game_ui, ui, interaction)
        for space, container, child, item in (
            ("A", "bed", "pillow", "fragment_1"),
            ("B", "workbench", "workbench_drawer", "fragment_2")
        ):
            with self.subTest(space=space):
                self.game.enter_space(space)
                interaction.open_object(container)
                self.assertEqual(ui.mode, "container")
                interaction.open_container_child(child)
                self.assertEqual(ui.mode, "searchable")
                buttons = ui.draw(self.screen, (0, 0))
                interaction.handle_click(buttons, buttons["yes"].center)
                self.assertTrue(self.game.has_item(item))
                self.assertTrue(codex.is_unlocked(self.game, item))
                hotbar.open_item(item)
                self.assertEqual((ui.mode, ui.current_object_id), ("item", item))
                ui.draw(self.screen, (0, 0))
                ui.close()
        self.assertEqual(codex.get_progress(self.game)[0], 2)
        interaction.open_object("floor_rift_B")
        buttons = ui.draw(self.screen, (0, 0))
        interaction.handle_click(buttons, buttons["enter"].center)
        self.assertEqual(self.game.current_space, "A")
        self.assertEqual(interaction.pending_entry_rift, "floor_rift_B")
        self.assertFalse(ui.is_open())


if __name__ == "__main__":
    unittest.main()

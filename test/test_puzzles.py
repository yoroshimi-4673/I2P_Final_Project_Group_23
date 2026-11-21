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
from managers.interaction_manager import collect_item, get_door_info, interact_with_puzzle
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
        self.layout = load_data("ui_layout.json")
        self.puzzle_id = self.objects["exit_door"]["puzzle_id"]
        self.answer = self.puzzles[self.puzzle_id]["answer"]
        self.wrong = "9" * self.puzzles[self.puzzle_id]["length"]
        self.game = GameManager()
        self.game.enter_space("C")
        self.manager = PuzzleManager(self.game, self.puzzles, self.objects)
        self.controller = PuzzleController(self.manager)

    def make_ui(self):
        levels = load_data("levels.json")
        game_ui = GameUI(self.layout, levels, self.objects)
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
        self.assertTrue(self.game.has_event("chapter1_password_solved"))
        self.assertEqual(get_door_info(self.game, "exit_door", self.objects)["status"], "door_available")
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
        interaction.open_object("exit_door")
        self.controller.append_input(self.answer)
        interaction.submit_puzzle()
        self.assertTrue(self.game.has_item("photo_1"))
        self.click(ui, interaction, "ok")
        self.assertEqual(ui.mode, "message")
        self.assertIsNone(ui.photo_id)
        self.assertEqual(ui.result["message"], "ACCESS GRANTED")

    def click(self, ui, interaction, control):
        buttons = ui.draw(self.screen, (0, 0))
        interaction.handle_click(buttons, buttons[control].center)

    def test_space_c_only_contains_exit_and_rifts(self):
        space = self.layout["spaces"]["C"]
        expected_objects = {"rift_C_A", "rift_C_B", "exit_door"}
        self.assertNotIn("password_panel", self.objects)
        self.assertEqual(set(space["objects"]), expected_objects)
        self.assertEqual(set(load_data("levels.json")["C"]["objects"]), expected_objects)
        self.assertNotIn("password_panel_body", space["collision_zones"])

    def test_chapter1_reward_notifies_then_plays_photo_story(self):
        ui, interaction, story = self.make_ui()
        interaction.open_object("exit_door")
        self.controller.append_input(self.answer)
        interaction.submit_puzzle()
        self.assertTrue(self.game.is_puzzle_solved("chapter1_password"))
        self.assertTrue(self.game.has_event("chapter1_password_solved"))
        self.assertTrue(self.game.has_item("photo_1"))
        self.assertEqual((ui.mode, ui.notification["item_id"]), ("item_notification", "photo_1"))
        interaction.handle_key(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
        self.assertEqual(ui.mode, "item_notification")
        self.click(ui, interaction, "ok")
        self.assertEqual(
            (ui.mode, ui.photo_id, ui.photo_mode, ui.photo_side),
            ("photo", "photo_1", "story", "front"),
        )
        interaction.handle_key(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
        self.assertEqual(ui.mode, "photo")
        self.assertFalse(ui.draw(self.screen, (0, 0))["allow_close"])
        self.assertFalse(self.game.has_event("photo_back_seen"))
        self.click(ui, interaction, "back")
        self.assertFalse(ui.is_open())
        self.assertTrue(self.game.has_event("photo_back_seen"))
        self.assertEqual(self.game.game_state, DIALOGUE)
        self.assertEqual(story.dialogue_controller.dialogue_id, "photo_back_story")
        script = "\n".join(line["text"] for line in story.dialogue_controller.lines)
        for line in (
            "空間D……還有？", "牆上顯示器突然亮起。", "收斂率更新",
            "空間A：81%", "空間B：55%", "空間C：37%",
            "收斂率在漲……", "這個房間在消失。", "我得走。",
        ):
            self.assertIn(line, script)
        story.finish_dialogue_action()
        self.assertEqual((self.game.current_space, self.game.game_state), ("C", SPACE))

        hotbar = HotbarController(self.game, ui.game_ui, ui, interaction)
        hotbar.open_item("photo_1")
        self.assertEqual((ui.mode, ui.photo_id, ui.photo_mode), ("photo", "photo_1", "inventory"))
        self.click(ui, interaction, "back")
        self.assertEqual((ui.mode, ui.photo_side, self.game.game_state), ("photo", "back", SPACE))
        ui.close()

        interaction.open_object("exit_door")
        self.assertEqual(ui.mode, "door")
        with patch.object(story, "start_chapter_end", wraps=story.start_chapter_end) as chapter_end:
            self.click(ui, interaction, "enter")
            chapter_end.assert_called_once()
            self.assertEqual(chapter_end.call_args.args[0]["target_scene"], "chapter_1_end")
        self.assertEqual(self.game.game_state, DIALOGUE)

    def test_drawer_notifies_only_new_items_in_reward_order(self):
        for owned in ((), ("pencil",), ("pencil", "t0_diary_page_4")):
            with self.subTest(owned=owned):
                self.game.reset_game()
                self.game.enter_space("T0")
                for item in owned:
                    self.game.add_item(item)
                ui, interaction, _ = self.make_ui()
                interaction.open_object("t0_bedside_drawer")
                self.controller.append_input("121")
                interaction.submit_puzzle()
                self.assertEqual(ui.mode, "message")
                self.assertEqual(ui.result["message"], "抽屜打開了。")
                self.click(ui, interaction, "ok")

                for item in ("pencil", "t0_diary_page_4"):
                    self.assertTrue(self.game.has_item(item))
                    if item not in owned:
                        self.assertEqual((ui.mode, ui.notification["item_id"]), ("item_notification", item))
                        self.click(ui, interaction, "ok")
                self.assertFalse(ui.is_open())
                self.assertIsNone(interaction.item_notification_result)

    def test_t0_item_assets_load_through_shared_renderer(self):
        ui, _, _ = self.make_ui()
        for item, asset in (("pencil", "pencil.png"), ("present_fragment", "piece.png")):
            with self.subTest(item=item):
                path = self.objects[item]["ui_asset"]
                self.assertEqual(Path(path).name, asset)
                self.assertTrue((ROOT / path).is_file())
                self.assertTrue(ui.game_ui.draw_item_asset(self.screen, item, pygame.Rect(0, 0, 50, 50)))

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
        interaction.open_object("exit_door")
        self.assertEqual(ui.mode, "custom_mode")
        self.assertEqual(self.controller.ui_mode, "custom_mode")

    def test_unlimited_ui_omits_attempts_and_uses_configured_length(self):
        puzzle_id = "t0_bedside_drawer"
        self.puzzles[puzzle_id].pop("max_attempts", None)
        self.puzzles[puzzle_id]["length"] = 4
        ui, interaction, _ = self.make_ui()
        interaction.open_object(puzzle_id)
        original_font = ui.game_ui.font_small
        font = Mock(wraps=original_font)
        ui.game_ui.font_small = font
        with patch("ui.interaction_ui.pygame.draw.rect", wraps=pygame.draw.rect) as draw_rect:
            buttons = ui.draw(self.screen, (0, 0))
        self.assertEqual(set(buttons), set("0123456789") | {"clear", "submit", "back"})
        interaction.handle_key(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_9))
        self.assertEqual(self.controller.input_text, "9")
        rendered = [call.args[0] for call in font.render.call_args_list]
        self.assertFalse(any("剩餘嘗試次數" in text or "None" in text for text in rendered))
        boxes = [call for call in draw_rect.call_args_list
                 if call.args[1] == (30, 32, 40)]
        self.assertEqual(len(boxes), 4)
        self.puzzles[puzzle_id].pop("length")
        ui.draw(self.screen, (0, 0))  # 缺少長度設定仍可安全繪製既有介面

    def test_unsolved_door_opens_password_and_preserves_attempts(self):
        ui, interaction, _ = self.make_ui()
        self.game.complete_event("photo_back_seen")
        interaction.open_object("exit_door")
        self.assertEqual(ui.mode, "password")
        self.assertEqual(self.controller.current_puzzle_id, "chapter1_password")
        self.assertEqual(self.game.game_state, PASSWORD)
        buttons = ui.draw(self.screen, (0, 0))
        self.assertEqual(list(buttons), ["1", "0"])
        interaction.handle_click(buttons, buttons["1"].center)
        interaction.handle_click(buttons, buttons["0"].center)
        interaction.handle_click(buttons, buttons["0"].center)
        self.assertEqual(self.controller.input_text, "100")
        interaction.handle_key(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_BACKSPACE))
        self.assertEqual(self.controller.input_text, "10")
        for key in range(pygame.K_2, pygame.K_9 + 1):
            interaction.handle_key(pygame.event.Event(pygame.KEYDOWN, key=key))
        self.assertEqual(self.controller.input_text, "10")
        for digit in "0100":
            self.click(ui, interaction, digit)
        self.assertEqual(ui.mode, "message")
        self.assertEqual(ui.result["message"].splitlines()[0], "密碼錯誤。")
        self.assertEqual(self.controller.input_text, "")
        self.assertEqual(self.controller.remaining_attempts, 2)
        self.click(ui, interaction, "ok")
        self.assertEqual(ui.mode, "password")
        interaction.handle_key(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
        interaction.open_object("exit_door")
        self.assertEqual(self.controller.remaining_attempts, 2)

    def test_ui_escape_and_game_over_close(self):
        ui, interaction, _ = self.make_ui()
        interaction.open_object("exit_door")
        interaction.handle_key(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
        self.assertFalse(ui.is_open())
        self.assertIsNone(self.controller.current_puzzle_id)
        self.assertEqual(self.game.game_state, SPACE)
        interaction.open_object("exit_door")
        for _ in range(3):
            for _ in range(6):
                interaction.handle_key(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_1))
            if ui.mode == "message":
                self.click(ui, interaction, "ok")
        self.assertFalse(ui.is_open())
        self.assertEqual(self.game.game_state, GAME_OVER)
        self.assertEqual(self.game.game_over_reason, "space_c_locked")

    def test_binary_password_submits_on_sixth_digit(self):
        ui, interaction, _ = self.make_ui()
        interaction.open_object("exit_door")
        for digit in "10010":
            key = pygame.K_0 + int(digit)
            interaction.handle_key(pygame.event.Event(pygame.KEYDOWN, key=key))
        self.assertEqual(self.controller.input_text, "10010")
        self.assertFalse(self.game.is_puzzle_solved(self.puzzle_id))
        self.assertEqual(self.controller.remaining_attempts, 3)
        self.click(ui, interaction, "1")
        self.assertTrue(self.game.is_puzzle_solved(self.puzzle_id))
        self.assertEqual(ui.notification["item_id"], "photo_1")

    def test_binary_lock_focus_cycles_and_enter_follows_the_yellow_frame(self):
        ui, interaction, _ = self.make_ui()
        interaction.open_object("exit_door")
        buttons = ui.draw(self.screen, (0, 0))
        interaction.last_buttons = buttons
        interaction.update_interaction_hover_focus(buttons, buttons["0"].center, mouse_moved=False)
        self.assertEqual(interaction.focus_id, "1")
        for key, target in (
            (pygame.K_RIGHT, "0"), (pygame.K_RIGHT, "1"),
            (pygame.K_LEFT, "0"), (pygame.K_LEFT, "1"),
        ):
            interaction.handle_key(pygame.event.Event(pygame.KEYDOWN, key=key))
            interaction.update_interaction_hover_focus(buttons, buttons["0"].center, mouse_moved=False)
            self.assertEqual(interaction.focus_id, target)

        enter = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN)
        interaction.handle_key(enter)
        interaction.update_interaction_hover_focus(buttons, buttons["0"].center)
        self.assertEqual(interaction.focus_id, "0")
        with patch("controllers.interaction_controller.pygame.draw.rect") as draw_rect:
            interaction.draw_focus(self.screen, buttons)
        draw_rect.assert_called_once_with(
            self.screen, (255, 220, 0), buttons["0"].inflate(8, 8), width=3, border_radius=6
        )
        interaction.handle_key(enter)
        self.assertEqual(self.controller.input_text, "10")

    def test_rubbing_codex_entries_unlock_and_persist_without_inventory_entries(self):
        ui, _, story = self.make_ui()
        codex = CodexUI(ui.game_ui, load_data("codex.json"), self.objects)
        self.assertTrue(codex.select_chapter("chapter_2"))
        before, after = "rubbing_paper_before_codex", "rubbing_paper_after_codex"
        items = codex.get_selected_chapter()["items"]
        self.assertNotIn("rubbing_paper", items)
        self.assertEqual(items[2:4], [before, after])
        self.assertEqual(codex.get_chapter_progress(self.game), (0, len(items)))
        for item_id in (before, after):
            self.assertFalse(self.objects[item_id].get("collectable", False))
            self.assertEqual(collect_item(self.game, item_id, self.objects)["status"], "not_collectable")
        self.assertFalse(self.game.discovered_items)
        self.game.add_item("rubbing_paper")
        self.assertTrue(codex.is_unlocked(self.game, before))
        self.assertFalse(codex.is_unlocked(self.game, after))
        self.assertEqual(codex.get_chapter_progress(self.game), (1, len(items)))
        story.complete_t7_rubbing()
        self.assertEqual(codex.get_chapter_progress(self.game), (2, len(items)))
        self.assertEqual(self.game.inventory, ["rubbing_paper"])
        story.enter_t3()
        self.round_trip_save()
        self.assertFalse(self.game.inventory)
        self.assertEqual(self.game.discovered_items, ["rubbing_paper"])
        self.assertTrue(codex.is_unlocked(self.game, before))
        self.assertTrue(codex.is_unlocked(self.game, after))

    def test_rubbing_paper_changes_hotbar_and_popup_without_replacing_item(self):
        ui, interaction, story = self.make_ui()
        self.game.enter_space("T7")
        self.game.add_item("pencil")
        self.game.add_item("rubbing_paper")
        inventory = self.game.inventory.copy()
        hotbar = HotbarController(self.game, ui.game_ui, ui, interaction)
        for completed, filename, description in (
            (False, "empty_paper.png", "一張空白紙，可以覆在刻痕上進行拓印。"),
            (True, "paper_0347.png", "拓印完成的紙。上面微微地刻著「0347」四個數字，下面還有一行小字：「刻給還沒出生的我們。」"),
        ):
            with self.subTest(completed=completed):
                if completed:
                    interaction.open_object("t7_broken_bed")
                    self.assertTrue(self.game.has_event("t7_rubbing_completed"))
                asset = f"assets/素材庫/第二章/T+0/{filename}"
                hotbar.open_item("rubbing_paper")
                self.assertEqual(ui.result["description"], description)
                with patch.object(ui.game_ui, "load_image", wraps=ui.game_ui.load_image) as load:
                    ui.game_ui.draw_hotbar(self.screen, self.game, 0, 0, (0, 0))
                    self.assertIn(asset, [call.args[0] for call in load.call_args_list])
                    load.reset_mock()
                    ui.draw(self.screen, (0, 0))
                    self.assertIn(asset, [call.args[0] for call in load.call_args_list])
                self.assertEqual(self.game.inventory, inventory)
                ui.close()
        story.enter_t3()
        self.assertFalse(self.game.has_item("rubbing_paper"))

    def test_text_entry_uses_same_rules(self):
        with patch("builtins.input", return_value=self.answer), patch("sys.stdout", new_callable=io.StringIO):
            with patch("managers.interaction_manager.interact_with_photo") as photo:
                interact_with_puzzle(self.game, "exit_door", self.objects, self.manager)
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

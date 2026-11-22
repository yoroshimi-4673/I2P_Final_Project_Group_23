from datetime import datetime
import json
import os
from pathlib import Path
from tempfile import gettempdir
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from uuid import uuid4

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame

from controllers.save_controller import SaveController
from controllers.settings_controller import SettingsController
from game_states import DIALOGUE, PASSWORD, SPACE
from managers.game_manager import GameManager
from player import Player
import managers.save_manager as saves
from ui.dialogue_ui import DialogueController
from ui.game_ui import GameUI
from ui.save_ui import SaveUI
from test.test_chapter2_flow import home_function


class SaveSlotTests(unittest.TestCase):
    def test_delete_flow_cancels_one_layer_at_a_time_and_accepts_corruption(self):
        saves.save_game(self.game, 2)
        saves.get_save_path(3).write_text("{", encoding="utf-8")
        controller = SaveController()
        nav = controller.handle_navigation
        for operation in ("new", "save"):
            controller.open_slots(operation)
            nav("reset")
            self.assertEqual(controller.mode, "slots")
        controller.open_slots("load")
        nav("reset")
        self.assertEqual(controller.mode, "delete_select")
        self.assertIsNone(controller.selected_slot)
        self.assertIsNone(nav("enter"))
        self.assertEqual(controller.mode, "delete_select")
        nav("down")
        self.assertEqual(controller.focused_slot, 2)
        nav("enter")
        self.assertEqual((controller.mode, controller.selected_slot, controller.focused_action),
                         ("delete_confirm_1", 2, "cancel"))
        nav("left")
        self.assertIsNone(nav("enter"))
        self.assertEqual(controller.mode, "delete_confirm_2")
        self.assertEqual(controller.confirmation()[0], "你真的確定要刪除嗎？請注意此操作無法復原。")
        self.assertEqual(controller.focused_action, "cancel")
        nav("escape")
        self.assertEqual((controller.mode, controller.focused_action), ("delete_confirm_1", "cancel"))
        nav("escape")
        self.assertEqual((controller.mode, controller.focused_slot), ("delete_select", 2))
        nav("down")
        nav("enter")
        self.assertEqual((controller.mode, controller.selected_slot), ("delete_confirm_1", 3))
        nav("escape")
        nav("escape")
        self.assertEqual((controller.mode, controller.operation), ("slots", "load"))

    def test_only_second_confirmation_resets_files_and_clears_legacy_slot_one(self):
        screenshot = pygame.Surface((16, 16))
        saves.save_game(self.game, 2, screenshot_surface=screenshot)
        second = {path: path.read_bytes() for path in (saves.get_save_path(2), saves.get_thumbnail_path(2))}
        for with_new_save in (False, True):
            with self.subTest(with_new_save=with_new_save):
                self.legacy.write_text('{"game_state":"space","current_space":"B"}', encoding="utf-8")
                if with_new_save:
                    saves.save_game(self.game, 1, screenshot_surface=screenshot)
                controller = SaveController()
                controller.active_save_slot = 1
                controller.open_slots("load")
                controller.handle_navigation("reset")
                controller.handle_click(1)
                self.assertIsNone(controller.selected_slot)
                controller.handle_click(1)
                self.assertIsNone(controller.activate("delete"))
                self.assertTrue(self.legacy.is_file())
                if with_new_save:
                    self.assertTrue(saves.get_save_path(1).is_file())
                    self.assertTrue(saves.get_thumbnail_path(1).is_file())
                controller.handle_navigation("left")
                action = controller.handle_navigation("enter")
                self.assertEqual(action, ("reset", 1))
                self.assertTrue(self.legacy.is_file())
                controller.execute_action(action)
                self.assertFalse(self.legacy.exists())
                self.assertFalse(saves.get_save_path(1).exists())
                self.assertFalse(saves.get_thumbnail_path(1).exists())
                self.assertIsNone(controller.active_save_slot)
                self.assertEqual(controller.confirmation()[0], "SLOT 1 已刪除。")
                controller.handle_navigation("enter")
                self.assertEqual(controller.slots[1]["status"], "NO DATA")
                self.assertEqual({path: path.read_bytes() for path in second}, second)

    def test_execute_action_handles_new_overwrite_and_backend_errors(self):
        saves.save_game(self.game, 2)
        controller = SaveController(game=self.game)
        start_new = Mock()
        controller.open_slots("new")
        controller.activate(2)
        self.assertIn("可能覆蓋原有進度", controller.confirmation()[0])
        controller.execute_action(controller.activate("yes"), start_new_game=start_new)
        start_new.assert_called_once_with()
        self.assertEqual((controller.active_save_slot, controller.mode), (2, None))

        controller.open_ingame(None)
        controller.activate(2)
        self.assertIsNone(controller.activate("yes"))
        self.assertEqual(controller.mode, "overwrite")
        with patch.object(saves, "save_game") as backend:
            controller.execute_action(controller.activate("yes"), screen_size=(800, 600))
        backend.assert_called_once_with(self.game, 2, None, None, None, session={"screen_size": [800, 600]})
        self.assertEqual(controller.mode, "saved")

        for error in (OSError, ValueError, pygame.error):
            with self.subTest(error=error), patch.object(saves, "save_game", side_effect=error):
                controller.execute_action(("save", 2), screen_size=(800, 600))
                self.assertEqual(controller.mode, "error")
        with patch.object(saves, "reset_save", side_effect=OSError):
            controller.execute_action(("reset", 2))
        self.assertEqual((controller.mode, controller.active_save_slot), ("delete_error", 2))

        saves.get_save_path(3).write_text("{", encoding="utf-8")
        controller.open_slots("load")
        restore = Mock()
        controller.execute_action(("load", 3), restore_loaded_session=restore)
        restore.assert_not_called()
        self.assertEqual(controller.mode, "error")
        controller.open_slots("load")
        controller.activate(1)
        start_new.reset_mock()
        controller.execute_action(controller.activate("yes"), start_new_game=start_new)
        start_new.assert_called_once_with()
        self.assertEqual(controller.active_save_slot, 1)

    def test_execute_action_round_trips_runtime_dialogue_and_window(self):
        pygame.display.init()
        self.addCleanup(pygame.quit)
        screen = pygame.display.set_mode((800, 600))
        player = Player(120, 200)
        hotbar = SimpleNamespace(selected_slot=0, offset=0, selected_item=None)
        dialogue = DialogueController()
        story = Mock(dialogue_after_action="enter_selected_space", pending_target_space="A")
        controller = SaveController(
            game=self.game, player=player, hotbar_controller=hotbar,
            dialogue_controller=dialogue, story_manager=story,
        )
        state = {
            "pygame": pygame, "screen": screen, "screen_width": 800, "screen_height": 600,
            "game": self.game, "player": player, "dialogue_controller": dialogue, "story_manager": story,
            "reset_gameplay_ui": Mock(), "DIALOGUE": DIALOGUE, "SPACE": SPACE, "CHOICE": "choice",
            "UI_GAME": "game", "ui_screen": "menu", "ui_overlay": "save",
        }
        home_function("get_4_3_window_size", state)
        home_function("scale_player_for_window", state)
        restore = home_function("restore_loaded_session", state)
        for size, expected_size, game_state in (
            ((1024, 768), (1024, 768), DIALOGUE),
            ((1000, 600), (1000, 750), SPACE),
        ):
            with self.subTest(size=size):
                self.game.game_state = game_state
                dialogue.start("scene_04_choice_result", [{"text": "First"}, {"text": "Second"}])
                dialogue.current_index = 1
                dialogue.visible_characters = 3
                original = pygame.Rect(120, 200, 40, 40)
                player.rect = original.copy()
                controller.open_ingame(None)
                controller.activate(1)
                action = controller.activate("yes")
                if controller.mode == "overwrite":
                    action = controller.activate("yes")
                controller.execute_action(action, screen_size=size)
                self.assertEqual(controller.mode, "saved")
                dialogue.start("other", [{"text": "Other"}])
                player.rect.topleft = (0, 0)
                controller.open_slots("load")
                controller.activate(1)
                controller.execute_action(controller.activate("yes"), restore_loaded_session=restore)
                self.assertEqual((state["ui_screen"], state["ui_overlay"]), ("game", None))
                self.assertEqual(state["screen"].get_size(), expected_size)
                self.assertEqual(state["last_player_space"], "T7")
                self.assertEqual(self.game.game_state, game_state)
                self.assertEqual(player.position, pygame.Vector2(player.rect.topleft))
                if game_state == DIALOGUE:
                    self.assertEqual(player.rect, original)
                    self.assertEqual(
                        (dialogue.dialogue_id, dialogue.current_index, dialogue.visible_characters),
                        ("scene_04_choice_result", 1, 3),
                    )
                    self.assertEqual(story.dialogue_after_action, "enter_selected_space")
                    self.assertEqual(story.pending_target_space, "A")
                else:
                    self.assertEqual(player.rect, pygame.Rect(120, 250, 40, 50))

    def setUp(self):
        directory = Path(gettempdir()) / f"i2p-save-test-{uuid4().hex}"
        directory.mkdir()
        self.addCleanup(directory.rmdir)
        self.legacy = directory / "save.json"
        self.addCleanup(self.legacy.unlink, missing_ok=True)
        self.addCleanup(self.clean_slots, directory / "saves")
        self.enterContext(patch.object(saves, "SAVE_DIR", directory / "saves"))
        self.enterContext(patch.object(saves, "LEGACY_SAVE_PATH", self.legacy))
        self.game = GameManager()
        self.game.enter_space("T7")

    def clean_slots(self, directory):
        if directory.is_dir():
            for path in directory.iterdir():
                path.unlink()
            directory.rmdir()

    def test_validate_slots_and_isolate_writes(self):
        self.assertEqual(saves.VALID_SAVE_SLOTS, (1, 2, 3))
        for invalid in (0, 4, True, "1"):
            for call in (
                saves.get_save_path, saves.get_thumbnail_path, saves.get_save_slot_info,
                lambda slot: saves.save_game(self.game, slot),
                lambda slot: saves.load_game(self.game, slot),
            ):
                with self.subTest(slot=invalid, call=call), self.assertRaises(ValueError):
                    call(invalid)
        self.assertEqual(saves.get_save_slot_info(1), {
            "slot": 1, "exists": False, "status": "NO DATA", "metadata": None, "thumbnail_path": None,
        })
        saves.save_game(self.game, 1)
        first = saves.get_save_path(1).read_bytes()
        self.game.enter_space("B")
        saves.save_game(self.game, 2)
        second = saves.get_save_path(2).read_bytes()
        self.assertEqual(saves.get_save_path(1).read_bytes(), first)
        self.game.enter_space("A")
        saves.save_game(self.game, 1)
        self.assertNotEqual(saves.get_save_path(1).read_bytes(), first)
        self.assertEqual(saves.get_save_path(2).read_bytes(), second)
        self.assertEqual(saves.get_save_slot_info(3)["status"], "NO DATA")

    def test_round_trip_metadata_thumbnail_and_all_game_state(self):
        game = self.game
        game.game_state = PASSWORD
        expected = {
            "current_scene": "scene_11_t7",
            "current_space": "T7",
            "inventory": ["pencil"],
            "discovered_items": ["rubbing_paper", "pencil"],
            "knowledge": ["number_0347"],
            "unlocked_objects": ["door_t7"],
            "inspected_objects": ["t7_safe"],
            "solved_puzzles": ["t7_circuit"],
            "story_events": ["t7_circuit_completed"],
            "puzzle_attempts": {"t3_time_capsule": 2},
            "scene13_anchor_slots": {"past": None, "present": "present_fragment", "future": None},
            "chapter": 2,
            "game_over_reason": "example",
        }
        for key, value in expected.items():
            setattr(game, key, value)
        player = SimpleNamespace(rect=pygame.Rect(237, 314, 60, 75))
        hotbar = SimpleNamespace(selected_slot=2, offset=1)
        screenshot = pygame.Surface((800, 600))
        screenshot.fill((25, 60, 120))
        session = {"screen_size": [800, 600]}
        with patch.object(game, "get_play_time", return_value=3661):
            saves.save_game(game, 3, player, hotbar, screenshot, session=session)
        info = saves.get_save_slot_info(3)
        metadata = info["metadata"]
        self.assertEqual(info["status"], "DATA")
        self.assertEqual(metadata["slot"], 3)
        self.assertEqual(metadata["chapter"], 2)
        self.assertEqual(metadata["chapter_name"], "Chapter 2")
        self.assertEqual(metadata["space"], "T7")
        self.assertIn("T+7", metadata["space_name"])
        self.assertEqual(metadata["play_time"], 3661)
        self.assertEqual(metadata["thumbnail"], "slot_3.png")
        self.assertIsInstance(datetime.fromisoformat(metadata["saved_at"]), datetime)
        image = pygame.image.load(info["thumbnail_path"])
        self.assertEqual(image.get_size(), (320, 240))
        for actual, expected_channel in zip(image.get_at((80, 60))[:3], (25, 60, 120)):
            self.assertAlmostEqual(actual, expected_channel, delta=2)

        restored = GameManager()
        restored_player = SimpleNamespace(
            rect=pygame.Rect(0, 0, 1, 1), position=pygame.Vector2(), cancel_mouse_movement=Mock()
        )
        restored_hotbar = SimpleNamespace(selected_slot=0, offset=0, selected_item="old")
        restored_session = {}
        self.assertTrue(saves.load_game(
            restored, 3, restored_player, restored_hotbar, restored_session=restored_session
        ))
        self.assertEqual(restored.game_state, SPACE)
        for key, value in expected.items():
            with self.subTest(key=key):
                self.assertEqual(getattr(restored, key), value)
        self.assertEqual(restored.play_time, 3661)
        self.assertEqual(restored_player.rect, player.rect)
        self.assertEqual(restored_player.position, pygame.Vector2(player.rect.topleft))
        restored_player.cancel_mouse_movement.assert_called_once_with()
        self.assertEqual(vars(restored_hotbar), {"selected_slot": 2, "offset": 1, "selected_item": None})
        self.assertEqual(restored_session, {**session, "has_player_position": True})

        info["thumbnail_path"].unlink()
        self.assertIsNone(saves.get_save_slot_info(3)["thumbnail_path"])
        self.assertTrue(saves.get_save_slot_info(3)["exists"])

    def test_corrupted_json_is_distinct_from_empty_and_cannot_load(self):
        path = saves.get_save_path(2)
        path.parent.mkdir()
        for contents in ("[", "{}", '{"game_state":"broken"}', '{"player":{"x":"bad"},"game_state":"space"}'):
            path.write_text(contents, encoding="utf-8")
            self.assertEqual(saves.get_save_slot_info(2)["status"], "CORRUPTED")
            self.assertFalse(saves.load_game(self.game, 2))
            self.assertEqual(self.game.current_space, "T7")

    def test_legacy_slot_one_reuses_migration_and_never_supersedes_a_new_save(self):
        old = {"game_state": SPACE, "current_space": "C", "solved_puzzles": ["password_panel"]}
        self.legacy.write_text(json.dumps(old), encoding="utf-8")
        self.assertTrue(saves.get_save_slot_info(1)["exists"])
        self.assertTrue(saves.load_game(self.game, 1))
        self.assertEqual(self.game.current_space, "C")
        self.assertTrue(self.game.is_puzzle_solved("chapter1_password"))
        self.assertFalse(saves.get_save_path(1).exists())
        self.game.enter_space("A")
        saves.save_game(self.game, 1)
        self.assertTrue(saves.load_game(self.game, 1))
        self.assertEqual(self.game.current_space, "A")
        self.assertEqual(json.loads(self.legacy.read_text(encoding="utf-8")), old)

    def test_main_menu_new_load_and_corrupted_selection(self):
        saves.save_game(self.game, 2)
        saves.get_save_path(3).write_text("{", encoding="utf-8")
        controller = SaveController()
        for mode, slot, action in (("new", 1, "new"), ("load", 2, "load"), ("load", 1, "new")):
            controller.open_start()
            self.assertEqual(controller.mode, "start")
            controller.activate(mode)
            self.assertEqual(tuple(controller.slots), (1, 2, 3))
            controller.activate(slot)
            self.assertEqual(controller.mode, "confirm")
            self.assertEqual(controller.activate("yes"), (action, slot))
        controller.activate("no")
        controller.activate(3)
        self.assertEqual(controller.mode, "error")
        self.assertIsNone(controller.activate("yes"))
        self.assertEqual(controller.mode, "slots")

    def test_save_overwrite_and_return_to_menu(self):
        saves.save_game(self.game, 2)
        controller = SaveController()
        screenshot = pygame.Surface((800, 600))
        controller.open_ingame(screenshot, return_after_save=True)
        self.assertEqual(controller.mode, "return")
        self.assertEqual(controller.activate("no"), ("settings", None))
        self.assertEqual(controller.activate("discard"), ("menu", None))
        controller.activate("save")
        self.assertEqual(controller.mode, "slots")
        controller.activate(2)
        self.assertIsNone(controller.activate("yes"))
        self.assertEqual(controller.mode, "overwrite")
        self.assertEqual(controller.activate("yes"), ("save", 2))
        self.assertIs(controller.screenshot, screenshot)
        controller.complete("save", True)
        self.assertEqual(controller.active_save_slot, 2)
        self.assertEqual(controller.activate("yes"), ("menu", None))
        controller.open_ingame(screenshot)
        controller.activate(1)
        self.assertEqual(controller.activate("yes"), ("save", 1))
        controller.complete("save", True)
        self.assertEqual(controller.activate("yes"), ("game", None))

    def test_settings_and_slot_ui_render_missing_or_corrupt_thumbnail(self):
        pygame.display.init()
        pygame.font.init()
        self.addCleanup(pygame.quit)
        screen = pygame.display.set_mode((800, 600))
        gui = GameUI({"base_resolution": {"width": 800, "height": 600}}, {}, {})
        buttons = gui.draw_settings_overlay(screen, (0, 0), 50)
        self.assertEqual(set(buttons), {"save", "tutorial", "slider", "800", "1024", "codex", "menu", "close"})
        settings = SettingsController()
        self.assertEqual(settings.handle_click(buttons, buttons["save"].center), "open_save")
        self.assertEqual(settings.handle_click(buttons, buttons["menu"].center), "go_menu")
        self.assertNotIn("save", gui.draw_settings_overlay(screen, (0, 0), 50, allow_save=False))
        saves.save_game(self.game, 2, screenshot_surface=screen)
        saves.get_thumbnail_path(2).write_bytes(b"broken image")
        controller = SaveController()
        controller.open_start()
        view = SaveUI(gui)
        self.assertEqual(set(view.draw(screen, (0, 0), controller)), {"back", "load", "new"})
        controller.activate("load")
        self.assertEqual(set(view.draw(screen, (0, 0), controller)), {1, 2, 3, "back"})
        self.assertTrue(controller.slots[2]["exists"])

    def test_keyboard_wraps_start_and_slot_focus_and_activates_the_same_actions(self):
        controller = SaveController()
        controller.open_start()
        self.assertEqual(controller.focused_action, "new")
        for key, expected in (("down", "load"), ("down", "back"), ("down", "new"), ("up", "back")):
            controller.handle_navigation(key)
            self.assertEqual(controller.focused_action, expected)
        self.assertEqual(controller.handle_navigation("enter"), ("menu", None))
        self.assertEqual(controller.handle_navigation("escape"), ("menu", None))

        controller.open_start()
        controller.handle_navigation("down")
        controller.handle_navigation("enter")
        self.assertEqual((controller.operation, controller.focused_slot), ("load", 1))
        for key, expected in (("down", 2), ("down", 3), ("down", 1), ("up", 3)):
            controller.handle_navigation(key)
            self.assertEqual(controller.focused_slot, expected)
        controller.handle_navigation("enter")
        self.assertEqual((controller.selected_slot, controller.focused_action), (3, "yes"))
        controller.handle_navigation("right")
        self.assertEqual(controller.focused_action, "no")
        controller.handle_navigation("left")
        self.assertEqual(controller.focused_action, "yes")
        controller.handle_navigation("escape")
        self.assertEqual((controller.mode, controller.focused_slot), ("slots", 3))
        controller.handle_navigation("escape")
        self.assertEqual((controller.mode, controller.focused_action), ("start", "load"))

        controller.active_save_slot = 2
        controller.handle_navigation("enter")
        self.assertEqual(controller.focused_slot, 2)

    def test_return_and_corrupt_confirmation_support_keyboard(self):
        controller = SaveController()
        for moves, expected in ((0, None), (1, ("menu", None)), (2, ("settings", None))):
            controller.open_ingame(None, return_after_save=True)
            for _ in range(moves):
                controller.handle_navigation("right")
            self.assertEqual(controller.handle_navigation("enter"), expected)
            if moves == 0:
                self.assertEqual((controller.mode, controller.operation), ("slots", "save"))
        controller.open_ingame(None, return_after_save=True)
        self.assertEqual(controller.handle_navigation("escape"), ("settings", None))

        path = saves.get_save_path(2)
        path.parent.mkdir()
        path.write_text("{", encoding="utf-8")
        controller.open_slots("load")
        controller.handle_navigation("down")
        self.assertEqual(controller.focused_slot, 2)
        controller.handle_navigation("enter")
        self.assertEqual((controller.mode, controller.focused_action), ("error", "yes"))

    def test_scaled_rows_and_hover_leave_keyboard_focus_intact(self):
        pygame.display.init()
        pygame.font.init()
        self.addCleanup(pygame.quit)
        gui = GameUI({"base_resolution": {"width": 800, "height": 600}}, {}, {})
        saves.save_game(self.game, 2)
        controller = SaveController()
        controller.active_save_slot = 2
        controller.open_slots("load")
        controller.slots[2]["metadata"]["saved_at"] = "malformed timestamp"
        view = SaveUI(gui)
        for size in ((640, 480), (800, 600), (1024, 768)):
            with self.subTest(size=size):
                screen = pygame.display.set_mode(size)
                buttons = view.draw(screen, (0, 0), controller)
                buttons = view.draw(screen, buttons[3].center, controller)
                self.assertEqual(controller.focused_slot, 2)
                self.assertTrue(all(screen.get_rect().contains(rect) for rect in buttons.values()))
                self.assertLess(buttons[3].bottom, gui.scale_y(screen, 544))
                self.assertEqual(screen.get_at((buttons[2].x + 5, buttons[2].centery))[:3], view.FOCUS)
                self.assertNotEqual(screen.get_at((buttons[3].x + 5, buttons[3].centery))[:3], view.FOCUS)
        controller.activate(3)
        self.assertEqual((controller.focused_slot, controller.selected_slot), (3, 3))

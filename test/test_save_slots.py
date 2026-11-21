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
from game_states import PASSWORD, SPACE
from managers.game_manager import GameManager
import save_manager as saves
from ui.game_ui import GameUI
from ui.save_ui import SaveUI


class SaveSlotTests(unittest.TestCase):
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

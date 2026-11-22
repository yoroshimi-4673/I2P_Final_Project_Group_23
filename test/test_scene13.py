"""Scene 13 終端啟用、碎片拖放及存檔相容測試。"""
import copy
import json
import unittest
from unittest.mock import patch

import pygame
import test_chapter2_flow as flow
from game_states import DIALOGUE, SPACE
from managers.game_manager import GameManager
from managers.map_manager import MapManager
import managers.save_manager as save_manager


class Scene13Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        cls.screen = pygame.display.set_mode((800, 600))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        self.f = flow.Chapter2FlowTests()
        self.f.screen = self.screen
        self.f.setUp()
        self.f.game.enter_space("CH2_CORRIDOR")
        self.f.game.current_scene = "scene_13_anchor_terminal"
        for item in ("past_fragment", "present_fragment", "future_fragment"):
            self.f.game.add_item(item)

    def drag(self, item, slot=None):
        buttons = self.f.ui.draw(self.screen, (0, 0))
        self.assertTrue(self.f.interaction.start_anchor_drag(buttons, buttons["fragment:" + item].center))
        position = buttons["slot:" + slot].center if slot else (10, 590)
        self.f.interaction.update_anchor_drag(position)
        self.f.interaction.finish_anchor_drag(buttons, position)

    def test_entry_terminal_visibility_and_collision(self):
        f = self.f
        manager = MapManager(copy.deepcopy(f.layout), f.game_ui, f.game)
        before = manager.build_space_runtime_data("CH2_CORRIDOR", self.screen)
        self.assertNotIn("ch2_terminal", before["object_rects"])
        self.assertNotIn("ch2_terminal_body", before["collision_rects"])
        f.game.enter_space("T3")
        f.game.complete_event("t3_completed")
        self.assertEqual(f.story.return_to_chapter2_corridor(), "door_t3")
        f.expect_dialogue("scene_13_entry")
        self.assertIsNone(f.puzzle.current_puzzle_id)
        f.finish()
        self.assertEqual(f.game.game_state, SPACE)
        after = manager.build_space_runtime_data("CH2_CORRIDOR", self.screen)
        self.assertEqual(after["object_rects"]["ch2_terminal"], pygame.Rect(300, 220, 200, 160))
        self.assertEqual(after["collision_rects"]["ch2_terminal_body"], pygame.Rect(320, 236, 160, 128))
        self.assertEqual(after["interaction_rects"]["ch2_terminal"], pygame.Rect(300, 216, 200, 168))
        asset = f.layout["spaces"]["CH2_CORRIDOR"]["objects"]["ch2_terminal"]["asset"]
        self.assertIsNotNone(f.game_ui.load_image(asset))
        self.assertIn("door_d", f.layout["spaces"]["CH2_CORRIDOR"]["objects"])
        self.assertNotIn("door_d", after["object_rects"])
        self.assertNotIn("door_d", after["interaction_rects"])
        f.game.enter_space("T3")
        f.story.return_to_chapter2_corridor()
        self.assertNotEqual(f.game.game_state, DIALOGUE)

    def test_terminal_render_caches_transparency_without_changing_original(self):
        f = self.f
        terminal = f.layout["spaces"]["CH2_CORRIDOR"]["objects"]["ch2_terminal"]
        self.assertIs(terminal["remove_white_background"], True)
        threshold = terminal["white_background_threshold"]
        asset = terminal["asset"]
        gui = f.game_ui
        original = gui.load_image(asset)
        original_bytes = pygame.image.tobytes(original, "RGBA")

        with patch.object(gui, "remove_near_white_background", wraps=gui.remove_near_white_background) as process:
            gui.draw_space(self.screen, f.game, (0, 0))
            process.assert_not_called()
            f.game.complete_event("scene_13_started")
            gui.draw_space(self.screen, f.game, (0, 0))
            gui.draw_space(self.screen, f.game, (0, 0))
            process.assert_called_once_with(original, threshold)

        processed = gui.load_asset_without_white_background(asset, threshold)
        self.assertIsNot(processed, original)
        self.assertIs(gui.load_asset_without_white_background(asset, threshold), processed)
        self.assertLess(pygame.mask.from_surface(processed, 0).count(),
                        pygame.mask.from_surface(original, 0).count())
        self.assertGreater(pygame.mask.from_surface(processed, 0).count(), 0)
        self.assertIs(gui.load_image(asset), original)
        self.assertEqual(pygame.image.tobytes(original, "RGBA"), original_bytes)

    def test_white_removal_only_changes_alpha_at_threshold(self):
        image = pygame.Surface((3, 1), pygame.SRCALPHA)
        colors = [(245, 250, 255, 255), (255, 244, 255, 255), (40, 80, 120, 150)]
        for x, color in enumerate(colors):
            image.set_at((x, 0), color)
        processed = self.f.game_ui.remove_near_white_background(image)
        self.assertEqual([tuple(processed.get_at((x, 0))) for x in range(3)],
                         [(245, 250, 255, 0), *colors[1:]])
        self.assertEqual([tuple(image.get_at((x, 0))) for x in range(3)], colors)

    def test_drag_returns_wrong_or_blank_and_retains_correct_on_reopen(self):
        f = self.f
        f.open("ch2_terminal")
        attempts = copy.deepcopy(f.game.puzzle_attempts)
        self.drag("past_fragment", "future")
        self.assertIsNone(f.puzzle.anchor_slots["past"])
        self.drag("past_fragment")
        self.assertFalse(f.puzzle.anchor_fragment_positions)
        self.drag("past_fragment", "past")
        f.click("close")
        f.open("ch2_terminal")
        self.assertEqual(f.puzzle.anchor_slots["past"], "past_fragment")
        self.assertNotIn("fragment:past_fragment", f.ui.draw(self.screen, (0, 0)))
        self.assertEqual(f.game.puzzle_attempts, attempts)
        self.assertTrue(f.game.has_item("past_fragment"))

    def test_slots_round_trip_old_save_defaults_and_age_input_transient(self):
        f = self.f
        f.open("ch2_terminal")
        self.drag("past_fragment", "past")
        f.puzzle.multi_input = {"past": "4", "present": "7", "future": "1"}
        with patch("save_manager._write_slot") as write:
            save_manager.save_game(f.game, 1)
            payload = json.dumps(write.call_args.args[1])
        saved = json.loads(payload)
        self.assertEqual(saved["scene13_anchor_slots"]["past"], "past_fragment")
        self.assertNotIn("multi_input", saved)
        restored = GameManager()
        reference = restored.scene13_anchor_slots
        with patch("save_manager._read_slot", return_value=json.loads(payload)):
            self.assertTrue(save_manager.load_game(restored, 1))
        self.assertIs(restored.scene13_anchor_slots, reference)
        f.build(restored)
        self.assertEqual(f.puzzle.anchor_slots["past"], "past_fragment")
        self.assertEqual(f.puzzle.multi_input, {})
        del saved["scene13_anchor_slots"]
        with patch("save_manager._read_slot", return_value=saved):
            self.assertTrue(save_manager.load_game(restored, 1))
        self.assertEqual(f.puzzle.anchor_slots, {"past": None, "present": None, "future": None})
        restored.scene13_anchor_slots["past"] = "past_fragment"
        restored.reset_game()
        self.assertEqual(f.puzzle.anchor_slots, {"past": None, "present": None, "future": None})

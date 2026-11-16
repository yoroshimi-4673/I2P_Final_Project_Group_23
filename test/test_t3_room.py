"""T-3 搜尋、容器子道具、固定 NPC 與既有狀態持久化。"""
import copy
import ast
import json
import os
from pathlib import Path
import unittest
from unittest.mock import mock_open, patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame

import test_chapter2_flow as flow
from managers.game_manager import GameManager
from managers.map_manager import MapManager
import save_manager


class T3RoomTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.font.init()
        pygame.display.init()
        cls.screen = pygame.display.set_mode((800, 600))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        self.f = flow.Chapter2FlowTests()
        self.f.screen = self.screen
        self.f.setUp()
        self.f.game.enter_space("T3")
        self.f.game.current_scene = "scene_12_t3"

    def search(self, object_id):
        self.f.open(object_id)
        self.f.expect_dialogue("scene_12_wrong_search")
        self.assertFalse(self.f.ui.is_open())
        self.f.finish()

    def test_desk_collects_child_only_after_dialogue_and_never_duplicates(self):
        g = self.f.game
        self.f.open("t3_knife")
        self.assertFalse(g.has_item("t3_knife"))
        self.f.ui.close()
        self.f.open("t3_desk")
        self.f.expect_dialogue("scene_12_wrong_search")
        self.assertFalse(g.has_item("t3_knife"))
        self.f.finish()
        self.assertEqual(self.f.ui.mode, "item_notification")
        self.assertTrue(g.has_item("t3_knife"))
        self.assertTrue(g.has_discovered_item("t3_knife"))
        self.assertTrue(g.has_event("t3_desk_searched"))
        self.f.click("ok")
        self.assertEqual(self.f.ui.mode, "container")
        self.assertEqual(self.f.ui.current_object_id, "t3_desk")
        self.search("t3_desk")
        self.assertEqual(self.f.ui.mode, "message")
        self.assertIn("已經被拿走", self.f.ui.result["description"])
        self.assertEqual(g.inventory.count("t3_knife"), 1)
        g.remove_item("t3_knife")
        self.search("t3_desk")
        self.assertFalse(g.has_item("t3_knife"))

    def test_wrong_searches_never_change_attempts_and_window_reveals_box(self):
        self.f.game.puzzle_attempts = {"chapter1_password": 2, "t3_time_capsule": 1}
        before = copy.deepcopy(self.f.game.puzzle_attempts)
        for object_id in ("t3_bed", "t3_desk", "t3_wardrobe"):
            self.search(object_id)
            self.assertEqual(self.f.game.puzzle_attempts, before)
            self.assertTrue(self.f.game.has_event(object_id + "_searched"))
            self.f.ui.close()
        self.f.open("t3_windowsill")
        self.assertTrue(self.f.game.has_event("t3_time_capsule_found"))
        self.assertTrue(self.f.game.has_event("t3_windowsill_searched"))
        self.assertEqual(self.f.game.puzzle_attempts, before)

    def test_bed_child_carving_needs_knife_capsule_and_knowledge(self):
        self.search("t3_bed")
        self.assertEqual(self.f.ui.mode, "container")
        self.f.click("t3_bed_board")
        self.assertFalse(self.f.game.has_event("t3_0347_carved"))
        self.f.game.complete_event("t3_capsule_opened")
        self.search("t3_bed")
        self.f.click("t3_bed_board")
        self.assertEqual(self.f.ui.mode, "message")
        self.search("t3_desk")
        self.search("t3_bed")
        self.f.click("t3_bed_board")
        self.assertFalse(self.f.game.has_event("t3_0347_carved"))
        self.f.game.learn_knowledge("number_0347")
        self.search("t3_bed")
        self.f.click("t3_bed_board")
        self.f.expect_dialogue("scene_12_carving")
        self.assertTrue(self.f.game.has_event("t3_0347_carved"))
        self.assertTrue(self.f.game.has_event("t3_completed"))
        self.assertTrue(self.f.game.has_item("t3_knife"))

    def test_existing_save_state_retains_search_knife_carving_and_puzzle(self):
        self.search("t3_desk")
        g = self.f.game
        g.learn_knowledge("number_0347")
        g.complete_event("t3_capsule_opened")
        g.solve_puzzle("t3_time_capsule")
        g.add_item("past_fragment")
        self.search("t3_bed")
        self.f.click("t3_bed_board")
        self.f.finish()
        writer = mock_open()
        with patch("builtins.open", writer):
            save_manager.save_game(g)
        payload = "".join(call.args[0] for call in writer().write.call_args_list)
        restored = GameManager()
        with patch("builtins.open", mock_open(read_data=payload)):
            self.assertTrue(save_manager.load_game(restored))
        self.f.build(restored)
        self.search("t3_desk")
        self.assertEqual(self.f.ui.mode, "message")
        self.assertEqual(restored.inventory.count("t3_knife"), 1)
        self.assertTrue(restored.has_event("t3_0347_carved"))
        self.assertTrue(restored.is_puzzle_solved("t3_time_capsule"))
        self.assertTrue(restored.has_knowledge("number_0347"))
        self.assertTrue(restored.has_item("past_fragment"))

    def test_world_layout_assets_and_first_npc_frame(self):
        gui = self.f.game_ui
        room = self.f.layout["spaces"]["T3"]
        manager = MapManager(copy.deepcopy(self.f.layout), gui)
        for size in ((800, 600), (640, 480), (1280, 720)):
            surface = pygame.Surface(size)
            runtime = manager.build_space_runtime_data("T3", surface)
            self.assertNotIn("t3_knife", runtime["object_rects"])
            self.assertNotIn("t3_bed_board", runtime["object_rects"])
            self.assertNotIn("young_li_nian", runtime["interaction_rects"])
            self.assertIn("t3_windowsill", runtime["interaction_rects"])
            self.assertEqual(set(runtime["collision_rects"]), {
                "t3_bed_body", "t3_wardrobe_body", "t3_desk_body"
            })
            for object_id in ("t3_bed", "t3_wardrobe", "t3_desk"):
                layout = room["objects"][object_id]
                target = gui.scale_rect(surface, layout)
                image = gui.load_image(layout["asset"])
                expected = gui.scale_image_to_fit(image, target).get_rect(center=target.center)
                self.assertEqual(runtime["collision_rects"][object_id + "_body"], expected)
            self.assertEqual(room["objects"]["t3_windowsill"]["x"], 286)
            gui.draw_space(surface, self.f.game, (0, 0))
        npc = room["decorations"]["young_li_nian"]
        sheet = gui.load_image(npc["asset"])
        self.assertEqual(sheet.get_size(), (64, 51))
        key = ("decoration_frame", npc["asset"], 4, 3, 0, 0)
        frame = gui.image_cache[key]
        self.assertEqual(frame.get_size(), (16, 17))
        expected = sheet.subsurface(pygame.Rect(0, 0, 16, 17))
        self.assertEqual(pygame.image.tobytes(frame, "RGBA"), pygame.image.tobytes(expected, "RGBA"))
        self.assertIs(frame, gui.image_cache[key])
        for obj in room["objects"].values():
            if obj.get("asset"):
                self.assertTrue((flow.ROOT / obj["asset"]).is_file())
        self.assertFalse(gui.draw_decoration(self.screen, {
            "asset": None, "sprite_sheet": {"columns": 4, "rows": 3}
        }, pygame.Rect(0, 0, 55, 75)))
        self.assertFalse(gui.draw_decoration(self.screen, {
            "asset": "missing_npc.png", "sprite_sheet": {"columns": 4, "rows": 3}
        }, pygame.Rect(0, 0, 55, 75)))

    def test_capsule_is_hidden_until_window_interaction(self):
        gui = self.f.game_ui
        g = self.f.game
        manager = MapManager(copy.deepcopy(self.f.layout), gui)
        runtime = manager.build_space_runtime_data("T3", self.screen)
        source = ast.parse((flow.ROOT / "game_home.py").read_text(encoding="utf-8"))
        function = next(node for node in source.body if isinstance(node, ast.FunctionDef)
                        and node.name == "get_nearest_interaction_target")
        from types import SimpleNamespace
        namespace = {
            "pygame": pygame, "game": g, "ui_layout": self.f.layout,
            "player": SimpleNamespace(rect=pygame.Rect(350, 130, 20, 20)),
            "is_in_interaction_region": lambda *args: True
        }
        exec(compile(ast.Module(body=[function], type_ignores=[]), "game_home.py", "exec"), namespace)
        rects = {"t3_time_capsule": runtime["object_rects"]["t3_time_capsule"]}
        get_target = namespace["get_nearest_interaction_target"]
        self.assertIsNone(get_target(rects, rects))
        self.assertNotIn("t3_time_capsule", gui.draw_space(self.screen, g, (350, 130)))
        self.f.open("t3_windowsill")
        self.assertTrue(g.has_event("t3_time_capsule_found"))
        self.assertIn("t3_time_capsule", gui.draw_space(self.screen, g, (350, 130)))
        self.assertEqual(get_target(rects, rects)["id"], "t3_time_capsule")


if __name__ == "__main__":
    unittest.main()

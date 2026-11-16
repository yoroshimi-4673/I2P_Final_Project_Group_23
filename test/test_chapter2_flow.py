"""第一章結尾至第二章的流程與資料一致性回歸。"""
import ast
import copy
import json
import os
from pathlib import Path
import types
import unittest
from unittest.mock import Mock, patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame

from controllers.interaction_controller import InteractionController
from controllers.puzzle_controller import PuzzleController
from game_states import DIALOGUE, GAME_OVER, PASSWORD, SPACE
from managers.game_manager import GameManager
from managers.map_manager import MapManager
from managers.puzzle_manager import PuzzleManager
from managers.story_manager import StoryManager
from ui.game_ui import GameUI
from ui.interaction_ui import InteractionUI

ROOT = Path(__file__).resolve().parent.parent


def load_data(name):
    return json.loads((ROOT / "data" / (name + ".json")).read_text(encoding="utf-8"))


def home_function(name, namespace):
    # 僅載入正式函式，避免測試啟動遊戲常駐迴圈
    tree = ast.parse((ROOT / "game_home.py").read_text(encoding="utf-8"))
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
    exec(compile(ast.Module(body=[node], type_ignores=[]), "<game_home>", "exec"), namespace)
    return namespace[name]


class Chapter2FlowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.font.init()
        pygame.display.init()
        cls.screen = pygame.display.set_mode((800, 600))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        self.objects = load_data("objects")
        self.puzzles = load_data("puzzles")
        self.dialogues = load_data("dialogue")
        self.layout = load_data("ui_layout")
        self.build(GameManager())

    def build(self, game):
        self.game = game
        self.dialogue = Mock()
        self.story = StoryManager(game, self.dialogue, Mock(), self.dialogues)
        self.manager = PuzzleManager(game, self.puzzles, self.objects)
        self.puzzle = PuzzleController(self.manager)
        self.game_ui = GameUI(self.layout, load_data("levels"), self.objects)
        self.ui = InteractionUI(self.game_ui, game, self.objects, self.game_ui.levels, self.puzzle)
        self.interaction = InteractionController(self.ui, self.story, game, self.puzzle)
        self.finish = home_function("finish_dialogue_and_open_ready_puzzle", {
            "game": game, "story_manager": self.story,
            "interaction_controller": self.interaction, "SPACE": SPACE
        })

    def open(self, object_id):
        # pending Rect 不在此測試猜測，直接呼叫 E 所用入口
        self.interaction.open_object(object_id)

    def click(self, control):
        buttons = self.ui.draw(self.screen, (0, 0))
        self.assertIn(control, buttons)
        self.interaction.handle_click(buttons, buttons[control].center)

    def expect_dialogue(self, name):
        self.assertEqual(self.game.game_state, DIALOGUE)
        self.assertEqual(self.dialogue.start.call_args.args[0], name)

    def password(self, object_id, answer):
        self.open(object_id)
        for digit in answer:
            self.click(digit)
        self.click("submit")


    def enter_chapter2_from_chapter1_exit(self):
        self.game.enter_space("C")
        self.game.complete_event("photo_back_seen")
        self.open("exit_door")
        self.assertEqual(self.ui.mode, "door")
        self.click("enter")
        self.expect_dialogue("chapter_1_end")
        self.assertEqual(self.story.dialogue_after_action, "start_chapter2")
        self.assertFalse(self.ui.is_open())
        self.finish()
        self.assertEqual(self.game.chapter, 2)
        self.assertEqual(self.game.current_scene, "scene_09_corridor")
        self.assertEqual(self.game.current_space, "CH2_CORRIDOR")
        self.expect_dialogue("scene_09_entry")
        self.assertTrue(self.game.has_event("t0_unlocked"))

    def test_chapter_transition_preserves_existing_progress(self):
        self.game.add_item("photo_1")
        self.game.add_item("fragment_1")
        self.game.solve_puzzle("chapter1_password")
        self.game.complete_event("chapter1_password_solved")
        self.game.learn_knowledge("existing_knowledge")
        self.game.play_time = 321
        inventory = list(self.game.inventory)
        puzzles = list(self.game.solved_puzzles)
        knowledge = list(self.game.knowledge)
        session_start = self.game.session_start
        self.enter_chapter2_from_chapter1_exit()
        self.assertEqual(self.game.inventory, inventory)
        self.assertEqual(self.game.solved_puzzles, puzzles)
        self.assertEqual(self.game.knowledge, knowledge)
        self.assertTrue(self.game.has_event("photo_back_seen"))
        self.assertTrue(self.game.has_event("chapter1_password_solved"))
        self.assertEqual(self.game.play_time, 321)
        self.assertEqual(self.game.session_start, session_start)
        self.finish()
        self.assertEqual(self.game.game_state, SPACE)
        self.assertEqual(self.game.current_scene, "scene_09_corridor")
        self.assertEqual(self.game.current_space, "CH2_CORRIDOR")
        self.assertEqual(self.story.chapter_end_text,
                         "你只解開了一把鎖。但你還沒解開自己。")

    def test_chapter1_end_to_scene13(self):
        g = self.game
        for name in ("current_scene", "current_space", "inventory", "knowledge",
                     "story_events", "solved_puzzles", "puzzle_attempts"):
            self.assertTrue(hasattr(g, name))
        self.enter_chapter2_from_chapter1_exit()
        self.expect_dialogue("scene_09_entry")
        self.assertTrue(g.has_event("t0_unlocked"))
        self.assertFalse(g.has_event("t7_unlocked"))
        self.assertFalse(g.has_event("t3_unlocked"))
        self.finish()
        self.open("ch2_terminal")
        self.expect_dialogue("scene_09_terminal")
        self.finish()
        for door, label in (("door_t7", "T+7"), ("door_t3", "T-3")):
            self.open(door)
            self.assertEqual(self.dialogue.start.call_args.args[1][0]["text"], label)
            self.assertEqual(len(self.dialogue.start.call_args.args[1]), 2)
            self.finish()
            self.assertEqual(g.current_space, "CH2_CORRIDOR")
        self.open("door_t0")
        self.assertEqual(g.current_space, "CH2_CORRIDOR")
        self.finish()
        self.expect_dialogue("scene_10_entry")
        self.finish()
        self.open("t0_height_marks")
        self.assertEqual(self.ui.mode, "inspectable")
        self.click("back")
        self.password("t0_bedside_drawer", "121")
        self.assertTrue(g.has_item("pencil"))
        self.assertTrue(g.has_item("t0_diary_page_4"))
        self.ui.close()
        self.open("t0_bed")
        self.click("t0_pillow")
        self.click("yes")
        self.click("ok")
        self.ui.close()
        self.assertTrue(g.has_item("t0_diary_page_2"))
        g = self.game
        self.open("t0_curtain")
        self.click("yes")
        self.click("ok")
        self.open("t0_diary")
        for page in (2, 4, 5):
            self.click(f"page:t0_diary_page_{page}")
        self.click("submit")
        self.assertTrue(g.is_puzzle_solved("t0_diary_restore"))
        self.password("t0_child_safe", "21")
        self.expect_dialogue("scene_10_fragment")
        self.assertTrue(g.has_item("present_fragment"))
        self.assertTrue(g.has_item("rubbing_paper"))
        self.finish()
        self.assertEqual(g.current_space, "T0")
        self.assertTrue(g.has_event("t0_completed"))
        self.open("t0_exit_door")
        self.open("door_t7")
        self.finish()
        self.expect_dialogue("scene_11_entry")
        self.finish()
        for missing in ("pencil", "rubbing_paper"):
            g.remove_item(missing)
            self.open("t7_broken_bed")
            self.assertEqual(self.ui.mode, "message")
            self.assertFalse(g.has_knowledge("number_0347"))
            g.add_item(missing)
        self.open("t7_broken_bed")
        self.expect_dialogue("scene_11_rubbing")
        self.finish()
        self.open("t7_letter")
        self.assertEqual(self.ui.mode, "readable")
        self.click("close")
        self.expect_dialogue("scene_11_letter")
        self.finish()
        g = self.game
        self.assertTrue(g.has_knowledge("number_0347"))
        self.assertTrue(g.has_knowledge("future_age_14"))
        letter_dialogue_count = self.dialogue.start.call_count
        self.open("t7_letter")
        self.click("close")
        self.assertEqual(self.dialogue.start.call_count, letter_dialogue_count)
        self.password("t7_desk_drawer", "307")
        self.expect_dialogue("scene_11_fragment")
        self.finish()
        self.assertEqual(g.current_space, "T7")
        self.open("t7_exit_door")
        g.add_item("t7_letter")
        self.open("door_t3")
        self.finish()
        self.expect_dialogue("scene_12_warning")
        self.assertEqual(g.current_space, "CH2_CORRIDOR")
        self.finish()
        self.expect_dialogue("scene_12_entry")
        self.assertEqual(g.current_space, "T3")
        for item in ("pencil", "rubbing_paper", "t7_letter"):
            self.assertFalse(g.has_item(item))
        self.assertTrue(g.has_knowledge("number_0347"))
        for item in ("present_fragment", "future_fragment"):
            self.assertTrue(g.has_item(item))
        self.finish()
        for object_id in ("t3_bed", "t3_desk", "t3_wardrobe"):
            self.open(object_id)
            self.assertEqual(self.ui.mode, "inspectable")
            self.click("back")
        self.open("t3_time_capsule")
        self.assertEqual(self.ui.mode, "message")
        self.assertIsNone(self.puzzle.current_puzzle_id)
        self.open("t3_windowsill")
        self.assertTrue(g.has_event("t3_time_capsule_found"))
        self.password("t3_time_capsule", "0347")
        self.expect_dialogue("scene_12_note")
        self.assertTrue(g.has_item("past_fragment"))
        self.assertTrue(g.has_item("t3_note"))
        self.finish()
        self.open("t3_bed_board")
        self.assertEqual(self.ui.mode, "message")
        self.open("t3_knife")
        self.assertTrue(g.has_item("t3_knife"))
        self.click("ok")
        g = self.game
        self.open("t3_bed_board")
        self.expect_dialogue("scene_12_carving")
        self.finish()
        self.assertTrue(g.has_event("t3_completed"))
        self.open("t3_exit_door")
        self.assertEqual(g.current_scene, "scene_13_anchor_terminal")
        g = self.game
        self.open("ch2_terminal")
        self.click("fragment:past_fragment")
        attempts = copy.deepcopy(g.puzzle_attempts)
        self.click("slot:present")
        self.assertEqual(self.ui.result["status"], "wrong_slot")
        self.assertEqual(g.puzzle_attempts, attempts)
        self.assertEqual(self.ui.mode, "anchor_fragments")
        for item, slot in (("past_fragment", "past"), ("present_fragment", "present"),
                           ("future_fragment", "future")):
            self.click("fragment:" + item)
            self.click("slot:" + slot)
        self.expect_dialogue("scene_13_terminal")
        self.finish()
        self.assertEqual(self.ui.mode, "multi_input")
        for field, value in (("past", "4"), ("present", "7"), ("future", "14")):
            self.click("field:" + field)
            for digit in value:
                self.click(digit)
        self.click("submit")
        self.expect_dialogue("scene_13_success")
        self.finish()
        self.assertTrue(g.has_event("anchor_verified"))
        self.assertTrue(g.has_event("space_d_unlocked"))
        self.assertEqual(g.current_space, "CH2_CORRIDOR")
        self.assertEqual(g.current_scene, "scene_13_anchor_terminal")

    def test_capsule_and_age_failure_paths(self):
        self.game.enter_space("T3")
        self.game.complete_event("t3_time_capsule_found")
        self.open("t3_time_capsule")
        self.assertEqual(self.ui.result["status"], "puzzle_unavailable")
        self.game.learn_knowledge("number_0347")
        self.open("t3_time_capsule")
        for answer, remaining in (("1111", 2), ("2222", 1), ("3333", 0)):
            for digit in answer:
                self.click(digit)
            result = self.interaction.submit_puzzle()
            self.assertEqual(result["remaining_attempts"], remaining)
        self.assertEqual(self.game.game_state, GAME_OVER)
        self.assertEqual(self.game.game_over_reason, "time_loop_broken")
        self.build(GameManager())
        self.game.enter_space("CH2_CORRIDOR")
        self.game.current_scene = "scene_13_anchor_terminal"
        for item in ("past_fragment", "present_fragment", "future_fragment"):
            self.game.add_item(item)
        self.game.complete_event("anchor_age_puzzle_ready")
        self.open("ch2_terminal")
        self.assertEqual(self.manager.get_failure_stage("anchor_age_verification"), "far")
        for field, value in (("past", "4"), ("present", "7"), ("future", "13")):
            self.puzzle.set_active_field(field)
            self.puzzle.append_input(value)
        for stage in ("middle", "near", "consumed"):
            self.interaction.submit_puzzle()
            self.assertEqual(self.manager.get_failure_stage("anchor_age_verification"), stage)
        self.assertEqual(self.game.game_state, GAME_OVER)
        self.assertEqual(self.game.game_over_reason, "white_wall_consumed_corridor")


    def test_background_render_and_anonymous_interaction_prompt(self):
        layout = copy.deepcopy(self.layout)
        layout["spaces"]["T3"]["objects"]["test_background_object"] = {
            "x": 500, "y": 400, "width": 100, "height": 100,
            "render_mode": "background", "interaction_padding": 40,
            "asset": "fake.png", "overlay_asset": "fake_overlay.png"
        }
        ui = GameUI(layout, self.game_ui.levels, self.objects)
        manager = MapManager(copy.deepcopy(layout), ui)
        self.game.enter_space("T3")
        with patch.object(ui, "draw_asset", wraps=ui.draw_asset) as asset, \
                patch.object(ui, "draw_placeholder_rect", wraps=ui.draw_placeholder_rect) as placeholder, \
                patch.object(ui, "font_small", Mock(wraps=ui.font_small)) as font:
            rects = ui.draw_space(self.screen, self.game, (510, 410))
            self.assertIn("test_background_object", rects)
            self.assertFalse(any(call.args[1] in ("fake.png", "fake_overlay.png")
                                 for call in asset.call_args_list))
            placeholder.assert_not_called()
            font.render.assert_not_called()
        self.assertIn("test_background_object", manager.get_interaction_rects("T3", self.screen))
        spy = Mock(wraps=self.game_ui.font_small)
        fake_player = types.SimpleNamespace(rect=pygame.Rect(100, 100, 40, 40))
        prompt = home_function("draw_interaction_prompt", {
            "pygame": pygame, "objects": self.objects, "ui_layout": layout,
            "game": self.game, "game_ui": types.SimpleNamespace(font_small=spy),
            "player": fake_player
        })
        target = {"id": "test_background_object"}
        prompt(self.screen, target)
        self.assertEqual(spy.render.call_args.args[0], "[E] 互動")
        self.assertEqual(target["id"], "test_background_object")
        target = {"id": "t3_wardrobe"}
        prompt(self.screen, target)
        self.assertIn(self.objects["t3_wardrobe"]["name"], spy.render.call_args.args[0])

    def test_data_references_and_pending_runtime_exclusion(self):
        represented = set()
        for space, layout in self.layout["spaces"].items():
            represented.update(layout.get("objects", {}))
            represented.update(layout.get("pending_objects", {}))
            for object_id, rect in layout.get("objects", {}).items():
                self.assertIn(object_id, self.objects)
                self.assertGreater(rect["width"], 0)
                self.assertGreater(rect["height"], 0)
        for object_id, data in self.objects.items():
            if data.get("space"):
                self.assertIn(object_id, represented)
        manager = MapManager(copy.deepcopy(self.layout), self.game_ui)
        for space, layout in self.layout["spaces"].items():
            active = manager.get_object_rects(space, self.screen)
            self.assertFalse(set(active) & set(layout.get("pending_objects", {})))
        mapping = {"t0_bedside_drawer": "t0_bedside_drawer", "t0_diary": "t0_diary_restore",
                   "t0_child_safe": "t0_child_safe", "t7_desk_drawer": "t7_desk_drawer",
                   "t3_time_capsule": "t3_time_capsule"}
        for object_id, puzzle_id in mapping.items():
            self.assertEqual(self.objects[object_id]["puzzle_id"], puzzle_id)
            self.assertIn(puzzle_id, self.puzzles)
        self.assertIn("anchor_age_verification", self.puzzles)
        tree = ast.parse((ROOT / "managers/story_manager.py").read_text(encoding="utf-8"))
        ids = [n.args[0].value for n in ast.walk(tree) if isinstance(n, ast.Call)
               and isinstance(n.func, ast.Attribute) and n.func.attr == "start_dialogue"
               and n.args and isinstance(n.args[0], ast.Constant)]
        for dialogue_id in ids:
            self.assertIn(dialogue_id, self.dialogues)


if __name__ == "__main__":
    unittest.main()

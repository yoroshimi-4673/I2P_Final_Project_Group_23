"""D 門解鎖、Scene 14 對話與第二章結束流程。"""

import unittest
from unittest.mock import Mock, patch

import pygame
import test_chapter2_flow as flow
from game_states import DIALOGUE, SPACE, SUCCESS
from managers.interaction_manager import enter_door
from managers.map_manager import MapManager
from managers.interaction_target_manager import InteractionTargetManager
from player import Player
from ui.dialogue_ui import DialogueController


class Scene14Tests(unittest.TestCase):
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
        self.f.game.enter_space("CH2_CORRIDOR")
        self.f.game.current_scene = "scene_13_anchor_terminal"

    def test_unlock_controls_visibility_and_exact_polygon(self):
        f = self.f
        corridor = f.layout["spaces"]["CH2_CORRIDOR"]
        door = corridor["objects"]["door_d"]
        self.assertNotIn("door_d", corridor.get("pending_objects", {}))
        self.assertNotIn("D", f.layout["spaces"])
        self.assertEqual(door["interaction_polygon"], [[627, 234], [627, 324], [657, 324], [657, 231]])
        self.assertEqual(door["interaction_label"], "前往D空間")
        manager = MapManager(f.layout, f.game_ui, f.game)
        before = manager.build_space_runtime_data("CH2_CORRIDOR", self.screen)
        for key in ("object_rects", "interaction_rects"):
            self.assertNotIn("door_d", before[key])
        self.assertNotIn("door_d", f.game_ui.draw_space(self.screen, f.game, (0, 0)))
        self.assertEqual(enter_door(f.game, "door_d", f.objects)["status"], "door_locked")
        f.game.complete_event("space_d_unlocked")
        self.assertIn("door_d", f.game_ui.draw_space(self.screen, f.game, (0, 0)))
        for size in ((800, 600), (1280, 720)):
            with self.subTest(size=size):
                screen = pygame.Surface(size)
                runtime = manager.build_space_runtime_data("CH2_CORRIDOR", screen)
                self.assertEqual(runtime["interaction_rects"]["door_d"], f.game_ui.scale_rect(screen, door))
                player = Player(0, 0, width=f.game_ui.scale_x(screen, 60), height=f.game_ui.scale_y(screen, 75))
                player.rect.center = (f.game_ui.scale_x(screen, 605), f.game_ui.scale_y(screen, 270))
                player.direction = 1
                self.assertTrue(player.is_inside_walkable_polygon(runtime["walkable_polygon"]))
                targets = InteractionTargetManager(f.layout, f.game_ui, f.game)
                target = targets.get_interaction_target(
                    player, "CH2_CORRIDOR", runtime["object_rects"], runtime["interaction_rects"], screen
                )
                self.assertEqual(target["id"], "door_d")

    def test_d_door_prompt_uses_layout_text(self):
        f = self.f
        f.game.complete_event("space_d_unlocked")
        font = Mock(wraps=f.game_ui.font_small)
        player = Player(575, 233, width=60, height=75)
        prompt = flow.home_function("draw_interaction_prompt", {
            "pygame": pygame, "objects": f.objects, "ui_layout": f.layout,
            "game": f.game, "game_ui": f.game_ui, "player": player,
        })
        with patch.object(f.game_ui, "font_small", font):
            prompt(self.screen, {"id": "door_d"})
        self.assertEqual(font.render.call_args.args[0], "[E] 互動：前往D空間")

    def test_door_confirmation_runs_four_lines_then_finishes_chapter(self):
        f = self.f
        f.game.complete_event("space_d_unlocked")
        self.assertEqual(enter_door(f.game, "door_d", f.objects), {
            "status": "scene_transition", "object_id": "door_d", "target_scene": "scene_14",
        })
        self.assertEqual(f.game.game_state, SPACE)
        dialogue = DialogueController()
        f.story.dialogue_controller = dialogue
        f.open("door_d")
        self.assertEqual(f.ui.mode, "door")
        with patch.object(f.story, "start_scene_14", wraps=f.story.start_scene_14) as start:
            f.click("enter")
            start.assert_called_once_with()
        self.assertFalse(f.ui.is_open())
        self.assertEqual((f.game.current_scene, f.game.current_space, f.game.game_state),
                         ("scene_14", None, DIALOGUE))
        self.assertEqual(dialogue.dialogue_id, "scene_14")
        lines = [
            ("系統", "空間 D — 收斂率 100%"),
            ("系統", "錨點：已鎖定"),
            ("黎念", "……六十一、六十二、六十三……"),
            ("黎琛", "她還在數。"),
        ]
        for index, expected in enumerate(lines):
            line = dialogue.get_current_line()
            self.assertEqual((line["speaker"], line["text"]), expected)
            dialogue.complete_current_line()
            self.assertEqual(dialogue.advance(), "next_line" if index < 3 else "dialogue_finished")
        f.finish()
        self.assertEqual(f.game.chapter, 2)
        self.assertTrue(f.game.has_event("chapter_2_completed"))
        self.assertEqual((f.game.current_scene, f.game.current_space, f.game.game_state),
                         ("chapter_2_end", None, SUCCESS))

    def test_dark_scene_and_success_screen(self):
        f = self.f
        f.story.start_scene_14()
        game_ui = Mock()
        player = Mock()
        draw = flow.home_function("draw_dialogue_background", {
            "game": f.game, "game_ui": game_ui, "player": player,
            "dialogue_controller": Mock(dialogue_id="scene_14"),
        })
        background = pygame.Surface(self.screen.get_size())
        draw(background, (0, 0))
        self.assertEqual(background.get_at((0, 0))[:3], (12, 22, 48))
        player.draw.assert_not_called()
        game_ui.draw_space.assert_not_called()
        f.finish()
        with (
            patch.object(f.game_ui, "draw_button", wraps=f.game_ui.draw_button) as draw_button,
            patch.object(f.game_ui, "font_title", Mock(wraps=f.game_ui.font_title)) as title,
            patch.object(f.game_ui, "font_ui", Mock(wraps=f.game_ui.font_ui)) as summary,
        ):
            buttons = f.game_ui.draw_success_end(self.screen, (0, 0))
            self.assertEqual(set(buttons), {"settings", "menu"})
            self.assertEqual([call.args[1] for call in draw_button.call_args_list], ["設定", "回到主畫面"])
            self.assertEqual(title.render.call_args.args[0], "結束資訊")
            self.assertEqual(summary.render.call_args_list[0].args[0], "Chapter 2 已完成。")

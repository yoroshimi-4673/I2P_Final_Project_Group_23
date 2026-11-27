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

from controllers.hotbar_controller import HotbarController
from controllers.interaction_controller import InteractionController
from controllers.puzzle_controller import PuzzleController
from game_states import DIALOGUE, GAME_OVER, PASSWORD, SPACE
from managers.game_manager import GameManager
from managers.map_manager import MapManager
from managers.puzzle_manager import PuzzleManager
from managers.story_manager import StoryManager
from player import Player
import save_manager
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

    def click_circuit_tile(self, position):
        buttons = self.ui.draw(self.screen, (0, 0))
        self.interaction.handle_click(buttons, buttons["_tiles"][position].center)

    def solve_circuit(self):
        rotations = {
            (4, 1): 3, (3, 1): 1, (3, 3): 3, (2, 3): 2,
            (1, 1): 1, (1, 3): 1, (1, 5): 1, (1, 6): 2,
            (2, 6): 3, (2, 5): 1, (3, 5): 0, (4, 6): 0,
            (4, 8): 3, (3, 8): 1, (3, 9): 3, (2, 9): 0,
            (1, 8): 0, (0, 8): 1,
        }
        for position, expected in rotations.items():
            current = self.puzzle.circuit_tiles[position]["rotation"]
            for _ in range((expected - current) % 4):
                self.click_circuit_tile(position)

    def test_t7_circuit_draw_reset_exit_and_reentry(self):
        self.game.complete_event("t7_unlocked")
        self.assertTrue(self.story.enter_t7())
        self.expect_dialogue("scene_11_circuit_intro")
        self.finish()
        self.assertEqual((self.puzzle.current_puzzle_id, self.ui.mode), ("t7_circuit", "circuit"))
        buttons = self.ui.draw(self.screen, (0, 0))
        self.assertEqual(len(buttons["_tiles"]), 28)
        self.assertEqual(buttons["_tiles"][(4, 0)], pygame.Rect(75, 339, 66, 66))
        self.assertEqual(buttons["_tiles"][(0, 8)].right, buttons["_tiles"][(0, 9)].left)
        self.assertEqual(set(self.interaction.get_interaction_rect_buttons(buttons)), {"reset", "leave"})
        tile = (4, 1)
        self.click_circuit_tile(tile)
        self.assertEqual(self.puzzle.circuit_tiles[tile]["rotation"], 1)
        self.click("reset")
        self.assertEqual(self.puzzle.circuit_tiles[tile]["rotation"], 0)
        self.click_circuit_tile(tile)
        self.interaction.handle_key(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_r))
        self.assertEqual(self.puzzle.circuit_tiles[tile]["rotation"], 0)
        self.click_circuit_tile(tile)
        escape = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)
        self.interaction.handle_key(escape)
        self.assertEqual(self.ui.mode, "circuit_exit_confirmation")
        self.assertEqual(set(self.ui.draw(self.screen, (0, 0))), {"continue", "leave"})
        self.interaction.handle_key(escape)
        self.assertEqual(self.ui.mode, "circuit")
        self.assertEqual(self.puzzle.circuit_tiles[tile]["rotation"], 1)
        self.click("leave")
        self.click("continue")
        self.assertEqual(self.ui.mode, "circuit")
        self.click("leave")
        self.click("leave")
        self.assertEqual(self.game.current_space, "CH2_CORRIDOR")
        self.assertEqual(self.interaction.pending_entry_object, "door_t7")
        self.assertFalse(self.puzzle.circuit_tiles)
        self.assertIsNone(self.puzzle.current_puzzle_id)
        self.story.enter_t7()
        self.expect_dialogue("scene_11_circuit_intro")
        self.finish()
        self.assertEqual(self.puzzle.circuit_tiles[tile]["rotation"], 0)

    def test_t7_circuit_completion_lights_room_and_survives_save_load(self):
        self.game.complete_event("t7_unlocked")
        self.story.enter_t7()
        overlay = home_function("draw_t7_power_outage_overlay", {"game": self.game, "pygame": pygame})
        surface = pygame.Surface((2, 2))
        surface.fill("white")
        overlay(surface)
        self.assertEqual(surface.get_at((0, 0))[:3], (51, 51, 51))
        self.finish()
        self.solve_circuit()
        self.assertTrue(self.game.has_event("t7_circuit_completed"))
        self.assertTrue(self.game.is_puzzle_solved("t7_circuit"))
        self.assertFalse(self.ui.is_open())
        self.expect_dialogue("scene_11_entry")
        surface.fill("white")
        overlay(surface)
        self.assertEqual(surface.get_at((0, 0))[:3], (255, 255, 255))
        self.finish()

        with patch("save_manager._write_slot") as write:
            save_manager.save_game(self.game, 1)
            saved = json.loads(json.dumps(write.call_args.args[1]))
        restored = GameManager()
        with patch("save_manager._read_slot", return_value=saved):
            self.assertTrue(save_manager.load_game(restored, 1))
        self.build(restored)
        self.assertTrue(restored.has_event("t7_circuit_completed"))
        self.assertTrue(restored.is_puzzle_solved("t7_circuit"))
        self.assertTrue(self.story.enter_t7())
        self.assertEqual(restored.game_state, SPACE)
        self.dialogue.start.assert_not_called()
        self.assertFalse(self.ui.is_open())

    def password(self, object_id, answer):
        self.open(object_id)
        if self.ui.mode == "dial_password":
            self.set_dial_password(answer)
            self.click("confirm")
        else:
            for digit in answer:
                self.click(digit)

    def set_dial_password(self, answer):
        for index, target in enumerate(map(int, answer)):
            steps = (target - self.puzzle.dial_digits[index]) % 10
            step = 1 if steps <= 5 else -1
            for _ in range(min(steps, 10 - steps)):
                self.click_dial(index, step)

    def click_dial(self, index, step, screen=None):
        screen = self.screen if screen is None else screen
        buttons = self.ui.dial_password_controls(screen)
        self.interaction.handle_click(buttons, buttons["_dial_regions"][index, step].center)

    def test_dial_password_wraps_and_preserves_input_until_game_reset(self):
        drawer = "t0_bedside_drawer"
        safe = "t0_child_safe"
        escape = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)
        self.game.enter_space("T0")
        self.game.solve_puzzle("t0_diary_restore")
        self.open(drawer)
        self.assertEqual(self.puzzle.dial_digits, [0, 0, 0])
        self.click_dial(0, 1)
        self.assertEqual(self.puzzle.dial_digits, [1, 0, 0])
        self.click_dial(1, -1)
        self.assertEqual(self.puzzle.dial_digits, [1, 9, 0])
        self.click_dial(1, 1)
        self.assertEqual(self.puzzle.dial_digits, [1, 0, 0])
        self.set_dial_password("120")
        self.click("confirm")
        self.assertEqual(self.ui.result["message"], "抽屜卡住了。")
        self.assertEqual(self.puzzle.dial_digits, [1, 2, 0])
        self.interaction.handle_key(escape)
        self.assertFalse(self.ui.is_open())
        self.open(safe)
        self.assertEqual(self.puzzle.dial_digits, [0, 0])
        self.click_dial(1, -1)
        self.click("back")
        self.open(drawer)
        self.assertEqual(self.puzzle.dial_digits, [1, 2, 0])
        self.interaction.handle_key(escape)
        self.open(safe)
        self.assertEqual(self.puzzle.dial_digits, [0, 9])
        self.interaction.handle_key(escape)
        self.game.reset_game()
        self.game.enter_space("T0")
        self.game.solve_puzzle("t0_diary_restore")
        self.open(drawer)
        self.assertEqual(self.puzzle.dial_digits, [0, 0, 0])
        self.ui.close()
        self.open(safe)
        self.assertEqual(self.puzzle.dial_digits, [0, 0])

    def test_dial_password_ignores_keyboard_and_reopens_solved_message(self):
        puzzle_id = "t0_bedside_drawer"
        self.game.enter_space("T0")
        self.open(puzzle_id)
        self.set_dial_password("121")
        controls = self.ui.draw(self.screen, (0, 0))
        self.assertEqual(set(controls), {"_dial_regions", "confirm", "back"})
        self.interaction.last_buttons = controls
        self.interaction.update_interaction_hover_focus(controls, controls["confirm"].center)
        keys = [
            *range(pygame.K_0, pygame.K_9 + 1), pygame.K_BACKSPACE, pygame.K_RETURN,
            pygame.K_KP_ENTER, pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT, pygame.K_TAB,
        ]
        for key in keys:
            self.interaction.handle_key(pygame.event.Event(pygame.KEYDOWN, key=key))
        self.assertEqual(self.puzzle.dial_digits, [1, 2, 1])
        self.assertFalse(self.game.is_puzzle_solved(puzzle_id))
        self.click("confirm")
        self.assertTrue(self.game.is_puzzle_solved(puzzle_id))
        self.acknowledge_success("抽屜打開了。")
        self.acknowledge_rewards("pencil", "t0_diary_page_4")
        self.open(puzzle_id)
        self.assertEqual(self.ui.mode, "message")
        self.assertEqual(self.ui.result["status"], "puzzle_solved")

    def test_dial_back_matches_escape_without_submitting_or_spending_attempts(self):
        puzzle_id = "t3_time_capsule"
        self.game.enter_space("T3")
        self.game.complete_event("t3_time_capsule_found")
        self.game.learn_knowledge("number_0347")
        self.open(puzzle_id)
        self.click("confirm")  # 先用掉一次，驗證返回也不會把剩餘次數重設。
        self.assertEqual(self.puzzle.remaining_attempts, 2)
        self.set_dial_password("0347")
        escape = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)

        with patch.object(self.puzzle, "submit", wraps=self.puzzle.submit) as submit:
            for exit_action in (lambda: self.click("back"), lambda: self.interaction.handle_key(escape)):
                self.interaction.last_buttons = self.ui.draw(self.screen, (0, 0))
                exit_action()
                submit.assert_not_called()
                self.assertFalse(self.ui.is_open())
                self.assertIsNone(self.puzzle.current_puzzle_id)
                self.assertEqual(self.interaction.last_buttons, {})
                self.assertEqual(self.game.game_state, SPACE)
                self.assertEqual(self.manager.get_remaining_attempts(puzzle_id), 2)
                self.assertFalse(self.game.is_puzzle_solved(puzzle_id))
                self.open(puzzle_id)
                self.assertEqual(self.puzzle.dial_digits, [0, 3, 4, 7])

    def test_dial_password_is_transient_across_save_and_restart(self):
        self.game.enter_space("T0")
        self.open("t0_bedside_drawer")
        self.set_dial_password("120")
        self.ui.close()
        with patch.object(save_manager, "_write_slot") as write:
            save_manager.save_game(self.game, 1)
            saved = json.loads(json.dumps(write.call_args.args[1]))
        self.open("t0_bedside_drawer")
        self.assertEqual(self.puzzle.dial_digits, [1, 2, 0])
        restored = GameManager()
        with patch.object(save_manager, "_read_slot", return_value=saved):
            self.assertTrue(save_manager.load_game(restored, 1))
        self.build(restored)
        self.open("t0_bedside_drawer")
        self.assertEqual(self.puzzle.dial_digits, [0, 0, 0])

    def test_dial_highlight_and_hit_regions_follow_scaled_art(self):
        self.game.solve_puzzle("t0_diary_restore")
        self.game.complete_event("t3_time_capsule_found")
        self.game.learn_knowledge("number_0347")
        for room, puzzle_id in (
            ("T0", "t0_bedside_drawer"), ("T0", "t0_child_safe"),
            ("T7", "t7_desk_drawer"), ("T3", "t3_time_capsule"),
        ):
            self.game.enter_space(room)
            self.open(puzzle_id)
            layout = self.layout["chapter2_password_locks"][puzzle_id]
            for size in ((800, 600), (1000, 750), (640, 480)):
                with self.subTest(puzzle=puzzle_id, size=size):
                    screen = pygame.Surface(size)
                    screen.fill((0, 0, 0))
                    buttons = self.ui.draw(screen, (0, 0))
                    regions = buttons["_dial_regions"]
                    self.assertEqual(len(regions), 2 * len(self.puzzle.dial_digits))
                    for index, slot in enumerate(layout["digit_slots"]):
                        up, down = regions[index, 1], regions[index, -1]
                        self.assertEqual(up.bottom, down.top)
                        self.assertEqual(up.union(down), self.game_ui.scale_rect(screen, slot))
                    up, down = regions[0, 1], regions[0, -1]
                    before = screen.get_at(up.center), screen.get_at(down.center)
                    screen.fill((0, 0, 0))
                    self.ui.draw(screen, up.center)
                    self.assertNotEqual(screen.get_at(up.center), before[0])
                    self.assertEqual(screen.get_at(down.center), before[1])
                    screen.fill((0, 0, 0))
                    self.ui.draw(screen, down.center)
                    self.assertEqual(screen.get_at(up.center), before[0])
                    self.assertNotEqual(screen.get_at(down.center), before[1])
                    digit = self.puzzle.dial_digits[0]
                    self.click_dial(0, 1, screen)
                    self.assertEqual(self.puzzle.dial_digits[0], (digit + 1) % 10)
                    self.click_dial(0, -1, screen)
                    self.assertEqual(self.puzzle.dial_digits[0], digit)

                    back_rect = self.game_ui.scale_rect(screen, layout["back_button"])
                    confirm_rect = self.game_ui.scale_rect(screen, layout["confirm_button"])
                    with patch.object(self.game_ui, "draw_button", wraps=self.game_ui.draw_button) as draw:
                        controls = self.ui.draw(screen, back_rect.center)
                    draw.assert_any_call(screen, "返回", back_rect, True)
                    draw.assert_any_call(screen, "確認", confirm_rect, False)
                    self.assertEqual(controls["confirm"], confirm_rect)
                    self.assertEqual(controls["back"], back_rect)
                    self.assertEqual(controls, self.ui.dial_password_controls(screen))
                    self.interaction.handle_click(controls, back_rect.center)
                    self.assertFalse(self.ui.is_open())
                    self.open(puzzle_id)
            self.ui.close()

    def acknowledge_success(self, message):
        self.assertEqual(self.ui.mode, "message")
        self.assertEqual(self.ui.result["message"], message)
        self.click("ok")

    def acknowledge_rewards(self, *items):
        for item in items:
            self.assertEqual(self.ui.mode, "item_notification")
            self.assertEqual(self.ui.notification["item_id"], item)
            self.click("ok")
        self.assertFalse(self.ui.is_open())

    def test_letter_reader_falls_back_to_thumbnail_and_discovered_letter_stays_hidden(self):
        self.game.enter_space("T7")
        letter = self.objects["t7_letter"]
        letter.pop("reader_asset")
        self.ui.open_readable("t7_letter")
        self.assertEqual(self.ui.result["asset"], letter["ui_asset"])
        self.ui.close()

        self.game.add_item("t7_letter")
        self.game.remove_item("t7_letter")
        self.open("t7_desk")
        self.assertEqual(
            [child["object_id"] for child in self.ui.result["contents"]],
            ["t7_desk_drawer"]
        )
        self.interaction.open_container_child("t7_letter")
        self.assertEqual(self.ui.mode, "container")
        self.assertFalse(self.game.has_item("t7_letter"))

    def enter_chapter2_from_chapter1_exit(self):
        self.game.enter_space("C")
        if not self.game.is_puzzle_solved("chapter1_password"):
            self.password("exit_door", "100101")
            self.click("ok")
            self.click("back")
            self.expect_dialogue("photo_back_story")
            self.finish()
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
        self.assertFalse(self.game.has_event("photo_back_seen"))
        self.assertTrue(self.game.has_event("chapter1_password_solved"))
        self.assertEqual(self.game.play_time, 321)
        self.assertEqual(self.game.session_start, session_start)
        self.finish()
        self.assertEqual(self.game.game_state, SPACE)
        self.assertEqual(self.game.current_scene, "scene_09_corridor")
        self.assertEqual(self.game.current_space, "CH2_CORRIDOR")
        self.assertEqual(self.story.chapter_end_text,
                         "你只解開了一把鎖。但你還沒解開自己。")

    def test_forced_anchor_puzzle_takes_priority_over_pending_reward(self):
        self.game.enter_space("T0")
        self.game.solve_puzzle("t0_diary_restore")
        for item in ("past_fragment", "future_fragment"):
            self.game.add_item(item)
        self.password("t0_child_safe", "21")
        self.acknowledge_success("保險箱打開了。")
        self.expect_dialogue("scene_10_fragment")
        self.game.current_space = "CH2_CORRIDOR"
        self.game.complete_event("anchor_age_puzzle_ready")
        self.finish()
        self.assertEqual(self.ui.mode, "multi_input")
        self.assertEqual(self.puzzle.current_puzzle_id, "anchor_age_verification")
        self.ui.close()
        self.interaction.resume_pending_item_notifications()
        self.acknowledge_rewards("present_fragment", "rubbing_paper")

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
        self.acknowledge_success("抽屜打開了。")
        self.acknowledge_rewards("pencil", "t0_diary_page_4")
        self.open("t0_bed")
        self.click("t0_pillow")
        self.click("yes")
        self.assertEqual((self.ui.mode, self.ui.notification["item_id"]), ("item_notification", "t0_diary_page_2"))
        self.click("ok")
        self.assertEqual(self.ui.mode, "container")
        self.ui.close()
        self.assertTrue(g.has_item("t0_diary_page_2"))
        g = self.game
        self.open("t0_windowsill")
        self.assertEqual(self.ui.mode, "searchable")
        self.click("yes")
        self.acknowledge_rewards("t0_diary_page_5")
        self.assertTrue(g.has_item("t0_diary_page_5"))
        self.open("t0_desk")
        self.click("t0_diary")
        for index, page in enumerate((2, 4, 5)):
            if index:
                self.click("diary_next_page")
            buttons = self.ui.draw(self.screen, (0, 0))
            item = f"t0_diary_page_{page}"
            rect = buttons["_drag_rects"][item]
            self.interaction.start_diary_drag(item, rect, rect.center)
            target = buttons[f"diary_slot:page_{page}"].center
            self.interaction.update_diary_drag(target)
            self.interaction.finish_diary_drag(buttons, target)
        self.click("confirm")
        self.assertTrue(g.is_puzzle_solved("t0_diary_restore"))
        self.acknowledge_success("日記頁已經按照月份恢復。")
        self.acknowledge_rewards("t0_fixed_diary")
        self.password("t0_child_safe", "21")
        self.assertTrue(g.has_item("present_fragment"))
        self.assertTrue(g.has_item("rubbing_paper"))
        self.acknowledge_success("保險箱打開了。")
        self.expect_dialogue("scene_10_fragment")
        self.interaction.resume_pending_item_notifications()
        self.assertFalse(self.ui.is_open())
        self.finish()
        self.acknowledge_rewards("present_fragment", "rubbing_paper")
        self.assertEqual(g.current_space, "T0")
        self.assertTrue(g.has_event("t0_completed"))
        self.open("t0_exit_door")
        self.click("leave")
        self.open("door_t7")
        self.finish()
        self.expect_dialogue("scene_11_circuit_intro")
        self.finish()
        self.solve_circuit()
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
        self.open("t7_desk")
        self.assertEqual(
            [child["object_id"] for child in self.ui.result["contents"]],
            ["t7_letter", "t7_desk_drawer"]
        )
        self.click("t7_letter")
        self.assertEqual(self.ui.notification["item_id"], "t7_letter")
        self.assertTrue(g.has_discovered_item("t7_letter"))
        self.assertFalse(g.has_event("t7_letter_read"))
        self.assertFalse(g.has_knowledge("future_age_14"))
        self.click("ok")
        self.assertEqual(
            [child["object_id"] for child in self.ui.result["contents"]],
            ["t7_desk_drawer"]
        )
        self.click("close")
        hotbar = HotbarController(g, self.game_ui, self.ui, self.interaction)
        hotbar.open_item("t7_letter")
        self.assertEqual(self.ui.mode, "readable")
        self.expect_dialogue("scene_11_letter")
        self.assertTrue(g.has_event("t7_letter_read"))
        self.assertEqual(self.ui.result["asset"], self.objects["t7_letter"]["reader_asset"])
        self.click("close")
        self.finish()
        g = self.game
        self.assertTrue(g.has_knowledge("number_0347"))
        self.assertTrue(g.has_knowledge("future_age_14"))
        letter_dialogue_count = self.dialogue.start.call_count
        hotbar.open_item("t7_letter")
        self.assertEqual(self.ui.mode, "readable")
        self.click("close")
        self.assertEqual(self.dialogue.start.call_count, letter_dialogue_count)
        self.open("t7_desk")
        self.click("t7_desk_drawer")
        self.assertEqual(self.puzzle.current_puzzle_id, "t7_desk_drawer")
        self.set_dial_password("307")
        self.click("confirm")
        self.acknowledge_success("書桌抽屜打開了。")
        self.expect_dialogue("scene_11_fragment")
        self.finish()
        self.acknowledge_rewards("future_fragment")
        self.assertEqual(g.current_space, "T7")
        self.open("t7_exit_door")
        self.click("leave")
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
        for object_id in ("t3_bed", "t3_wardrobe"):
            self.open(object_id)
            self.assertEqual(self.ui.mode, "container" if object_id == "t3_bed" else "inspectable")
            self.click("close" if object_id == "t3_bed" else "back")
            self.expect_dialogue("scene_12_wrong_search")
            self.finish()
        self.open("t3_time_capsule")
        self.assertEqual(self.ui.mode, "message")
        self.assertIsNone(self.puzzle.current_puzzle_id)
        self.open("t3_windowsill")
        self.assertTrue(g.has_event("t3_time_capsule_found"))
        self.password("t3_time_capsule", "0347")
        self.assertTrue(g.has_item("past_fragment"))
        self.assertTrue(g.has_item("t3_note"))
        self.acknowledge_success("鐵盒打開了。")
        self.expect_dialogue("scene_12_note")
        self.finish()
        self.acknowledge_rewards("past_fragment", "t3_note")
        self.open("t3_bed_board")
        self.assertEqual(self.ui.mode, "message")
        self.click("ok")
        self.open("t3_desk")
        self.click("t3_knife")
        self.assertEqual((self.ui.mode, self.ui.notification["item_id"]), ("item_notification", "t3_knife"))
        self.assertTrue(g.has_item("t3_knife"))
        self.click("ok")
        self.click("close")
        self.assertEqual(g.game_state, SPACE)
        g = self.game
        self.open("t3_bed")
        self.click("t3_bed_board")
        self.expect_dialogue("scene_12_carving")
        self.finish()
        self.assertEqual(g.game_state, SPACE)
        self.assertTrue(g.has_event("t3_completed"))
        self.open("t3_exit_door")
        self.click("leave")
        self.assertEqual(g.current_scene, "scene_13_anchor_terminal")
        g = self.game
        self.expect_dialogue("scene_13_entry")
        self.finish()
        self.open("ch2_terminal")
        buttons = self.ui.draw(self.screen, (0, 0))
        self.interaction.start_anchor_drag(buttons, buttons["fragment:past_fragment"].center)
        attempts = copy.deepcopy(g.puzzle_attempts)
        self.interaction.finish_anchor_drag(buttons, buttons["slot:present"].center)
        self.assertEqual(self.ui.result["status"], "wrong_slot")
        self.assertEqual(g.puzzle_attempts, attempts)
        self.assertEqual(self.ui.mode, "anchor_fragments")
        for item, slot in (("past_fragment", "past"), ("present_fragment", "present"),
                           ("future_fragment", "future")):
            buttons = self.ui.draw(self.screen, (0, 0))
            self.interaction.start_anchor_drag(buttons, buttons["fragment:" + item].center)
            self.interaction.finish_anchor_drag(buttons, buttons["slot:" + slot].center)
        self.expect_dialogue("scene_13_terminal")
        self.finish()
        self.assertEqual(self.ui.mode, "multi_input")
        self.click("back")
        self.open("ch2_terminal")
        self.assertEqual(self.ui.mode, "multi_input")
        self.assertEqual(self.puzzle.multi_input, {"past": "", "present": "", "future": ""})
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
        self.assertEqual(g.game_state, SPACE)
        self.assertFalse(self.ui.is_open())
        manager = MapManager(self.layout, self.game_ui, g)
        self.assertIn("door_d", manager.get_interaction_rects("CH2_CORRIDOR", self.screen))

    def test_capsule_and_age_failure_paths(self):
        self.game.enter_space("T3")
        self.game.complete_event("t3_time_capsule_found")
        self.open("t3_time_capsule")
        self.assertEqual(self.ui.result["status"], "puzzle_unavailable")
        self.game.learn_knowledge("number_0347")
        self.open("t3_time_capsule")
        self.assertEqual(self.puzzle.dial_digits, [0, 0, 0, 0])
        self.click_dial(0, 1)
        self.interaction.handle_key(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
        self.open("t3_time_capsule")
        self.assertEqual(self.puzzle.dial_digits, [1, 0, 0, 0])
        self.assertEqual(self.puzzle.remaining_attempts, 3)
        for answer, remaining in (("1111", 2), ("2222", 1), ("3333", 0)):
            self.set_dial_password(answer)
            self.assertEqual(self.puzzle.remaining_attempts, remaining + 1)
            self.click("confirm")
            self.assertEqual(self.manager.get_remaining_attempts("t3_time_capsule"), remaining)
            if remaining:
                self.assertEqual(self.ui.result["message"].splitlines()[0], "密碼錯誤。")
                self.assertEqual(self.puzzle.dial_digits, list(map(int, answer)))
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
            self.puzzle.multi_input = {"past": "4", "present": "7", "future": "13"}
            self.interaction.submit_puzzle()
            self.assertEqual(self.manager.get_failure_stage("anchor_age_verification"), stage)
            self.assertEqual(self.puzzle.multi_input, {"past": "", "present": "", "future": ""})
        self.assertNotEqual(self.game.game_state, GAME_OVER)
        self.assertEqual(self.puzzle.last_result["status"], "final_failure_pending")
        self.assertEqual(self.puzzle.multi_input, {"past": "", "present": "", "future": ""})
        self.click("ack_failure")
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
        manager = MapManager(copy.deepcopy(layout), ui, self.game)
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
        for space, object_id in (("T0", "t0_windowsill"), ("T3", "t3_windowsill")):
            with self.subTest(space=space):
                self.game.enter_space(space)
                prompt(self.screen, {"id": object_id})
                self.assertEqual(spy.render.call_args.args[0], "[E] 互動：窗台")

    def test_t0_windowsill_data_keeps_search_reward_and_location(self):
        layout_objects = self.layout["spaces"]["T0"]["objects"]
        self.assertNotIn("t0_curtain", self.objects)
        self.assertNotIn("t0_curtain", layout_objects)
        windowsill = self.objects["t0_windowsill"]
        self.assertEqual(
            (windowsill["name"], windowsill["type"], windowsill["item"]),
            ("窗台", "searchable", "t0_diary_page_5"),
        )

    def test_windowsill_interaction_polygon(self):
        manager = MapManager(self.layout, self.game_ui, self.game)
        player = Player(0, 0, width=2, height=2)
        in_region = home_function("is_in_interaction_region", {
            "ui_layout": self.layout, "game": self.game, "game_ui": self.game_ui,
            "screen": self.screen, "player": player,
        })
        for space, object_id in (("T0", "t0_windowsill"), ("T3", "t3_windowsill")):
            with self.subTest(space=space):
                self.game.enter_space(space)
                rect = manager.get_interaction_rects(space, self.screen)[object_id]
                self.assertEqual(rect, pygame.Rect(293, 150, 201, 47))
                player.rect.center = (390, 175)
                self.assertTrue(in_region(object_id, rect))
                player.rect.center = (295, 153)
                self.assertFalse(in_region(object_id, rect))

    def test_corridor_return_spawns_are_independent_of_door_positions(self):
        corridor = self.layout["spaces"]["CH2_CORRIDOR"]
        expected = {
            "door_t0": ((201, 229), (139, 239)),
            "door_t3": ((201, 53), (139, 52)),
            "door_t7": ((201, 431), (140, 436)),
        }
        for door, (spawn, position) in expected.items():
            with self.subTest(door=door):
                self.assertEqual(corridor["entry_spawns"][door], dict(zip(("x", "y"), spawn)))
                layout = corridor["objects"][door]
                self.assertEqual((layout["x"], layout["y"]), position)

    def test_space_change_places_player_and_hides_only_first_frame(self):
        place = home_function("place_player_on_space_change", {})
        manager = MapManager(self.layout, self.game_ui, self.game)
        player = Player(0, 0)
        cases = (
            ("A", "B", "wardrobe_rift", None),
            ("A", "C", "floor_rift_A", None),
            ("B", "A", "floor_rift_B", None),
            ("B", "C", "ceiling_rift", None),
            ("C", "A", "rift_C_A", None),
            ("C", "B", "rift_C_B", None),
            ("CH2_CORRIDOR", "T0", None, None),
            ("T0", "CH2_CORRIDOR", None, "door_t0"),
            ("CH2_CORRIDOR", "T7", None, None),
            ("T7", "CH2_CORRIDOR", None, "door_t7"),
            ("CH2_CORRIDOR", "T3", None, None),
            ("T3", "CH2_CORRIDOR", None, "door_t3"),
        )
        for source, target, rift, door in cases:
            with self.subTest(source=source, target=target):
                spawn = manager.get_spawn_layout(target, rift)
                if door:
                    spawn.update(manager.get_object_entry_spawn(target, door))
                expected = self.game_ui.scale_rect(self.screen, spawn).center
                manager.place_player(player, source, self.screen)
                player.set_mouse_target((10, 10))
                keys = {pygame.K_w}
                self.interaction.pending_entry_rift = rift
                self.interaction.pending_entry_object = door
                with patch.object(manager, "place_player", wraps=manager.place_player) as placement:
                    self.assertTrue(place(target, source, manager, player, self.screen, self.interaction, keys))
                    self.assertEqual(player.rect.center, expected)
                    self.assertFalse(keys)
                    self.assertIsNone(player.mouse_target)
                    self.assertIsNone(self.interaction.pending_entry_rift)
                    self.assertIsNone(self.interaction.pending_entry_object)
                    self.assertFalse(place(target, target, manager, player, self.screen, self.interaction, keys))
                    placement.assert_called_once_with(player, target, self.screen, rift, door)

    def test_dialogue_background_can_hide_player_without_hiding_space(self):
        player = Mock()
        game_ui = Mock()
        self.game.enter_space("T0")
        draw = home_function("draw_dialogue_background", {
            "game": self.game, "game_ui": game_ui, "player": player,
            "dialogue_controller": types.SimpleNamespace(dialogue_id="scene_10_entry"),
            "draw_t7_power_outage_overlay": home_function(
                "draw_t7_power_outage_overlay", {"game": self.game, "pygame": pygame}
            ),
        })
        draw(self.screen, (0, 0), draw_player=False)
        game_ui.draw_space.assert_called_once_with(self.screen, self.game, (0, 0))
        player.draw.assert_not_called()
        draw(self.screen, (0, 0))
        player.draw.assert_called_once_with(self.screen)

    def test_data_references_and_pending_runtime_exclusion(self):
        represented = set()
        for space, layout in self.layout["spaces"].items():
            represented.update(layout.get("objects", {}))
            represented.update(layout.get("pending_objects", {}))
            for object_id, rect in layout.get("objects", {}).items():
                self.assertIn(object_id, self.objects)
                self.assertGreater(rect["width"], 0)
                self.assertGreater(rect["height"], 0)
        nested = {child for obj in self.objects.values() for child in obj.get("contents", [])}
        for object_id, data in self.objects.items():
            if data.get("space"):
                self.assertIn(object_id, represented | nested)
        for space, parent, children in (
            ("T0", "t0_desk", {"t0_diary"}),
            ("T7", "t7_desk", {"t7_letter", "t7_desk_drawer"}),
        ):
            world_objects = self.layout["spaces"][space]["objects"]
            self.assertIn(parent, world_objects)
            self.assertFalse(children & world_objects.keys())
        manager = MapManager(copy.deepcopy(self.layout), self.game_ui, self.game)
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

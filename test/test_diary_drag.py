"""日記拖放、道具合併、閱讀器與時間房出口回歸。"""
import copy
import os
from pathlib import Path
import unittest
from unittest.mock import patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame

from test import test_chapter2_flow as flow
from controllers.hotbar_controller import HotbarController
from managers.map_manager import MapManager
from player import Player


class DiaryDragTests(unittest.TestCase):
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
        self.f.game.enter_space("T0")
        self.pages = self.f.puzzles["t0_diary_restore"]["answer"]

    def open_diary(self, count=3):
        for item in self.pages[:count]:
            self.f.game.add_item(item)
        self.f.open("t0_diary")
        self.assertEqual(self.f.ui.mode, "diary_drag")
        return self.f.ui.draw(self.screen, (0, 0))

    def drag(self, item, slot=None):
        if slot is not None:
            puzzle = self.f.puzzle
            target_index = next(
                index for index, spread in enumerate(puzzle.diary_spreads)
                if spread["slot_id"] == slot
            )
            while puzzle.diary_spread_index < target_index:
                self.f.click("diary_next_page")
            while puzzle.diary_spread_index > target_index:
                self.f.click("diary_prev_page")
        buttons = self.f.ui.draw(self.screen, (0, 0))
        rect = buttons["_drag_rects"][item]
        self.f.interaction.handle_click(buttons, rect.center)
        self.assertEqual(self.f.puzzle.diary_dragging_page, item)
        destination = buttons["diary_slot:" + slot].center if slot else (25, 25)
        self.f.interaction.update_diary_drag(destination)
        self.f.interaction.finish_diary_drag(buttons, destination)

    def test_open_with_zero_to_three_pages_and_only_owned_draggable(self):
        for count in range(4):
            with self.subTest(count=count):
                self.f.game.inventory = list(self.pages[:count])
                buttons = self.open_diary(0)
                self.assertEqual(set(buttons["_drag_rects"]), set(self.pages[:count]))
                result = self.f.interaction.submit_puzzle()
                self.assertEqual(result["status"], "incomplete_input")
                self.assertEqual(self.f.game.puzzle_attempts, {})
                self.f.ui.close()
        self.f.game.inventory = []
        self.open_diary(0)
        self.f.interaction.start_diary_drag(self.pages[0], pygame.Rect(0, 0, 10, 10), (5, 5))
        self.assertIsNone(self.f.puzzle.diary_dragging_page)

    def test_drag_wrong_slot_replacement_outside_reset_and_resize(self):
        self.open_diary()
        self.drag(self.pages[0], "page_4")
        self.assertEqual(self.f.puzzle.diary_slots["page_4"], self.pages[0])
        self.drag(self.pages[1], "page_4")
        self.assertEqual(self.f.puzzle.diary_slots["page_4"], self.pages[1])
        buttons = self.f.ui.draw(self.screen, (0, 0))
        self.assertEqual(buttons["_drag_rects"][self.pages[0]].topleft, (180, 405))
        self.drag(self.pages[1])
        self.assertTrue(all(value is None for value in self.f.puzzle.diary_slots.values()))
        self.drag(self.pages[0], "page_2")
        self.f.click("reset")
        self.assertTrue(all(value is None for value in self.f.puzzle.diary_slots.values()))
        self.assertEqual(set(self.f.game.inventory), set(self.pages))
        for size in ((640, 480), (1280, 720)):
            buttons = self.f.ui.draw(pygame.Surface(size), (0, 0))
            rect = buttons["_drag_rects"][self.pages[0]]
            self.f.interaction.start_diary_drag(self.pages[0], rect, rect.center)
            target = buttons["diary_slot:page_2"].center
            self.f.interaction.update_diary_drag(target)
            self.f.interaction.finish_diary_drag(buttons, target)
            self.assertEqual(self.f.puzzle.diary_slots["page_2"], self.pages[0])
            self.f.puzzle.reset_diary_drag_state()

    def test_spread_config_and_navigation_bounds(self):
        puzzle = self.f.puzzle
        self.assertEqual(
            [(Path(s["background_asset"]).name, s["slot_id"], s["side"])
             for s in puzzle.diary_spreads],
            [("1.png", "page_2", "right"), ("3.png", "page_4", "right"),
             ("empty_diary.png", "page_5", "left")],
        )
        self.assertEqual(puzzle.diary_spread_index, 0)
        for expected in (1, 2, 2):
            puzzle.next_diary_spread()
            self.assertEqual(puzzle.diary_spread_index, expected)
        for expected in (1, 0, 0):
            puzzle.previous_diary_spread()
            self.assertEqual(puzzle.diary_spread_index, expected)

    def test_keyboard_navigation_and_reset_clear_all_drag_state(self):
        self.open_diary()
        self.drag(self.pages[0], "page_2")
        puzzle = self.f.puzzle
        for key, expected in ((pygame.K_RIGHT, 1), (pygame.K_LEFT, 0), (pygame.K_RIGHT, 1)):
            self.f.interaction.handle_key(pygame.event.Event(pygame.KEYDOWN, key=key))
            self.assertEqual(puzzle.diary_spread_index, expected)

        buttons = self.f.ui.draw(self.screen, (0, 0))
        rect = buttons["_drag_rects"][self.pages[1]]
        self.f.interaction.start_diary_drag(self.pages[1], rect, rect.center)
        self.assertTrue(puzzle.diary_page_positions)
        self.assertNotEqual(puzzle.diary_drag_offset, (0, 0))
        self.f.click("reset")
        self.assertEqual(puzzle.diary_spread_index, 0)
        self.assertIsNone(puzzle.diary_dragging_page)
        self.assertEqual(puzzle.diary_drag_offset, (0, 0))
        self.assertEqual(puzzle.diary_page_positions, {})
        self.assertTrue(all(value is None for value in puzzle.diary_slots.values()))

    def test_inventory_draws_the_shared_diary_assets(self):
        game_ui = self.f.game_ui
        for number in (2, 4, 5):
            item = f"t0_diary_page_{number}"
            with self.subTest(item=item):
                asset = self.f.objects[item]["ui_asset"]
                self.assertTrue(asset.endswith(f"/日記内容/{number}.png"))
                with patch.object(game_ui, "load_image", wraps=game_ui.load_image) as load:
                    self.assertTrue(game_ui.draw_item_asset(
                        self.screen, item, pygame.Rect(0, 0, 80, 80)
                    ))
                    load.assert_called_once_with(asset)

    def test_escape_cancel_preserves_confirm_exit_clears_and_reopen_clean(self):
        self.open_diary()
        self.drag(self.pages[0], "page_2")
        self.f.interaction.handle_key(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
        self.assertEqual(self.f.ui.mode, "diary_exit_confirmation")
        self.f.click("cancel")
        self.assertEqual(self.f.puzzle.diary_slots["page_2"], self.pages[0])
        self.f.click("exit")
        self.f.click("confirm")
        self.assertFalse(self.f.ui.is_open())
        self.assertEqual(set(self.f.game.inventory), set(self.pages))
        self.f.open("t0_diary")
        self.assertTrue(all(value is None for value in self.f.puzzle.diary_slots.values()))

    def restore_diary(self):
        self.open_diary()
        for item, slot in zip(self.pages, ("page_2", "page_4", "page_5")):
            self.drag(item, slot)
        self.f.click("confirm")

    def test_wrong_order_unlimited_then_success_conversion_and_safe_unlock(self):
        self.open_diary()
        for item, slot in zip(self.pages, ("page_4", "page_2", "page_5")):
            self.drag(item, slot)
        self.f.click("confirm")
        self.assertEqual(self.f.ui.result["status"], "wrong")
        self.assertEqual(self.f.game.puzzle_attempts, {})
        self.restore_diary()
        g = self.f.game
        self.assertTrue(g.is_puzzle_solved("t0_diary_restore"))
        self.assertTrue(g.has_item("t0_fixed_diary"))
        self.assertTrue(all(not g.has_item(item) for item in self.pages))
        self.assertTrue(all(g.has_discovered_item(item) for item in self.pages))
        self.assertTrue(all(value is None for value in self.f.puzzle.diary_slots.values()))
        self.assertTrue(self.f.manager.can_attempt("t0_child_safe"))

    def test_restored_diary_disappears_from_desk_and_hotbar_reader_keeps_all_months(self):
        self.restore_diary()
        self.f.acknowledge_success("日記頁已經按照月份恢復。")
        self.f.acknowledge_rewards("t0_fixed_diary")
        self.f.open("t0_desk")
        self.assertEqual(self.f.ui.result["contents"], [])
        self.f.game.remove_item("t0_fixed_diary")
        self.f.open("t0_desk")
        self.assertEqual(self.f.ui.result["contents"], [])
        self.f.click("close")
        self.f.game.add_item("t0_fixed_diary")
        hotbar = HotbarController(self.f.game, self.f.game_ui, self.f.ui, self.f.interaction)
        hotbar.open_item("t0_fixed_diary")
        self.assertEqual(self.f.ui.mode, "diary_reader")
        self.assertEqual(self.f.ui.current_object_id, "t0_fixed_diary")
        expected = [
            ("一月", "今天陪她只有一小時。本月缺席：2 次。"),
            ("二月", "她畫了一幅畫給我。本月缺席：3 次。"),
            ("三月", "她問我，爸爸為什麼總是在加班。本月缺席：5 次。"),
            ("四月", "我送她的繪本，她只翻到第一頁。本月缺席：8 次。"),
            ("五月", "護士說，她最近都不再問了。本月缺席：13 次。"),
            ("六月", "六月：本月缺席：＿＿ 次（還沒到）")
        ]
        pages = self.f.objects["t0_fixed_diary"]["pages"]
        self.assertEqual(
            [(month, text) for page in pages
             for month, text in zip(page["month"].split("・"), page["text"].splitlines(), strict=True)],
            expected
        )
        self.f.click("previous")
        self.assertEqual(self.f.puzzle.diary_reader_page, 0)
        for _ in range(7):
            self.f.click("next")
        self.assertEqual(self.f.puzzle.diary_reader_page, len(pages) - 1)
        for _ in range(7):
            self.f.click("previous")
        self.assertEqual(self.f.puzzle.diary_reader_page, 0)

    def test_all_exits_confirmation_cancel_and_corresponding_door_spawn(self):
        manager = MapManager(copy.deepcopy(self.f.layout), self.f.game_ui, self.f.game)
        for space, prefix in (("T0", "t0"), ("T7", "t7"), ("T3", "t3")):
            with self.subTest(space=space):
                self.f.game.enter_space(space)
                self.f.open(prefix + "_exit_door")
                self.assertEqual(self.f.ui.mode, "exit_confirmation")
                self.assertEqual(self.f.game.current_space, space)
                self.f.click("cancel")
                self.assertEqual(self.f.game.current_space, space)
                self.f.open(prefix + "_exit_door")
                self.f.click("leave")
                self.assertEqual(self.f.game.current_space, "CH2_CORRIDOR")
                object_id = "door_" + prefix
                self.assertEqual(self.f.interaction.pending_entry_object, object_id)
                door = self.f.layout["spaces"]["CH2_CORRIDOR"]["objects"][object_id]
                expected = self.f.layout["spaces"]["CH2_CORRIDOR"]["entry_spawns"][object_id]
                self.assertEqual(manager.get_object_entry_spawn("CH2_CORRIDOR", object_id), expected)
                player = Player(0, 0)
                self.assertTrue(manager.place_player(player, "CH2_CORRIDOR", self.screen,
                                                    entry_object_id=object_id))
                original = dict(manager.player_layouts["CH2_CORRIDOR"])
                original.update(expected)
                self.assertEqual(player.rect.center, self.f.game_ui.scale_rect(self.screen, original).center)
        self.assertIsNone(manager.get_object_entry_spawn("CH2_CORRIDOR", "missing"))


if __name__ == "__main__":
    unittest.main()

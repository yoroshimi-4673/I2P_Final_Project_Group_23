import unittest
from unittest.mock import patch

import pygame

from controllers.polygon_editor_controller import PolygonEditorController


class PolygonEditorControllerTests(unittest.TestCase):
    def setUp(self):
        self.original_polygon = [[0, 0], [800, 0], [0, 600]]
        self.layout = {
            "base_resolution": {"width": 800, "height": 600},
            "spaces": {"A": {"walkable_polygon": self.original_polygon}},
        }
        self.editor = PolygonEditorController(self.layout)
        output = patch("builtins.print")
        self.output = output.start()
        self.addCleanup(output.stop)
        self.editor.start("A")

    def test_start_centers_cursor_and_resets_state(self):
        self.editor.handle_keydown(pygame.K_RIGHT, 100)
        self.editor.add_point()
        self.editor.start("A")
        self.assertTrue(self.editor.active)
        self.assertEqual(self.editor.space_id, "A")
        self.assertEqual(self.editor.points, [])
        self.assertEqual(self.editor.cursor, [400, 300])
        self.assertEqual(self.editor.key_started, {})

    def test_mouse_add_updates_cursor_and_rounds_to_base_coordinates(self):
        screen = pygame.Surface((1200, 900))
        self.editor.add_point_from_screen((151, 302), screen)
        self.assertEqual(self.editor.cursor, [101, 201])
        self.assertEqual(self.editor.points, [(101, 201)])
        self.assertEqual(self.editor.base_to_screen((100, 200), screen), (150, 300))

    def test_undo_removes_only_last_vertex(self):
        self.editor.add_point()
        self.editor.handle_keydown(pygame.K_RIGHT, 100)
        self.editor.add_point()
        self.editor.handle_keydown(pygame.K_BACKSPACE, 100)
        self.assertEqual(self.editor.points, [(400, 300)])

    def test_clear_removes_all_vertices(self):
        self.editor.handle_keydown(pygame.K_SPACE, 100)
        self.editor.handle_keydown(pygame.K_r, 100)
        self.assertEqual(self.editor.points, [])

    def test_arrow_press_moves_once_then_waits_for_hold_threshold(self):
        self.editor.handle_keydown(pygame.K_RIGHT, 100)
        self.editor.handle_keydown(pygame.K_RIGHT, 200)
        self.assertEqual(self.editor.cursor, [401, 300])
        self.editor.update(0.1, 1099, True)
        self.assertEqual(self.editor.cursor, [401, 300])

    def test_hold_counts_only_time_after_threshold(self):
        self.editor.handle_keydown(pygame.K_RIGHT, 100)
        self.editor.update(0.1, 1150, True)  # 這一幀只有後半段超過門檻
        self.assertAlmostEqual(self.editor.cursor[0], 410)
        self.editor.update(0.1, 1250, True)
        self.assertAlmostEqual(self.editor.cursor[0], 428)

    def test_diagonal_hold_limits_speed(self):
        self.editor.handle_keydown(pygame.K_RIGHT, 100)
        self.editor.handle_keydown(pygame.K_DOWN, 100)
        self.editor.update(0.1, 1200, True)
        self.assertAlmostEqual(pygame.Vector2(self.editor.cursor).distance_to((401, 301)), 18)

    def test_keyboard_cursor_stays_within_base_resolution(self):
        self.editor.handle_keydown(pygame.K_LEFT, 0)
        self.editor.handle_keydown(pygame.K_UP, 0)
        self.editor.update(10, 11000, True)
        self.assertEqual(self.editor.cursor, [0, 0])
        self.editor.clear_held_keys()
        self.editor.handle_keydown(pygame.K_RIGHT, 11000)
        self.editor.handle_keydown(pygame.K_DOWN, 11000)
        self.editor.update(10, 22000, True)
        self.assertEqual(self.editor.cursor, [800, 600])

    def test_apply_requires_three_vertices(self):
        self.editor.add_point()
        self.assertFalse(self.editor.apply())
        self.assertIs(self.layout["spaces"]["A"]["walkable_polygon"], self.original_polygon)
        self.assertTrue(self.editor.active)

    def test_enter_applies_runtime_polygon_prints_json_and_closes(self):
        screen = pygame.Surface((800, 600))
        points = [(30, 50), (60, 50), (60, 80)]
        for point in points:
            self.editor.add_point_from_screen(point, screen)
        self.editor.handle_keydown(pygame.K_RETURN, 0)
        self.assertEqual(self.layout["spaces"]["A"]["walkable_polygon"], [list(p) for p in points])
        self.assertFalse(self.editor.active)
        self.assertTrue(any(call.args[0].startswith('"walkable_polygon": [')
                            for call in self.output.call_args_list))

    def test_cancel_clears_editor_state(self):
        self.editor.add_point()
        self.editor.handle_keydown(pygame.K_RIGHT, 0)
        self.editor.cancel()
        self.assertFalse(self.editor.active)
        self.assertIsNone(self.editor.space_id)
        self.assertEqual(self.editor.points, [])
        self.assertEqual(self.editor.key_started, {})

    def test_keyup_removes_only_released_key_and_focus_loss_clears_rest(self):
        self.editor.handle_keydown(pygame.K_RIGHT, 100)
        self.editor.handle_keydown(pygame.K_UP, 200)
        self.editor.handle_keyup(pygame.K_RIGHT)
        self.assertEqual(self.editor.key_started, {pygame.K_UP: 200})
        self.editor.update(0.1, 1300, False)
        self.assertEqual(self.editor.key_started, {})
        self.assertEqual(self.editor.cursor, [401, 299])

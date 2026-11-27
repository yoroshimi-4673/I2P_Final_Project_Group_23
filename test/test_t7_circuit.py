import json
from pathlib import Path
import unittest
from unittest.mock import patch

from controllers.puzzle_controller import PuzzleController
from managers.game_manager import GameManager
from managers.puzzle_manager import PuzzleManager


class T7CircuitTests(unittest.TestCase):
    def setUp(self):
        path = Path(__file__).resolve().parents[1] / "data" / "puzzles.json"
        self.puzzles = json.loads(path.read_text(encoding="utf-8"))
        self.game = GameManager()
        self.game.enter_space("T7")
        self.manager = PuzzleManager(self.game, self.puzzles, {})
        self.controller = PuzzleController(self.manager)

    def test_connections_for_each_rotation(self):
        for tile_type, rotations in {
            "straight": ("up down", "left right", "up down", "left right"),
            "corner": ("up right", "right down", "down left", "left up"),
            "T": ("left up right", "up right down", "right down left", "down left up"),
            "cross": ("up right down left",) * 4,
            "start": ("up", "right", "down", "left"),
            "end": ("up", "right", "down", "left"),
            "unknown": ("",) * 4,
        }.items():
            for rotation, directions in enumerate(rotations):
                with self.subTest(tile_type=tile_type, rotation=rotation):
                    expected = set(directions.split())
                    self.assertEqual(self.controller.get_circuit_connections(tile_type, rotation), expected)
                    self.assertEqual(self.controller.get_circuit_connections(tile_type, rotation + 4), expected)

    def test_adjacent_tiles_need_reciprocal_connections(self):
        start = {"type": "start", "rotation": 1}
        horizontal = {"type": "straight", "rotation": 1}
        vertical = {"type": "straight", "rotation": 0}
        connect = self.controller.are_circuit_tiles_connected
        self.assertTrue(connect(start, horizontal, "right"))
        self.assertTrue(connect(horizontal, start, "left"))
        self.assertFalse(connect(start, vertical, "right"))
        self.assertFalse(connect(start, horizontal, "left"))

    def test_initial_board(self):
        controller = self.controller
        self.assertEqual(controller.open_puzzle("t7_circuit")["status"], "input_required")
        self.assertEqual(len(controller.circuit_tiles), 28)
        self.assertEqual(controller.get_circuit_tile_position("start"), (4, 0))
        self.assertEqual(controller.get_circuit_tile_position("end"), (0, 9))
        self.assertEqual(controller.circuit_tiles[(4, 0)], {"type": "start", "rotation": 1, "rotatable": False})
        self.assertEqual(controller.circuit_tiles[(0, 9)], {"type": "end", "rotation": 3, "rotatable": False})
        self.assertEqual(controller.circuit_tiles[(2, 1)], {"type": "cross", "rotation": 0, "rotatable": False})
        self.assertEqual(controller.circuit_powered_tiles, {(4, 0)})
        self.assertFalse(controller.is_circuit_complete())

    def test_rotate_reset_and_close_do_not_mutate_definition(self):
        controller = self.controller
        self.assertEqual(controller.rotate_circuit_tile(4, 1), {"status": "not_circuit"})
        controller.open_puzzle("t7_circuit")
        initial = {
            (tile["row"], tile["col"]): tile["rotation"]
            for tile in self.puzzles["t7_circuit"]["tiles"]
        }
        for position in ((4, 0), (0, 9), (2, 1)):
            self.assertEqual(controller.rotate_circuit_tile(*position), {"status": "fixed"})
            self.assertEqual(controller.circuit_tiles[position]["rotation"], initial[position])
        self.assertEqual(controller.rotate_circuit_tile(0, 0), {"status": "empty"})
        self.assertEqual(controller.rotate_circuit_tile(4, 1), {
            "status": "rotated", "position": (4, 1), "rotation": 1,
        })
        self.assertEqual(controller.rotate_circuit_tile(1, 1)["rotation"], 0)
        self.assertEqual(
            {position: tile["rotation"] for position, tile in controller.circuit_initial_tiles.items()},
            initial,
        )
        controller.reset_circuit_state()
        self.assertEqual({position: tile["rotation"] for position, tile in controller.circuit_tiles.items()}, initial)
        self.assertEqual(controller.circuit_powered_tiles, {(4, 0)})
        controller.rotate_circuit_tile(4, 1)
        controller.close_puzzle()
        self.assertFalse(controller.circuit_tiles)
        self.assertFalse(controller.circuit_initial_tiles)
        self.assertFalse(controller.circuit_powered_tiles)
        controller.open_puzzle("t7_circuit")
        self.assertEqual({position: tile["rotation"] for position, tile in controller.circuit_tiles.items()}, initial)

    def test_complete_only_requires_end_power_and_runs_bfs_once(self):
        controller = self.controller
        controller.open_puzzle("t7_circuit")
        controller.circuit_tiles = {
            (0, 0): {"type": "start", "rotation": 1, "rotatable": False},
            (0, 1): {"type": "straight", "rotation": 0, "rotatable": True},
            (0, 2): {"type": "end", "rotation": 3, "rotatable": False},
            (1, 1): {"type": "cross", "rotation": 0, "rotatable": False},
        }
        self.assertFalse(controller.is_circuit_complete())
        with (
            patch.object(controller, "calculate_circuit_powered_tiles",
                         wraps=controller.calculate_circuit_powered_tiles) as bfs,
            patch.object(self.manager, "apply_success", wraps=self.manager.apply_success) as apply_success,
        ):
            result = controller.rotate_circuit_tile(0, 1)
        bfs.assert_called_once_with()
        apply_success.assert_called_once_with("t7_circuit")
        self.assertEqual(controller.circuit_powered_tiles, {(0, 0), (0, 1), (0, 2)})
        self.assertEqual(result["status"], "correct")
        self.assertEqual(result["on_complete"], {"type": "story_event", "event": "t7_circuit_completed"})
        self.assertIs(controller.last_result, result)
        self.assertTrue(self.game.is_puzzle_solved("t7_circuit"))
        self.assertEqual(controller.rotate_circuit_tile(0, 1), {"status": "puzzle_solved"})
        controller.close_puzzle()
        self.assertEqual(controller.open_puzzle("t7_circuit")["status"], "puzzle_solved")

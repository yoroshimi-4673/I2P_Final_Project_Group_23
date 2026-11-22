import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pygame

from controllers.navigation_controller import NavigationController
from player import Player


class NavigationControllerTests(unittest.TestCase):
    def setUp(self):
        self.path = [(70, 80)]
        self.pathfinding = Mock()
        self.pathfinding.find_path.return_value = self.path
        self.player = Mock(spec=Player)
        self.game = SimpleNamespace(current_space="T3")
        self.controller = NavigationController(self.pathfinding, self.player, self.game)
        self.screen = object()
        self.obstacles = [pygame.Rect(10, 15, 10, 10)]
        self.polygon = [(0, 0), (100, 0), (100, 100)]
        self.click = (90, 80)
        self.target = {"interaction_rect": pygame.Rect(65, 70, 30, 20)}

    def navigate(self, target=None):
        self.controller.navigate_to_click(
            self.click, self.screen, self.obstacles, self.polygon, target
        )

    def test_ground_click_passes_current_space_and_geometry(self):
        self.game.current_space = "T7"  # 切換房間後應取得最新空間
        self.navigate()

        self.pathfinding.find_path.assert_called_once_with(
            "T7", self.screen, self.player, self.click, self.obstacles, self.polygon, None
        )
        args = self.pathfinding.find_path.call_args.args
        self.assertIs(args[4], self.obstacles)
        self.assertIs(args[5], self.polygon)
        self.player.can_interact.assert_not_called()
        self.player.set_path.assert_called_once_with(self.path, None)

    def test_object_click_plans_to_the_interaction_stop_point(self):
        self.player.can_interact.return_value = False
        stop = (70, 80)
        self.player.get_interaction_stop_point.return_value = stop

        self.navigate(self.target)

        self.player.can_interact.assert_called_once_with(self.target)
        self.player.get_interaction_stop_point.assert_called_once_with(self.target)
        self.pathfinding.find_path.assert_called_once_with(
            "T3", self.screen, self.player, stop,
            self.obstacles, self.polygon, self.target["interaction_rect"],
        )
        self.player.set_path.assert_called_once_with(self.path, self.target)

    def test_object_in_range_cancels_without_planning(self):
        self.player.can_interact.return_value = True

        self.navigate(self.target)

        self.player.cancel_mouse_movement.assert_called_once_with()
        self.player.get_interaction_stop_point.assert_not_called()
        self.pathfinding.find_path.assert_not_called()
        self.player.set_path.assert_not_called()

    def test_no_route_clears_the_existing_player_route(self):
        player = Player(20, 40, width=20, height=20)
        player.set_path(self.path, self.target)  # 先建立可確認被清除的舊路徑
        self.controller = NavigationController(self.pathfinding, player, self.game)
        self.pathfinding.find_path.return_value = []

        with patch.object(player, "set_path", wraps=player.set_path) as set_path:
            self.navigate()
            set_path.assert_called_once_with([], None)

        self.assertEqual(player.path_points, [])
        self.assertEqual(player.path_index, 0)
        self.assertIsNone(player.mouse_target)
        self.assertIsNone(player.interaction_target)

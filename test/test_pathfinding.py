"""滑鼠導航的網格、實際腳部碰撞和路線追蹤回歸。"""

import unittest

import pygame

from managers.pathfinding_manager import PathfindingManager
from player import Player


class BaseLayout:
    def scale_x(self, screen, value):
        return value * screen.get_width() / 160

    def scale_y(self, screen, value):
        return value * screen.get_height() / 120


class PathfindingTests(unittest.TestCase):
    def setUp(self):
        self.screen = pygame.Surface((160, 120))
        self.player = Player(20, 40, width=20, height=20, speed=140)
        self.manager = PathfindingManager(BaseLayout())
        self.obstacles = []
        self.polygon = [(0, 0), (159, 0), (159, 119), (0, 119)]

    def plan(self, target, interaction_rect=None):
        return self.manager.find_path(
            "test", self.screen, self.player, target, self.obstacles, self.polygon, interaction_rect
        )

    def assert_route_clear(self, route):
        previous = self.player.rect.center
        for point in route:
            self.assertTrue(self.is_walkable(point))
            self.assertTrue(self.manager.segment_is_walkable(previous, point, self.is_walkable))
            previous = point

    def is_walkable(self, point):
        return self.manager.is_position_walkable(self.player, point, self.obstacles, self.polygon)

    def walk(self, route, interaction=None, dt=0.019):
        self.player.set_path(route, interaction)
        for _ in range(500):
            self.player.update(dt, set(), self.obstacles, *self.screen.get_size(), self.polygon)
            self.assertTrue(self.is_walkable(self.player.rect.center))
            if not self.player.path_points:
                return
        self.fail("Player did not finish the route")

    def test_open_route_simplifies_to_exact_click(self):
        target = (137, 49)
        before = self.player.rect.copy()
        route = self.plan(target)
        self.assertEqual(route, [pygame.Vector2(target)])
        self.assertEqual(self.player.rect, before)
        self.walk(route, dt=0.093)
        self.assertEqual(self.player.rect.center, target)

    def test_path_and_player_detour_around_small_furniture(self):
        self.obstacles = [pygame.Rect(65, 36, 30, 48)]
        route = self.plan((135, 50))
        self.assertGreater(len(route), 1)
        self.assert_route_clear(route)
        self.walk(route)
        self.assertEqual(self.player.rect.center, (135, 50))

    def test_off_polygon_and_furniture_clicks_snap(self):
        self.polygon = [(12, 18), (140, 18), (140, 100), (12, 100)]
        self.obstacles = [pygame.Rect(110, 43, 15, 30)]
        for target, expected in (((118, 55), (130, 55)), ((155, 35), (135, 35))):
            with self.subTest(target=target):
                route = self.plan(target)
                self.assert_route_clear(route)
                self.assertEqual(route[-1], pygame.Vector2(expected))

    def test_diagonal_cannot_cut_between_corner_obstacles(self):
        self.screen = pygame.Surface((32, 24))
        self.player = Player(5, 5, width=1, height=1)
        self.polygon = []
        self.obstacles = [pygame.Rect(5, 6, 1, 1), pygame.Rect(6, 5, 1, 1)]
        route = self.plan((6, 6))
        self.assertGreater(len(route), 1)
        self.assert_route_clear(route)
        self.walk(route)
        self.assertEqual(self.player.rect.center, (6, 6))

    def test_single_pixel_barrier_is_not_skipped(self):
        self.obstacles = [pygame.Rect(77, 0, 1, self.screen.get_height())]
        self.assertEqual(self.plan((130, 50)), [])

    def test_wasd_cancels_waypoints_and_new_click_replaces_all_state(self):
        self.player.set_path([(90, 60), (130, 70)], {"interaction_rect": pygame.Rect(130, 70, 10, 10)})
        self.player.set_path(self.plan((30, 88)))
        self.assertEqual(self.player.path_points, [pygame.Vector2(30, 88)])
        self.assertIsNone(self.player.interaction_target)
        self.player.update(0.1, {pygame.K_w}, [], *self.screen.get_size(), self.polygon)
        self.assertEqual(self.player.rect.center, (30, 36))
        self.assertEqual(self.player.path_points, [])
        self.assertIsNone(self.player.mouse_target)

    def test_interaction_falls_back_to_legal_node_and_stops_in_range(self):
        obstacle = pygame.Rect(96, 46, 24, 22)
        self.obstacles = [obstacle]
        region = obstacle.inflate(42, 30)
        target = {"rect": obstacle, "interaction_rect": region}
        stop = self.player.get_interaction_stop_point(target)
        self.assertNotEqual(self.player.rect.center, stop)
        route = self.plan((106, 50), region)
        self.assert_route_clear(route)
        self.walk(route, target)
        self.assertTrue(self.player.can_interact(target))
        self.assertIsNone(self.player.interaction_target)

    def test_geometry_and_resize_invalidate_grid_cache(self):
        self.plan((130, 50))
        self.plan((130, 55))
        self.assertEqual(len(self.manager.grid_cache), 1)
        self.obstacles = [pygame.Rect(65, 36, 30, 48)]
        self.assertGreater(len(self.plan((130, 50))), 1)
        self.screen = pygame.Surface((320, 240))
        self.plan((130, 50))
        self.assertEqual(len(self.manager.grid_cache), 3)
        self.assertEqual([key[3] for key in self.manager.grid_cache], [(5, 5), (5, 5), (10, 10)])

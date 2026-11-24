import unittest
from types import SimpleNamespace
from unittest.mock import Mock

import pygame

from controllers.navigation_controller import NavigationController
from managers.interaction_target_manager import InteractionTargetManager
from managers.pathfinding_manager import PathfindingManager
from player import Player


class LayoutScale:
    def scale_x(self, screen, value):
        return value * screen.get_width() / 160

    def scale_y(self, screen, value):
        return value * screen.get_height() / 120


class NavigationControllerTests(unittest.TestCase):
    def setUp(self):
        self.screen = pygame.Surface((160, 120))
        self.player = Player(20, 40, width=20, height=20, speed=140)
        self.game = SimpleNamespace(current_space="T3", has_event=Mock(return_value=False))
        self.objects = {"a": pygame.Rect(110, 45, 15, 12), "b": pygame.Rect(125, 80, 12, 10)}
        self.regions = {key: rect.inflate(30, 30) for key, rect in self.objects.items()}
        self.layout_objects = {"a": {}, "b": {}}
        layout = {"spaces": {"T3": {"objects": self.layout_objects}}}
        self.target_manager = InteractionTargetManager(layout, LayoutScale(), self.game)
        self.interaction = Mock()
        self.pathfinder = PathfindingManager(LayoutScale())
        self.nav = NavigationController(self.pathfinder, self.player, self.game,
                                        self.target_manager, self.interaction)
        self.obstacles = []
        self.polygon = [(0, 0), (159, 0), (159, 119), (0, 119)]

    def click(self, position):
        self.nav.navigate_to_click(
            position, self.screen, self.obstacles, self.polygon, self.objects, self.regions
        )

    def update(self, dt=0.02, pressed_keys=()):
        self.nav.update_player(
            dt, pressed_keys, self.obstacles, self.polygon, self.screen, self.objects, self.regions
        )

    def walk(self):
        for _ in range(200):
            self.update()
            if self.player.mouse_target is None:
                return
        self.fail("Navigation did not finish")

    def test_object_click_navigates_then_opens_exact_target_once(self):
        self.click(self.objects["a"].center)
        self.assertEqual(self.nav.pending_interaction, ("T3", "a"))
        self.assertIsNotNone(self.player.mouse_target)
        self.interaction.open_object.assert_not_called()
        self.walk()
        self.assertTrue(self.target_manager.is_in_interaction_region(
            self.player, "T3", "a", self.regions["a"], self.screen
        ))
        self.update()
        self.interaction.open_object.assert_called_once_with("a")
        self.assertIsNone(self.nav.pending_interaction)

    def test_click_in_padding_only_walks(self):
        point = (99, 51)
        self.assertTrue(self.regions["a"].collidepoint(point))
        self.assertFalse(self.objects["a"].collidepoint(point))
        self.click(point)
        self.assertIsNone(self.nav.pending_interaction)
        self.walk()
        self.assertEqual(self.player.rect.center, point)
        self.interaction.open_object.assert_not_called()

    def test_in_range_click_faces_the_object_before_opening_without_moving(self):
        for center, direction in (((100, 51), 1), ((136, 51), 3), ((117, 35), 0), ((117, 66), 2)):
            with self.subTest(center=center):
                self.player.rect.center = center
                self.player.direction = (direction + 1) % 4
                self.interaction.reset_mock()

                def check_open(object_id):
                    self.assertEqual(object_id, "a")
                    self.assertEqual(self.player.direction, direction)
                    self.assertEqual(self.player.rect.center, center)
                    self.assertFalse(self.player.is_moving)

                self.interaction.open_object.side_effect = check_open
                self.click(self.objects["a"].center)
                self.interaction.open_object.assert_called_once_with("a")
                self.assertIsNone(self.player.mouse_target)

    def test_new_object_replaces_previous_route_and_target(self):
        self.click(self.objects["a"].center)
        prior_path = self.player.path_points.copy()
        self.click(self.objects["b"].center)
        self.assertNotEqual(self.player.path_points, prior_path)
        self.assertEqual(self.nav.pending_interaction, ("T3", "b"))
        self.walk()
        self.interaction.open_object.assert_called_once_with("b")

    def test_ground_click_cancels_previous_target(self):
        self.click(self.objects["a"].center)
        self.click((40, 85))
        self.assertIsNone(self.nav.pending_interaction)
        self.walk()
        self.assertEqual(self.player.rect.center, (40, 85))
        self.interaction.open_object.assert_not_called()

    def test_wasd_cancels_pending_even_when_movement_keys_cancel_out(self):
        self.click(self.objects["a"].center)
        self.update(pressed_keys={pygame.K_a, pygame.K_d})
        self.assertIsNone(self.nav.pending_interaction)
        self.assertIsNone(self.player.mouse_target)
        self.interaction.open_object.assert_not_called()

    def test_no_path_cancels_previous_target(self):
        self.click(self.objects["a"].center)
        self.obstacles.append(pygame.Rect(70, 0, 1, 120))
        start = self.player.rect.center
        self.click(self.objects["b"].center)
        self.assertIsNone(self.nav.pending_interaction)
        self.assertIsNone(self.player.mouse_target)
        self.assertEqual(self.player.rect.center, start)
        self.interaction.open_object.assert_not_called()

    def test_collision_on_existing_route_cancels_pending(self):
        self.click(self.objects["a"].center)
        self.obstacles.append(pygame.Rect(70, 0, 1, 120))
        self.walk()
        self.assertLess(self.player.rect.centerx, 70)
        self.assertIsNone(self.nav.pending_interaction)
        self.interaction.open_object.assert_not_called()

    def test_polygon_is_required_even_when_player_already_overlaps_rectangle(self):
        self.layout_objects["a"]["interaction_polygon"] = [(113, 38), (120, 38), (120, 62), (113, 62)]
        self.player.rect.center = (96, 50)
        self.assertTrue(self.player.rect.colliderect(self.regions["a"]))
        self.click(self.objects["a"].center)
        self.interaction.open_object.assert_not_called()
        self.assertEqual(self.nav.pending_interaction, ("T3", "a"))
        self.walk()
        self.assertTrue(self.target_manager.is_in_interaction_region(
            self.player, "T3", "a", self.regions["a"], self.screen
        ))
        self.interaction.open_object.assert_called_once_with("a")

    def test_arrival_rechecks_polygon_and_rejects_coarse_only_endpoint(self):
        self.layout_objects["a"]["interaction_polygon"] = [(119, 38), (124, 38), (124, 62), (119, 62)]
        self.nav.pathfinding_manager = Mock()
        self.nav.pathfinding_manager.find_path.return_value = [(97, 50)]
        self.click(self.objects["a"].center)
        self.walk()
        self.assertTrue(self.player.rect.colliderect(self.regions["a"]))
        self.assertIsNone(self.nav.pending_interaction)
        self.interaction.open_object.assert_not_called()

    def test_target_hidden_or_space_changed_mid_route(self):
        for change_space in (False, True):
            with self.subTest(change_space=change_space):
                self.click(self.objects["a"].center)
                if change_space:
                    self.game.current_space = "T7"
                else:
                    self.layout_objects["a"]["visible_after_event"] = "visible"
                before = self.player.rect.center
                self.update()
                self.assertEqual(self.player.rect.center, before)
                self.assertIsNone(self.nav.pending_interaction)
                self.assertIsNone(self.player.mouse_target)
                self.layout_objects["a"].clear()
        self.interaction.open_object.assert_not_called()

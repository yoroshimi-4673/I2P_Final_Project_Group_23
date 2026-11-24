"""驗證動畫狀態與既有移動整合，不比對畫面像素。"""
import os
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import pygame
from player import Player

ROOT = Path(__file__).resolve().parent.parent
SPRITE = ROOT / "assets" / "素材庫" / "角色" / "main_character.png"


class PlayerAnimationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.display.init()
        pygame.display.set_mode((800, 600))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        self.player = Player(100, 100, sprite_path=SPRITE)

    def test_original_frames_and_idle(self):
        self.assertEqual(set(self.player.animations), {0, 1, 2, 3})
        sheet_width, sheet_height = pygame.image.load(SPRITE).get_size()
        frame_size = (sheet_width // 4, sheet_height // 4)
        for frames in self.player.animations.values():
            self.assertEqual([frame.get_size() for frame in frames], [frame_size] * 4)
        self.assertEqual((self.player.direction, self.player.frame_index), (0, 0))

    def test_direction_mapping_diagonal_and_stop(self):
        for vector, expected in (((0, 1), 0), ((1, 0), 1), ((0, -1), 2),
                                 ((-1, 0), 3), ((2, -1), 1), ((-1, -1), 2)):
            self.player.update_direction(pygame.Vector2(vector))
            self.assertEqual(self.player.direction, expected)
        self.player.update_direction(pygame.Vector2())
        self.assertEqual(self.player.direction, 2)

    def test_walking_uses_dt_and_stop_returns_idle(self):
        direction = pygame.Vector2(1, 0)
        self.player.update_animation(0.05, direction)
        self.assertEqual(self.player.frame_index, 1)
        self.player.update_animation(0.10, direction)
        self.assertEqual(self.player.frame_index, 3)
        self.player.update_animation(0.15, direction)
        self.assertEqual(self.player.frame_index, 1)
        self.player.update_animation(0.45, direction)
        self.assertEqual(self.player.frame_index, 3)
        self.player.update_animation(0.1, pygame.Vector2())
        self.assertEqual((self.player.frame_index, self.player.animation_timer), (0, 0))
        self.assertFalse(self.player.is_moving)

    def test_keyboard_and_mouse_share_animation(self):
        self.player.update(0.1, {pygame.K_d}, [], 800, 600)
        self.assertEqual(self.player.rect.x, 130)
        self.assertEqual(self.player.direction, 1)
        self.assertTrue(self.player.is_moving)
        self.player.set_mouse_target((150, 20))
        self.player.update(0.1, set(), [], 800, 600)
        self.assertEqual(self.player.direction, 2)
        self.player.cancel_mouse_movement()
        self.player.update(0.1, set(), [], 800, 600)
        self.assertEqual((self.player.direction, self.player.frame_index), (2, 0))

    def test_missing_and_malformed_sheet_fall_back(self):
        with patch("player.pygame.image.load", side_effect=FileNotFoundError):
            player = Player(0, 0, sprite_path="missing.png")
        self.assertFalse(player.animations)
        player.draw(pygame.Surface((100, 100)))
        with patch("player.pygame.image.load", return_value=pygame.Surface((5, 5))):
            self.assertFalse(player._load_sprite_sheet("invalid.png"))

    def test_draw_scales_and_aligns_after_resize(self):
        self.assertEqual(self.player.visual_scale, 1.5)
        frame_width, frame_height = self.player.animations[0][0].get_size()
        for size in ((40, 40), (80, 100), (102, 128)):
            with self.subTest(size=size):
                self.player.rect.size = size
                before = self.player.rect.copy()
                screen = Mock()
                self.player.draw(screen)
                image, rect = screen.blit.call_args.args
                scale = min(before.width / frame_width, before.height / frame_height) * 1.5
                self.assertEqual(image.get_size(), (round(frame_width * scale), round(frame_height * scale)))
                self.assertEqual(rect.midbottom, before.midbottom)
                self.assertEqual(self.player.rect, before)


if __name__ == "__main__":
    unittest.main()

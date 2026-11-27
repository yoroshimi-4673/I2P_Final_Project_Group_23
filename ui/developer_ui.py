import pygame

from controllers.developer_controller import DEV_PRESETS
from ui.dialogue_ui import wrap_text


class DeveloperUI:
    """按下F8鍵進入開發者模式，可以直接滿足條件跳轉到特定章節。"""
    def __init__(self, game_ui):
        self.game_ui = game_ui

    def draw(self, screen, mouse_pos, controller, game, debug_collision):
        shade = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        shade.fill((6, 13, 22, 240))
        screen.blit(shade, (0, 0))
        self._text(screen, "DEVELOPER MODE", 27, 21, large=True)
        self._text(screen, "測試跳轉不代表正式遊戲進度。", 28, 61, color=(248, 203, 132))
        self._text(screen, "F8 關閉", 683, 28)
        self._text(screen, f"Chapter {game.chapter}", 28, 218)
        scene_lines = wrap_text(
            f"Scene: {game.current_scene}", self.game_ui.font_small,
            self.game_ui.scale_x(screen, 174),
        )
        for index, line in enumerate(scene_lines):
            self._text(screen, line, 28, 247 + index * 23)
        y = 251 + len(scene_lines) * 23
        self._text(screen, f"Space: {game.current_space or '—'}", 28, y)
        self._text(screen, f"碰撞除錯：{'ON' if debug_collision else 'OFF'}", 28, y + 27)

        buttons = {}
        for index, category in enumerate(DEV_PRESETS):
            rect = self._rect(screen, 28, 113 + index * 42, 157, 33)
            buttons[category] = rect
            self._row(screen, rect, category, category == controller.category, mouse_pos)

        for index, (preset_id, label) in enumerate(controller.presets):
            rect = self._rect(screen, 218, 105 + index * 33, 550, 29)
            buttons[preset_id] = rect
            self._row(screen, rect, label, index == controller.focused_index, mouse_pos)

        self._text(screen, "← → 切換章節    ↑ ↓ 選擇    Enter 跳轉    Esc / F8 關閉", 28, 558)
        return buttons

    def _rect(self, screen, x, y, width, height):
        return self.game_ui.scale_rect(screen, dict(x=x, y=y, width=width, height=height))

    def _text(self, screen, label, x, y, *, large=False, color=(210, 224, 239)):
        font = self.game_ui.font_large if large else self.game_ui.font_small
        rendered = font.render(label, True, color)
        screen.blit(rendered, (self.game_ui.scale_x(screen, x), self.game_ui.scale_y(screen, y)))

    def _row(self, screen, rect, label, focused, mouse_pos):
        color = (46, 90, 120) if focused else (36, 62, 83) if rect.collidepoint(mouse_pos) else (23, 39, 55)
        pygame.draw.rect(screen, color, rect, border_radius=4)
        if focused:
            pygame.draw.rect(screen, (122, 200, 239), rect, width=1, border_radius=4)
        text = self.game_ui.font_small.render(label, True, (235, 245, 251))
        screen.blit(text, text.get_rect(midleft=(rect.left + 10, rect.centery)))

from datetime import datetime

import pygame

from ui.dialogue_ui import wrap_text


class SaveUI:
    BACKGROUND = (223, 227, 224)
    PANEL = (242, 243, 237)
    INK = (35, 45, 43)
    MUTED = (72, 88, 83)
    BORDER = (116, 134, 128)
    FOCUS = (39, 63, 61)
    ON_FOCUS = (248, 249, 242)

    def __init__(self, game_ui):
        self.game_ui = game_ui
        self.thumbnails = {}

    def _rect(self, screen, x, y, width, height):
        return self.game_ui.scale_rect(screen, dict(x=x, y=y, width=width, height=height))

    def _text(self, screen, text, x, y, *, font=None, color=None, width=None):
        font = font or self.game_ui.font_small
        color = color or self.INK
        text = str(text)
        if width is not None:
            limit = self.game_ui.scale_x(screen, width)
            if font.size(text)[0] > limit:
                text = wrap_text(text, font, max(1, limit - font.size("…")[0]))[0] + "…"
        position = self.game_ui.scale_x(screen, x), self.game_ui.scale_y(screen, y)
        screen.blit(font.render(text, True, color), position)

    def _thumbnail(self, path):
        if path is None:
            return None
        try:
            stamp = path.stat().st_mtime_ns
            cached = self.thumbnails.get(path)
            if cached is None or cached[0] != stamp:
                self.thumbnails[path] = (stamp, pygame.image.load(path).convert_alpha())
            return self.thumbnails[path][1]
        except (OSError, pygame.error):
            return None

    def _buttons(self, screen, mouse, choices, center_x, y, focused_action=None, vertical=False):
        width = 270 if vertical else 150
        x = center_x - (width if vertical else len(choices) * (width + 16) - 16) // 2
        buttons = {}
        for key, label in choices:
            rect = self._rect(screen, x, y, width, 38)
            focused = key == focused_action
            color = self.FOCUS if focused else (93, 110, 106)
            self.game_ui.draw_button(screen, label, rect, rect.collidepoint(mouse), bg_color=color)
            if focused:
                pygame.draw.rect(screen, self.INK, rect.inflate(4, 4), width=2, border_radius=8)
            buttons[key] = rect
            if vertical:
                y += 56
            else:
                x += width + 16
        return buttons

    def draw_background(self, screen, ingame):
        if not ingame:
            screen.fill(self.BACKGROUND)
            return
        shade = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        shade.fill((*self.BACKGROUND, 236))
        screen.blit(shade, (0, 0))

    def draw_title(self, screen, title):
        self._text(screen, title, 55, 32, font=self.game_ui.font_large)
        pygame.draw.rect(screen, self.BORDER, self._rect(screen, 55, 82, 690, 1))

    def draw_footer_hint(self, screen, *, horizontal=False, dismiss_only=False):
        pygame.draw.rect(screen, self.BORDER, self._rect(screen, 55, 544, 690, 1))
        if dismiss_only:
            hint = "Enter 確定    Esc 返回"
        elif horizontal:
            hint = "← → 選擇    Enter 確認    Esc 取消"
        else:
            hint = "↑ ↓ 選擇    Enter 確認    Esc 返回"
        self._text(screen, hint, 55, 561, color=self.MUTED)

    def draw(self, screen, mouse, controller):
        self.draw_background(screen, controller.operation == "save" or controller.return_after_save)
        if controller.mode == "start":
            self.draw_title(screen, "開始遊戲")
            self.draw_footer_hint(screen)
            return self._buttons(
                screen, mouse, controller.action_choices(), 190, 120,
                controller.focused_action, vertical=True,
            )
        if controller.mode == "slots":
            return self.draw_slots(screen, mouse, controller)
        return self.draw_confirmation(screen, mouse, controller)

    def draw_confirmation(self, screen, mouse, controller):
        message, choices = controller.confirmation()
        modal = self._rect(screen, 110, 190, 580, 220)
        pygame.draw.rect(screen, self.PANEL, modal, border_radius=8)
        pygame.draw.rect(screen, self.FOCUS, modal, width=2, border_radius=8)
        font = self.game_ui.font_ui
        width = self.game_ui.scale_x(screen, 524)
        lines = wrap_text(message, font, width)
        y = self.game_ui.scale_y(screen, 231)
        for line in lines:
            surface = font.render(line, True, self.INK)
            screen.blit(surface, surface.get_rect(midtop=(modal.centerx, y)))
            y += font.get_linesize()
        self.draw_footer_hint(screen, horizontal=True, dismiss_only=len(choices) == 1)
        return self._buttons(screen, mouse, choices, 400, 344, controller.focused_action)

    def draw_slots(self, screen, mouse, controller):
        titles = {"new": "新遊戲", "load": "讀取遊戲", "save": "存檔"}
        self.draw_title(screen, titles[controller.operation])
        buttons = {}
        for index, (slot, info) in enumerate(controller.slots.items()):
            y = 105 + 135 * index
            row = self._rect(screen, 55, y, 690, 120)
            focused = controller.focused_slot == slot
            hovered = row.collidepoint(mouse)
            fill = self.FOCUS if focused else (210, 221, 216) if hovered else self.PANEL
            color = self.ON_FOCUS if focused else self.INK
            pygame.draw.rect(screen, fill, row, border_radius=6)
            pygame.draw.rect(screen, self.INK if focused or hovered else self.BORDER,
                             row, width=2 if focused or hovered else 1, border_radius=6)
            self._text(screen, f"SLOT {slot}", 73, y + 7, color=color)
            if slot == controller.active_save_slot:
                self._text(screen, "CURRENT", 660, y + 7, color=color)
            self.draw_thumbnail(screen, info, y)
            self.draw_slot_metadata(screen, info, y, color)
            buttons[slot] = row
        self.draw_footer_hint(screen)
        buttons.update(self._buttons(screen, mouse, (("back", "返回"),), 670, 552))
        return buttons

    def draw_thumbnail(self, screen, info, y):
        preview = self._rect(screen, 73, y + 30, 135, 84)
        pygame.draw.rect(screen, (179, 192, 187), preview)
        image = self._thumbnail(info["thumbnail_path"])
        if image is not None:
            scaled = self.game_ui.scale_image_to_fit(image, preview)
            screen.blit(scaled, scaled.get_rect(center=preview.center))
        else:
            label = "NO IMAGE" if info["exists"] else "—"
            text = self.game_ui.font_small.render(label, True, self.INK)
            screen.blit(text, text.get_rect(center=preview.center))

    def draw_slot_metadata(self, screen, info, y, color):
        font = self.game_ui.font_ui
        if not info["exists"]:
            status = "CORRUPTED DATA" if info["status"] == "CORRUPTED" else "NO DATA"
            self._text(screen, status, 234, y + 54, font=font, color=color)
            return

        metadata = info["metadata"]
        self._text(screen, metadata.get("chapter_name", ""), 234, y + 28, font=font, color=color, width=275)
        self._text(screen, metadata.get("space_name", ""), 234, y + 60, font=font, color=color, width=275)
        seconds = max(0, int(metadata.get("play_time", 0)))
        hours, minutes = divmod(seconds // 60, 60)
        self._text(screen, "PLAY TIME", 526, y + 30, color=color)
        self._text(screen, f"{hours:02d}:{minutes:02d}:{seconds % 60:02d}", 526, y + 54, font=font, color=color)

        saved_at = str(metadata.get("saved_at", ""))
        try:
            date = datetime.fromisoformat(saved_at)
        except ValueError:
            self._text(screen, saved_at, 526, y + 85, color=color, width=205)
        else:
            self._text(screen, date.strftime("%Y-%m-%d"), 634, y + 53, color=color)
            self._text(screen, date.strftime("%H:%M"), 634, y + 79, color=color)

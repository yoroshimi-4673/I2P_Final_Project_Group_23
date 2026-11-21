import pygame

from ui.dialogue_ui import wrap_text


class SaveUI:
    def __init__(self, game_ui):
        self.game_ui = game_ui
        self.thumbnails = {}

    def _text(self, screen, text, position, *, large=False, color=(232, 238, 247)):
        font = self.game_ui.font_large if large else self.game_ui.font_small
        screen.blit(font.render(str(text), True, color), position)

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

    def _buttons(self, screen, mouse, choices, center_x, y, available_width):
        width = min(160, (available_width - 16 * (len(choices) - 1)) // len(choices))
        x = center_x - (len(choices) * width + (len(choices) - 1) * 16) // 2
        buttons = {}
        for key, label in choices:
            rect = pygame.Rect(x, y, width, 38)
            self.game_ui.draw_button(screen, label, rect, rect.collidepoint(mouse))
            buttons[key] = rect
            x += width + 16
        return buttons

    def draw(self, screen, mouse, controller):
        shade = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        shade.fill((5, 11, 20, 222))
        screen.blit(shade, (0, 0))
        if controller.mode == "start":
            center_x, center_y = screen.get_rect().center
            self._text(screen, "開始遊戲", (center_x - 70, center_y - 85), large=True)
            return self._buttons(
                screen, mouse, (("new", "新遊戲"), ("load", "讀取遊戲"), ("back", "返回")),
                center_x, center_y, screen.get_width() - 60,
            )
        if controller.mode == "slots":
            return self.draw_slots(screen, mouse, controller)

        message, choices = controller.confirmation()
        modal = pygame.Rect(0, 0, min(580, screen.get_width() - 60), 220)
        modal.center = screen.get_rect().center
        pygame.draw.rect(screen, (24, 39, 56), modal, border_radius=12)
        pygame.draw.rect(screen, (102, 151, 182), modal, width=1, border_radius=12)
        font = self.game_ui.font_small
        for index, line in enumerate(wrap_text(message, font, modal.width - 52)):
            self._text(screen, line, (modal.x + 26, modal.y + 35 + index * font.get_linesize()))
        return self._buttons(screen, mouse, choices, modal.centerx, modal.bottom - 60, modal.width - 38)

    def draw_slots(self, screen, mouse, controller):
        width = min(700, screen.get_width() - 44)
        x = (screen.get_width() - width) // 2
        height = min(135, (screen.get_height() - 145) // 3)
        y = 60
        titles = {"new": "新遊戲", "load": "讀取遊戲", "save": "存檔"}
        self._text(screen, titles[controller.operation], (x, 16), large=True)
        buttons = {}
        for slot, info in controller.slots.items():
            row = pygame.Rect(x, y, width, height)
            hovered = row.collidepoint(mouse)
            pygame.draw.rect(screen, (38, 66, 88) if hovered else (23, 39, 56), row, border_radius=8)
            pygame.draw.rect(screen, (123, 197, 233) if hovered else (59, 85, 108),
                             row, width=2 if hovered else 1, border_radius=8)
            preview = pygame.Rect(row.x + 12, row.y + 10, min(156, width // 3), height - 20)
            pygame.draw.rect(screen, (10, 17, 27), preview)
            image = self._thumbnail(info["thumbnail_path"])
            if image is not None:
                scaled = self.game_ui.scale_image_to_fit(image, preview)
                screen.blit(scaled, scaled.get_rect(center=preview.center))
            elif info["exists"]:
                self._text(screen, "NO IMAGE", (preview.x + 12, preview.centery - 10))
            label_x = preview.right + 16
            status = "CORRUPTED DATA" if info["status"] == "CORRUPTED" else info["status"]
            self._text(screen, f"SLOT {slot}   {status}", (label_x, y + 8), color=(145, 213, 245))
            if info["exists"]:
                metadata = info["metadata"]
                seconds = max(0, int(metadata.get("play_time", 0)))
                hours, minutes = divmod(seconds // 60, 60)
                self._text(screen, f'{metadata.get("chapter_name", "")} · {metadata.get("space_name", "")}', (label_x, y + 31))
                self._text(screen, f"{hours:02d}:{minutes:02d}:{seconds % 60:02d}", (label_x, y + 54))
                self._text(screen, str(metadata.get("saved_at", "")).replace("T", " "), (label_x, y + 77))
            buttons[slot] = row
            y += height + 8
        buttons.update(self._buttons(screen, mouse, (("back", "返回"),), screen.get_width() // 2, y + 6, width))
        return buttons

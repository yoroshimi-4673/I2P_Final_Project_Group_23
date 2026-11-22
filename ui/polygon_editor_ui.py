import pygame


class PolygonEditorUI:
    def __init__(self, font_ui, font_small):
        self.font_ui = font_ui
        self.font_small = font_small

    def draw(self, surface, controller):
        """繪製鍵盤操作的Polygon邊界編輯器。"""

        base_points = controller.points
        cursor_base = controller.cursor
        space_id = controller.space_id

        screen_points = [
            controller.base_to_screen(point, surface)
            for point in base_points
        ]

        cursor_screen = controller.base_to_screen(cursor_base, surface)

        if len(screen_points) >= 3:
            overlay = pygame.Surface(
                surface.get_size(),
                pygame.SRCALPHA
            )

            pygame.draw.polygon(
                overlay,
                (0, 200, 255, 45),
                screen_points
            )

            surface.blit(
                overlay,
                (0, 0)
            )

        if len(screen_points) >= 2:
            pygame.draw.lines(
                surface,
                (0, 230, 255),
                False,
                screen_points,
                width=3
            )

        if screen_points:
            pygame.draw.line(
                surface,
                (120, 245, 255),
                screen_points[-1],
                cursor_screen,
                width=2
            )

        if len(screen_points) >= 3:
            pygame.draw.line(
                surface,
                (0, 190, 230),
                screen_points[-1],
                screen_points[0],
                width=2
            )

        for index, (screen_point, base_point) in enumerate(
            zip(screen_points, base_points)
        ):
            pygame.draw.circle(
                surface,
                (0, 245, 255),
                screen_point,
                6
            )

            label = self.font_small.render(
                f"{index}: ({base_point[0]}, {base_point[1]})",
                True,
                (220, 255, 255)
            )

            surface.blit(
                label,
                (screen_point[0] + 8, screen_point[1] - 18)
            )

        pygame.draw.circle(
            surface,
            (255, 230, 60),
            cursor_screen,
            8,
            width=2
        )

        pygame.draw.line(
            surface,
            (255, 230, 60),
            (cursor_screen[0] - 12, cursor_screen[1]),
            (cursor_screen[0] + 12, cursor_screen[1]),
            width=1
        )

        pygame.draw.line(
            surface,
            (255, 230, 60),
            (cursor_screen[0], cursor_screen[1] - 12),
            (cursor_screen[0], cursor_screen[1] + 12),
            width=1
        )

        cursor_x = round(cursor_base[0])
        cursor_y = round(cursor_base[1])

        info_lines = [
            f"Polygon Editor / Space {space_id}",
            f"Cursor: ({cursor_x}, {cursor_y})",
            f"Vertices: {len(base_points)}",
            "Mouse: move; Arrows: 1px, hold 2s to move",
            "Left click / Space: add; Right click / Backspace / Delete: undo",
            "R：清空   Enter：套用並輸出JSON",
            "F2 / Esc：離開編輯模式"
        ]

        panel_width = min(
            500,
            surface.get_width() - 20
        )

        panel_height = 24 + len(info_lines) * 21

        panel_rect = pygame.Rect(
            10,
            10,
            panel_width,
            panel_height
        )

        panel = pygame.Surface(
            panel_rect.size,
            pygame.SRCALPHA
        )

        panel.fill((10, 20, 28, 215))
        surface.blit(panel, panel_rect)

        y = panel_rect.y + 9

        for index, line in enumerate(info_lines):
            font = (
                self.font_ui
                if index == 0
                else self.font_small
            )

            color = (
                (120, 245, 255)
                if index == 0
                else (230, 240, 245)
            )

            text_surface = font.render(
                line,
                True,
                color
            )

            surface.blit(
                text_surface,
                (panel_rect.x + 10, y)
            )

            y += 25 if index == 0 else 21

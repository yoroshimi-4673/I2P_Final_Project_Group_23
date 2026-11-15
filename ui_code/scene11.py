import pygame
import sys

pygame.init()
screen = pygame.display.set_mode((800, 600))
pygame.display.set_caption("Scene 11")

clock = pygame.time.Clock()
font_ui = pygame.font.SysFont("microsoftjhenghei", 16)

BG_COLOR = (50, 52, 60)
BOX_FILL = (78, 81, 94)
BOX_BORDER = (180, 185, 198)
TEXT_COLOR = (205, 210, 220)

def draw_box(rect, text):
    pygame.draw.rect(screen, BOX_FILL, rect, border_radius=8)
    pygame.draw.rect(screen, BOX_BORDER, rect, 2, border_radius=8)
    surf = font_ui.render(text, True, TEXT_COLOR)
    screen.blit(surf, surf.get_rect(center=rect.center))

running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    screen.fill(BG_COLOR)

    draw_box(pygame.Rect(330, 70, 140, 45), "門框")
    draw_box(pygame.Rect(550, 70, 120, 45), "牆上的日曆")
    draw_box(pygame.Rect(60, 230, 200, 115), "斷裂的床")
    draw_box(pygame.Rect(630, 340, 110, 150), "書桌")
    draw_box(pygame.Rect(630, 395, 40, 35), "信")

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
sys.exit()

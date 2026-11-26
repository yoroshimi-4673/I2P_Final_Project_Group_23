import pygame
import sys

pygame.init()
screen = pygame.display.set_mode((800, 600))
pygame.display.set_caption("Scene 9")

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

    # 門牌 (T-3, T+0, T+7) 與三扇門
    draw_box(pygame.Rect(155, 95, 90, 35), "T-3")
    draw_box(pygame.Rect(355, 95, 90, 35), "T+0")
    draw_box(pygame.Rect(555, 95, 90, 35), "T+7")

    draw_box(pygame.Rect(125, 145, 150, 340), "門 T-3")
    draw_box(pygame.Rect(325, 145, 150, 340), "門 T+0")
    draw_box(pygame.Rect(525, 145, 150, 340), "門 T+7")

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
sys.exit()

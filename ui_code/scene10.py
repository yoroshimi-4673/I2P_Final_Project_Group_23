import pygame
import sys

pygame.init()
screen = pygame.display.set_mode((800, 600))
pygame.display.set_caption("Scene 10")

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

    draw_box(pygame.Rect(120, 70, 130, 35), "窗簾")
    draw_box(pygame.Rect(330, 70, 140, 45), "門框")
    draw_box(pygame.Rect(50, 130, 100, 65), "床頭桌")
    draw_box(pygame.Rect(50, 210, 210, 115), "床")
    draw_box(pygame.Rect(62, 232, 55, 70), "枕頭")
    draw_box(pygame.Rect(50, 340, 110, 65), "床頭抽屜")
    draw_box(pygame.Rect(50, 425, 120, 75), "兒童保險箱")
    draw_box(pygame.Rect(610, 130, 130, 340), "裝飾區")

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
sys.exit()

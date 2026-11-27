import pygame
import sys

pygame.init()
screen = pygame.display.set_mode((800, 600))
pygame.display.set_caption("Scene 13")

clock = pygame.time.Clock()
font_ui = pygame.font.SysFont("microsoftjhenghei", 20)

BG_COLOR = (50, 52, 60)
BOX_FILL = (78, 81, 94)
BOX_BORDER = (180, 185, 198)
TEXT_COLOR = (205, 210, 220)

def draw_u_groove(rect, label):
    wall_thick = 25
    # 1. 畫出外層凹槽牆體
    pygame.draw.rect(screen, BOX_FILL, rect, border_radius=8)
    pygame.draw.rect(screen, BOX_BORDER, rect, 2, border_radius=8)

    # 2. 挖空內部凹槽（填上與螢幕相同的背景色，並保留左、下、右內框線）
    inner = pygame.Rect(rect.x + wall_thick, rect.y, rect.width - wall_thick * 2, rect.height - wall_thick)
    pygame.draw.rect(screen, BG_COLOR, inner)
    pygame.draw.line(screen, BOX_BORDER, inner.topleft, inner.bottomleft, 2)
    pygame.draw.line(screen, BOX_BORDER, inner.bottomleft, inner.bottomright, 2)
    pygame.draw.line(screen, BOX_BORDER, inner.bottomright, inner.topright, 2)

    # 3. 蓋掉上方開口處的框線，使其與背景連通
    pygame.draw.line(screen, BG_COLOR, (inner.left + 1, rect.top), (inner.right - 1, rect.top), 4)

    # 4. 繪製下方文字標籤
    surf = font_ui.render(label, True, TEXT_COLOR)
    screen.blit(surf, surf.get_rect(center=(rect.centerx, rect.bottom + 25)))

running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    screen.fill(BG_COLOR)

    channels = [
        (pygame.Rect(100, 140, 160, 280), "(過去)"),
        (pygame.Rect(320, 140, 160, 280), "(現在)"),
        (pygame.Rect(540, 140, 160, 280), "(未來)")
    ]
    for rect, label in channels:
        draw_u_groove(rect, label)

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
sys.exit()

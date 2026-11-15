import pygame
import sys
import os

pygame.init()
screen = pygame.display.set_mode((800, 600))
pygame.display.set_caption("Scene 11")

clock = pygame.time.Clock()
font_ui = pygame.font.SysFont("microsoftjhenghei", 16)

BG_COLOR = (50, 52, 60)
BOX_FILL = (78, 81, 94)
BOX_BORDER = (180, 185, 198)
TEXT_COLOR = (205, 210, 220)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

FOLDERS = [os.path.join(BASE_DIR, "..", "assets", "素材庫", "第二章", "T+7")]

def load_img(filename, size):
    if not filename:
        return None
    for folder in FOLDERS:
        path = os.path.join(folder, filename)
        if os.path.exists(path):
            try:
                img = pygame.image.load(path).convert_alpha()
                return pygame.transform.scale(img, size)
            except Exception:
                pass
    return None

def draw_box(rect, text, img=None):
    if img:
        screen.blit(img, rect.topleft)
    else:
        pygame.draw.rect(screen, BOX_FILL, rect, border_radius=8)
        pygame.draw.rect(screen, BOX_BORDER, rect, 2, border_radius=8)
        surf = font_ui.render(text, True, TEXT_COLOR)
        screen.blit(surf, surf.get_rect(center=rect.center))

# 背景圖
bg_img = load_img("background.png", (800, 600))

items = [
    (pygame.Rect(570, 90, 60, 50),  "牆上的日曆", "date.png"),
    (pygame.Rect(100, 230, 150, 115), "斷裂的床",   "bed.png"),
    (pygame.Rect(600, 170, 100, 120),"書桌",       "desk_drawer.png"),
    (pygame.Rect(630, 190, 30, 24),  "信",         "letter.png"),
]

loaded_items = [(rect, text, load_img(fname, rect.size)) for rect, text, fname in items]

running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    screen.fill(BG_COLOR)

    if bg_img:
        screen.blit(bg_img, (0, 0))

    for rect, text, img in loaded_items:
        draw_box(rect, text, img)

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
sys.exit()

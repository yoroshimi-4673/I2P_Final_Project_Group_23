import pygame
import math
import sys

# 1. 初始化 Pygame 與設定畫布 (800x600 視窗)
pygame.init()
SCREEN_WIDTH, SCREEN_HEIGHT = 800, 600
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("點擊移動 (走過的地方虛線消失)")
clock = pygame.time.Clock()

# 顏色定義 (RGB)
BG_COLOR = (30, 30, 40)       # 深藍灰色背景
SQUARE_COLOR = (50, 205, 50)  # 綠色正方形
TARGET_COLOR = (255, 215, 0)  # 黃色目標點/虛線

# 正方形屬性
square_size = 40
square_pos = [380.0, 280.0]  # 正方形即時座標 [x, y]
target_pos = list(square_pos) # 目標點座標
move_speed = 6.0             # 移動速度

def draw_dashed_line(surface, color, start_pos, end_pos, width=2, dash_length=12, space_length=14):
    """繪製兩點之間的虛線函數"""
    x1, y1 = start_pos
    x2, y2 = end_pos
    dx = x2 - x1
    dy = y2 - y1
    distance = math.hypot(dx, dy)
    
    if distance == 0:
        return

    ux = dx / distance
    uy = dy / distance

    current_dist = 0.0
    while current_dist < distance:
        start_dash = (x1 + ux * current_dist, y1 + uy * current_dist)
        end_dash_dist = min(current_dist + dash_length, distance)
        end_dash = (x1 + ux * end_dash_dist, y1 + uy * end_dash_dist)
        
        pygame.draw.line(surface, color, start_dash, end_dash, width)
        current_dist += dash_length + space_length

# 2. 主迴圈
running = True
while running:
    # --- 事件處理 ---
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        
        # 偵測滑鼠左鍵點擊
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            target_pos[0] = event.pos[0] - square_size / 2
            target_pos[1] = event.pos[1] - square_size / 2

    # --- 計算移動 (向量與距離) ---
    dx = target_pos[0] - square_pos[0]
    dy = target_pos[1] - square_pos[1]
    distance = math.hypot(dx, dy)

    if distance > move_speed:
        square_pos[0] += (dx / distance) * move_speed
        square_pos[1] += (dy / distance) * move_speed
    else:
        # 到達目的地
        square_pos[0] = target_pos[0]
        square_pos[1] = target_pos[1]

    # --- 繪製畫面 ---
    screen.fill(BG_COLOR)

    # 只要還沒到達目標，就繪製從「正方形中心」到「目標圓點」的剩餘路徑
    if square_pos != target_pos:
        # 當前正方形中心點 (作為虛線的動態起點)
        square_center = (
            int(square_pos[0] + square_size / 2),
            int(square_pos[1] + square_size / 2)
        )
        # 目標點中心
        target_center = (
            int(target_pos[0] + square_size / 2),
            int(target_pos[1] + square_size / 2)
        )

        # 1. 繪製從「正方形當前位置」到「目標點」的虛線 (只畫前方未走過的部分)
        draw_dashed_line(screen, TARGET_COLOR, square_center, target_center, width=2, dash_length=12, space_length=14)

        # 2. 繪製目標空心圓
        pygame.draw.circle(screen, TARGET_COLOR, target_center, 15, width=2)

    # 3. 繪製正方形
    square_rect = pygame.Rect(int(square_pos[0]), int(square_pos[1]), square_size, square_size)
    pygame.draw.rect(screen, SQUARE_COLOR, square_rect)

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
sys.exit()

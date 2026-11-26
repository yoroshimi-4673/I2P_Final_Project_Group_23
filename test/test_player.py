import pygame
import sys
import math
from pathlib import Path


# 將專案根目錄加入Python搜尋路徑
ROOT_DIR = (
    Path(__file__)
    .resolve()
    .parent
    .parent
)

sys.path.append(
    str(ROOT_DIR)
)

from player import Player


pygame.init()

# 停止文字輸入模式避免影響鍵盤事件
pygame.key.stop_text_input()


SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600


screen = pygame.display.set_mode(
    (
        SCREEN_WIDTH,
        SCREEN_HEIGHT
    )
)

pygame.display.set_caption(
    "Player完整功能測試"
)


# 建立Clock控制FPS與delta time
clock = pygame.time.Clock()


# ============================================================
# 顏色設定
# ============================================================

BG_COLOR = (
    30,
    30,
    40
)

WALL_COLOR = (
    100,
    100,
    120
)

OBJECT_COLOR = (
    180,
    120,
    70
)

INTERACTION_COLOR = (
    80,
    140,
    180
)

TARGET_COLOR = (
    255,
    215,
    0
)


# ============================================================
# 虛線繪製函式
# ============================================================

def draw_dashed_line(
    surface,
    color,
    start_pos,
    end_pos,
    width=2,
    dash_length=12,
    space_length=14
):
    """繪製兩個位置之間的虛線。"""

    # 取得虛線起點與終點座標
    x1, y1 = start_pos
    x2, y2 = end_pos

    # 計算兩點之間水平與垂直差距
    dx = x2 - x1
    dy = y2 - y1

    # 計算兩點之間的實際距離
    distance = math.hypot(
        dx,
        dy
    )

    # 起點終點相同時不需要繪製
    if distance == 0:
        return

    # 計算虛線方向的單位向量
    ux = dx / distance
    uy = dy / distance

    # 記錄目前已經繪製的距離
    current_dist = 0.0

    # 沿著路徑持續繪製每段虛線
    while current_dist < distance:

        start_dash = (
            x1 + ux * current_dist,
            y1 + uy * current_dist
        )

        end_dash_dist = min(
            current_dist + dash_length,
            distance
        )

        end_dash = (
            x1 + ux * end_dash_dist,
            y1 + uy * end_dash_dist
        )

        pygame.draw.line(
            surface,
            color,
            start_dash,
            end_dash,
            width
        )

        current_dist += (
            dash_length
            + space_length
        )


# ============================================================
# Player設定
# ============================================================

player = Player(
    x=100,
    y=100,
    width=40,
    height=40,
    speed=300
)


# ============================================================
# 測試用牆壁
# ============================================================

walls = [
    pygame.Rect(
        250,
        100,
        40,
        300
    ),

    pygame.Rect(
        450,
        350,
        250,
        40
    )
]


# ============================================================
# 測試互動物件
# ============================================================

bed_rect = pygame.Rect(
    550,
    150,
    120,
    70
)

bed = {
    "id": "bed",

    "rect": bed_rect,

    # 比物件本身上下左右各增加40像素
    "interaction_rect": (
        bed_rect.inflate(
            80,
            80
        )
    )
}


# ============================================================
# 所有不可通過區域
# ============================================================

obstacles = (
    walls
    + [
        bed[
            "rect"
        ]
    ]
)


# ============================================================
# 按鍵狀態
# ============================================================

# 儲存目前仍然被按住的鍵盤按鍵
pressed_keys = set()


# ============================================================
# 主遊戲迴圈
# ============================================================

running = True

while running:

    # 取得上一幀到現在經過的秒數
    dt = (
        clock.tick(60)
        / 1000
    )


    # ========================================================
    # Event處理
    # ========================================================

    for event in pygame.event.get():

        # 使用者關閉視窗時結束程式
        if event.type == pygame.QUIT:

            running = False


        # 按鍵按下時加入正在按住的集合
        elif event.type == pygame.KEYDOWN:

            pressed_keys.add(
                event.key
            )

            print(
                "KEYDOWN:",
                pygame.key.name(
                    event.key
                ),
                [
                    pygame.key.name(key)
                    for key
                    in pressed_keys
                ]
            )


        # 按鍵放開時從集合中移除按鍵
        elif event.type == pygame.KEYUP:

            pressed_keys.discard(
                event.key
            )

            print(
                "KEYUP:",
                pygame.key.name(
                    event.key
                ),
                [
                    pygame.key.name(key)
                    for key
                    in pressed_keys
                ]
            )


        # 視窗失去焦點時清除所有按鍵狀態
        elif event.type == pygame.WINDOWFOCUSLOST:

            pressed_keys.clear()

            print(
                "Keyboard state cleared"
            )


        # 滑鼠左鍵點擊時設定移動目標
        elif (
            event.type
            == pygame.MOUSEBUTTONDOWN
            and event.button == 1
        ):

            mouse_pos = (
                event.pos
            )


            # 點到床代表想與床進行互動
            if bed[
                "rect"
            ].collidepoint(
                mouse_pos
            ):

                player.set_interaction_target(
                    bed
                )

                print(
                    "目標：前往床邊"
                )


            # 點到其他地方則進行一般移動
            else:

                player.set_mouse_target(
                    mouse_pos
                )

                print(
                    "移動目標：",
                    mouse_pos
                )


    # ========================================================
    # 鍵盤狀態除錯
    # ========================================================

    # 有按鍵被記錄時顯示目前按鍵狀態
    if pressed_keys:

        print(
            "pressed:",
            [
                pygame.key.name(key)
                for key
                in pressed_keys
            ]
        )


    # ========================================================
    # Player更新
    # ========================================================

    interaction = player.update(
        dt,
        pressed_keys,
        obstacles,
        SCREEN_WIDTH,
        SCREEN_HEIGHT
    )


    # 玩家成功進入物件互動範圍
    if interaction is not None:

        print(
            "Interact with:",
            interaction[
                "id"
            ]
        )


    # ========================================================
    # Render
    # ========================================================

    # 清除上一幀並填入背景顏色
    screen.fill(
        BG_COLOR
    )


    # 繪製所有測試牆壁
    for wall in walls:

        pygame.draw.rect(
            screen,
            WALL_COLOR,
            wall
        )


    # 顯示床的互動範圍
    pygame.draw.rect(
        screen,
        INTERACTION_COLOR,
        bed[
            "interaction_rect"
        ],
        width=2
    )


    # 繪製床本身的碰撞矩形
    pygame.draw.rect(
        screen,
        OBJECT_COLOR,
        bed[
            "rect"
        ]
    )


    # ========================================================
    # 滑鼠移動路徑顯示
    # ========================================================

    if player.mouse_target is not None:

        # 取得目前玩家矩形的中心位置
        player_center = (
            player.rect.centerx,
            player.rect.centery
        )

        # 取得目前滑鼠目標中心位置
        target_center = (
            round(
                player.mouse_target.x
            ),
            round(
                player.mouse_target.y
            )
        )

        # 繪製玩家到目標之間的剩餘虛線
        draw_dashed_line(
            screen,
            TARGET_COLOR,
            player_center,
            target_center,
            width=2,
            dash_length=12,
            space_length=14
        )

        # 繪製目前滑鼠目標的空心圓
        pygame.draw.circle(
            screen,
            TARGET_COLOR,
            target_center,
            15,
            width=2
        )


    # ========================================================
    # Player繪製
    # ========================================================

    # 將Player繪製到目前畫面
    player.draw(
        screen
    )


    # 將完成的畫面顯示到視窗
    pygame.display.flip()


pygame.quit()
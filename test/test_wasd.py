import pygame

pygame.init()

pygame.key.stop_text_input()

SCREEN_WIDTH, SCREEN_HEIGHT = 800, 600

screen = pygame.display.set_mode(
    (SCREEN_WIDTH, SCREEN_HEIGHT)
)

pygame.display.set_caption(
    "上下左右移動(wasd)測試"
)

# 玩家矩形，用來記錄位置與碰撞範圍
player = pygame.Rect(350, 250, 40, 40)

# 測試用牆壁矩形
walls = [
    pygame.Rect(200, 150, 300, 40),
    pygame.Rect(500, 300, 40, 200),
    pygame.Rect(150, 450, 350, 40)
]

# 使用浮點向量保存玩家精確位置資訊
player_pos = pygame.Vector2(player.x, player.y)

# 顏色定義
BG_COLOR = (30, 30, 40)
SQUARE_COLOR = (50, 205, 50)

# 畫面上實際顯示的正方形大小
square_size = 40

# 玩家每秒移動的像素距離
player_speed = 300

# 建立 Clock 控制 FPS 與 delta time
clock = pygame.time.Clock()

# 儲存目前仍然被按住的鍵盤按鍵
pressed_keys = set()

running = True

while running:

    # 取得上一幀到目前經過的秒數
    dt = clock.tick(60) / 1000

    # 處理本幀所有 pygame 事件
    for event in pygame.event.get():

        # 使用者關閉視窗時結束遊戲迴圈
        if event.type == pygame.QUIT:
            running = False

        # 按鍵按下時加入正在按住的集合
        elif event.type == pygame.KEYDOWN:

            pressed_keys.add(event.key)

            print(
                "KEYDOWN:",
                pygame.key.name(event.key),
                pressed_keys
            )

        # 按鍵放開時從集合中移除該按鍵
        elif event.type == pygame.KEYUP:

            pressed_keys.discard(
                event.key
            )

            print(
                "KEYUP:",
                pygame.key.name(event.key),
                pressed_keys
            )

    # 建立本幀玩家移動方向向量
    direction = pygame.Vector2(0, 0)

    # 左方向鍵或 A 被按住時向左移動
    if (
        pygame.K_LEFT in pressed_keys
        or pygame.K_a in pressed_keys
    ):
        direction.x -= 1

    # 右方向鍵或 D 被按住時向右移動
    if (
        pygame.K_RIGHT in pressed_keys
        or pygame.K_d in pressed_keys
    ):
        direction.x += 1

    # 上方向鍵或 W 被按住時向上移動
    if (
        pygame.K_UP in pressed_keys
        or pygame.K_w in pressed_keys
    ):
        direction.y -= 1

    # 下方向鍵或 S 被按住時向下移動
    if (
        pygame.K_DOWN in pressed_keys
        or pygame.K_s in pressed_keys
    ):
        direction.y += 1

    # 有移動方向時將向量正規化，避免斜向移動速度較快
    if direction.length_squared() > 0:

        direction = (
            direction.normalize()
        )

    # 計算本幀水平移動距離
    move_x = (
        direction.x
        * player_speed
        * dt
    )

    player_pos.x += move_x
    player.x = round(player_pos.x)

    # 處理水平碰撞
    for wall in walls:

        if player.colliderect(wall):

            if move_x > 0:
                player.right = wall.left

            elif move_x < 0:
                player.left = wall.right

            player_pos.x = player.x

    # 計算本幀垂直移動距離
    move_y = (
        direction.y
        * player_speed
        * dt
    )

    player_pos.y += move_y
    player.y = round(player_pos.y)

    # 處理垂直碰撞
    for wall in walls:

        if player.colliderect(wall):

            if move_y > 0:
                player.bottom = wall.top

            elif move_y < 0:
                player.top = wall.bottom

            player_pos.y = player.y

    # 將玩家浮點位置限制在畫面範圍內
    player_pos.x = max(
        0,
        min(
            player_pos.x,
            SCREEN_WIDTH - player.width
        )
    )

    player_pos.y = max(
        0,
        min(
            player_pos.y,
            SCREEN_HEIGHT - player.height
        )
    )

    # 將浮點座標同步回 pygame Rect
    player.x = round(
        player_pos.x
    )

    player.y = round(
        player_pos.y
    )

    # 清除上一幀畫面並填入背景顏色
    screen.fill(
        BG_COLOR
    )

    # 使用玩家位置建立實際顯示的方塊
    square_rect = pygame.Rect(
        player.x,
        player.y,
        square_size,
        square_size
    )

    # 將玩家方塊繪製到目前畫面上
    pygame.draw.rect(
        screen,
        SQUARE_COLOR,
        square_rect
    )

    # 繪製測試牆壁
    for wall in walls:

        pygame.draw.rect(
            screen,
            (120, 120, 140),
            wall
        )

    # 將這一幀完成的畫面顯示出來
    pygame.display.flip()

pygame.quit()
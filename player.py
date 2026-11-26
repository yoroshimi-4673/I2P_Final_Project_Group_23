import pygame


class Player:
    """管理玩家位置、移動、碰撞與顯示範圍。"""

    def __init__(
        self,
        x,
        y,
        width=40,
        height=40,
        speed=300
    ):
        # 建立玩家矩形，用來記錄位置與碰撞範圍
        self.rect = pygame.Rect(
            x,
            y,
            width,
            height
        )

        # 使用浮點向量保存玩家精確位置資訊
        self.position = pygame.Vector2(x, y)

        # 儲存玩家每秒移動的像素距離
        self.speed = speed

    def get_direction(
        self,
        pressed_keys
    ):
        """依照目前按住的按鍵取得移動方向。"""

        # 建立本幀玩家移動方向向量
        direction = pygame.Vector2(
            0,
            0
        )

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

        # 正規化方向向量，避免斜向移動速度較快
        if direction.length_squared() > 0:

            direction = (
                direction.normalize()
            )

        return direction

    def move_x(
        self,
        move_x,
        obstacles
    ):
        """處理玩家水平方向移動與碰撞。"""

        # 更新玩家精確水平位置
        self.position.x += move_x

        # 將浮點位置同步到玩家矩形
        self.rect.x = round(
            self.position.x
        )

        # 逐一檢查所有不可通過物件
        for obstacle in obstacles:

            # 判斷玩家是否與障礙物發生碰撞
            if self.rect.colliderect(
                obstacle
            ):

                # 向右移動時貼齊障礙物左側
                if move_x > 0:

                    self.rect.right = (
                        obstacle.left
                    )

                # 向左移動時貼齊障礙物右側
                elif move_x < 0:

                    self.rect.left = (
                        obstacle.right
                    )

                # 碰撞修正後同步浮點水平位置
                self.position.x = (
                    self.rect.x
                )

    def move_y(
        self,
        move_y,
        obstacles
    ):
        """處理玩家垂直方向移動與碰撞。"""

        # 更新玩家精確垂直位置
        self.position.y += move_y

        # 將浮點位置同步到玩家矩形
        self.rect.y = round(
            self.position.y
        )

        # 逐一檢查所有不可通過物件
        for obstacle in obstacles:

            # 判斷玩家是否與障礙物發生碰撞
            if self.rect.colliderect(
                obstacle
            ):

                # 向下移動時貼齊障礙物上側
                if move_y > 0:

                    self.rect.bottom = (
                        obstacle.top
                    )

                # 向上移動時貼齊障礙物下側
                elif move_y < 0:

                    self.rect.top = (
                        obstacle.bottom
                    )

                # 碰撞修正後同步浮點垂直位置
                self.position.y = (
                    self.rect.y
                )

    def keep_inside_bounds(
        self,
        screen_width,
        screen_height
    ):
        """限制玩家不能離開目前畫面範圍。"""

        # 限制玩家水平位置在畫面範圍內
        self.position.x = max(
            0,
            min(
                self.position.x,
                screen_width
                - self.rect.width
            )
        )

        # 限制玩家垂直位置在畫面範圍內
        self.position.y = max(
            0,
            min(
                self.position.y,
                screen_height
                - self.rect.height
            )
        )

        # 將修正後位置同步回玩家矩形
        self.rect.x = round(
            self.position.x
        )

        self.rect.y = round(
            self.position.y
        )

    def update(
        self,
        dt,
        pressed_keys,
        obstacles,
        screen_width,
        screen_height
    ):
        """更新玩家移動、碰撞與畫面邊界。"""

        # 取得本幀玩家移動方向
        direction = self.get_direction(
            pressed_keys
        )

        # 計算本幀水平移動距離
        move_x = (
            direction.x
            * self.speed
            * dt
        )

        # 計算本幀垂直移動距離
        move_y = (
            direction.y
            * self.speed
            * dt
        )

        # 先處理水平方向移動與碰撞
        self.move_x(
            move_x,
            obstacles
        )

        # 再處理垂直方向移動與碰撞
        self.move_y(
            move_y,
            obstacles
        )

        # 最後限制玩家不能超出畫面
        self.keep_inside_bounds(
            screen_width,
            screen_height
        )

    def draw(
        self,
        screen,
        color=(50, 205, 50)
    ):
        """將玩家矩形繪製到畫面。"""

        pygame.draw.rect(
            screen,
            color,
            self.rect
        )
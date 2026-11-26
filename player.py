import pygame


class Player:
    """管理玩家位置、鍵盤滑鼠移動、碰撞與互動目標。"""

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
        self.position = pygame.Vector2(
            x,
            y
        )

        # 儲存玩家每秒移動的像素距離
        self.speed = speed

        # 記錄一般滑鼠點擊的移動目標
        self.mouse_target = None

        # 記錄目前想要靠近的互動物件
        self.interaction_target = None

    def get_keyboard_direction(
        self,
        pressed_keys
    ):
        """依照目前按住的按鍵取得移動方向。"""

        direction = pygame.Vector2(
            0,
            0
        )

        if (
            pygame.K_LEFT in pressed_keys
            or pygame.K_a in pressed_keys
        ):
            direction.x -= 1

        if (
            pygame.K_RIGHT in pressed_keys
            or pygame.K_d in pressed_keys
        ):
            direction.x += 1

        if (
            pygame.K_UP in pressed_keys
            or pygame.K_w in pressed_keys
        ):
            direction.y -= 1

        if (
            pygame.K_DOWN in pressed_keys
            or pygame.K_s in pressed_keys
        ):
            direction.y += 1

        # 正規化避免斜向移動速度比較快
        if direction.length_squared() > 0:
            direction = direction.normalize()

        return direction

    def set_mouse_target(
        self,
        target_position
    ):
        """設定一般地面點擊後的移動目標。"""

        self.mouse_target = pygame.Vector2(
            target_position
        )

        # 一般移動會取消原本互動目標
        self.interaction_target = None

    def get_interaction_stop_point(
        self,
        target
    ):
        """計算靠近物件時角色實際停下的位置。"""

        object_rect = target[
            "rect"
        ]

        interaction_rect = target[
            "interaction_rect"
        ]

        player_center = pygame.Vector2(
            self.rect.center
        )

        half_width = self.rect.width / 2
        half_height = self.rect.height / 2

        margin = 2

        min_y = (
            interaction_rect.top
            + half_height
        )

        max_y = (
            interaction_rect.bottom
            - half_height
        )

        min_x = (
            interaction_rect.left
            + half_width
        )

        max_x = (
            interaction_rect.right
            - half_width
        )

        if min_y > max_y:
            min_y = max_y = object_rect.centery

        if min_x > max_x:
            min_x = max_x = object_rect.centerx

        clamped_y = max(
            min_y,
            min(
                player_center.y,
                max_y
            )
        )

        clamped_x = max(
            min_x,
            min(
                player_center.x,
                max_x
            )
        )

        # 建立物件四個方向可能使用的停靠位置
        candidates = [
            pygame.Vector2(
                object_rect.left
                - half_width
                - margin,
                clamped_y
            ),
            pygame.Vector2(
                object_rect.right
                + half_width
                + margin,
                clamped_y
            ),
            pygame.Vector2(
                clamped_x,
                object_rect.top
                - half_height
                - margin
            ),
            pygame.Vector2(
                clamped_x,
                object_rect.bottom
                + half_height
                + margin
            )
        ]

        # 選擇距離目前玩家最近的停靠位置
        return min(
            candidates,
            key=lambda point: (
                point
                - player_center
            ).length_squared()
        )

    def set_interaction_target(
        self,
        target
    ):
        """設定需要自動靠近的互動物件。"""

        if self.can_interact(
            target
        ):
            self.cancel_mouse_movement()
            return

        self.interaction_target = target

        self.mouse_target = (
            self.get_interaction_stop_point(
                target
            )
        )

    def cancel_mouse_movement(self):
        """取消目前所有滑鼠自動移動。"""

        self.mouse_target = None
        self.interaction_target = None

    def can_interact(
        self,
        target
    ):
        """判斷玩家是否已進入物件互動範圍。"""

        return self.rect.colliderect(
            target[
                "interaction_rect"
            ]
        )

    def get_mouse_direction(self):
        """取得朝目前滑鼠目標前進的方向。"""

        if self.mouse_target is None:
            return pygame.Vector2(
                0,
                0
            )

        player_center = pygame.Vector2(
            self.rect.center
        )

        difference = (
            self.mouse_target
            - player_center
        )

        # 接近目標時視為已經抵達
        if difference.length() < 4:
            self.cancel_mouse_movement()

            return pygame.Vector2(
                0,
                0
            )

        return difference.normalize()

    # ========================================================
    # Polygon碰撞
    # ========================================================

    def get_feet_points(self):
        """取得角色腳底三個Polygon碰撞取樣點。"""

        inset = max(
            2,
            self.rect.width // 6
        )

        feet_y = self.rect.bottom - 2

        return [
            (
                self.rect.left + inset,
                feet_y
            ),
            (
                self.rect.centerx,
                feet_y
            ),
            (
                self.rect.right - inset,
                feet_y
            )
        ]

    def point_on_segment(
        self,
        point,
        start,
        end,
        tolerance=0.001
    ):
        """判斷點是否位於Polygon邊線上。"""

        px, py = point
        ax, ay = start
        bx, by = end

        # 利用叉積判斷三點是否近似共線
        cross = (
            (px - ax) * (by - ay)
            - (py - ay) * (bx - ax)
        )

        if abs(cross) > tolerance:
            return False

        # 共線後再確認點是否落在線段範圍內
        return (
            min(ax, bx) - tolerance
            <= px
            <= max(ax, bx) + tolerance
            and min(ay, by) - tolerance
            <= py
            <= max(ay, by) + tolerance
        )

    def point_in_polygon(
        self,
        point,
        polygon
    ):
        """使用射線法判斷一個點是否位於Polygon內。"""

        # 沒有有效Polygon時視為不限制移動
        if (
            polygon is None
            or len(polygon) < 3
        ):
            return True

        # 點剛好在線段上時也視為合法位置
        for index in range(
            len(polygon)
        ):
            start = polygon[
                index
            ]

            end = polygon[
                (index + 1)
                % len(polygon)
            ]

            if self.point_on_segment(
                point,
                start,
                end
            ):
                return True

        px, py = point

        inside = False

        previous_index = (
            len(polygon) - 1
        )

        # 射線法統計水平射線穿越邊界次數
        for index in range(
            len(polygon)
        ):
            x1, y1 = polygon[
                index
            ]

            x2, y2 = polygon[
                previous_index
            ]

            crosses_y = (
                (y1 > py)
                != (y2 > py)
            )

            if crosses_y:

                intersect_x = (
                    (x2 - x1)
                    * (py - y1)
                    / (y2 - y1)
                    + x1
                )

                if px < intersect_x:
                    inside = not inside

            previous_index = index

        return inside

    def is_inside_walkable_polygon(
        self,
        walkable_polygon
    ):
        """確認角色腳底仍完整位於可行走Polygon內。"""

        if (
            walkable_polygon is None
            or len(walkable_polygon) < 3
        ):
            return True

        # 左、中、右腳底都必須留在可行走區
        return all(
            self.point_in_polygon(
                point,
                walkable_polygon
            )
            for point in self.get_feet_points()
        )

    # ========================================================
    # Movement
    # ========================================================

    def move_x(
        self,
        move_x,
        obstacles,
        walkable_polygon=None
    ):
        """處理水平移動、家具Rect與Polygon邊界。"""

        old_x = (
            self.position.x
        )

        # 先嘗試水平移動到新位置
        self.position.x += move_x

        self.rect.x = round(
            self.position.x
        )

        # 檢查家具等Rect碰撞
        for obstacle in obstacles:

            if self.rect.colliderect(
                obstacle
            ):

                if move_x > 0:

                    self.rect.right = (
                        obstacle.left
                    )

                elif move_x < 0:

                    self.rect.left = (
                        obstacle.right
                    )

                self.position.x = (
                    self.rect.x
                )

        # 若腳底離開Polygon則撤銷水平移動
        if not self.is_inside_walkable_polygon(
            walkable_polygon
        ):

            self.position.x = (
                old_x
            )

            self.rect.x = round(
                old_x
            )

    def move_y(
        self,
        move_y,
        obstacles,
        walkable_polygon=None
    ):
        """處理垂直移動、家具Rect與Polygon邊界。"""

        old_y = (
            self.position.y
        )

        # 先嘗試垂直移動到新位置
        self.position.y += move_y

        self.rect.y = round(
            self.position.y
        )

        # 檢查家具等Rect碰撞
        for obstacle in obstacles:

            if self.rect.colliderect(
                obstacle
            ):

                if move_y > 0:

                    self.rect.bottom = (
                        obstacle.top
                    )

                elif move_y < 0:

                    self.rect.top = (
                        obstacle.bottom
                    )

                self.position.y = (
                    self.rect.y
                )

        # 若腳底離開Polygon則撤銷垂直移動
        if not self.is_inside_walkable_polygon(
            walkable_polygon
        ):

            self.position.y = (
                old_y
            )

            self.rect.y = round(
                old_y
            )

    def keep_inside_bounds(
        self,
        screen_width,
        screen_height
    ):
        """限制玩家不能離開目前畫面範圍。"""

        self.position.x = max(
            0,
            min(
                self.position.x,
                screen_width
                - self.rect.width
            )
        )

        self.position.y = max(
            0,
            min(
                self.position.y,
                screen_height
                - self.rect.height
            )
        )

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
        screen_height,
        walkable_polygon=None
    ):
        """更新玩家移動、家具碰撞與Polygon地圖邊界。"""

        keyboard_direction = (
            self.get_keyboard_direction(
                pressed_keys
            )
        )

        # 鍵盤操作優先於滑鼠自動移動
        if (
            keyboard_direction
            .length_squared()
            > 0
        ):

            self.cancel_mouse_movement()

            direction = (
                keyboard_direction
            )

        else:

            direction = (
                self.get_mouse_direction()
            )

        # 已進入互動範圍時停止自動靠近
        if (
            self.interaction_target
            is not None
            and self.can_interact(
                self.interaction_target
            )
        ):

            self.cancel_mouse_movement()

            direction = pygame.Vector2(
                0,
                0
            )

        move_x = (
            direction.x
            * self.speed
            * dt
        )

        move_y = (
            direction.y
            * self.speed
            * dt
        )

        # X、Y分開處理才能沿Polygon邊界滑動
        self.move_x(
            move_x,
            obstacles,
            walkable_polygon
        )

        self.move_y(
            move_y,
            obstacles,
            walkable_polygon
        )

        # 畫面邊界仍保留最後一道安全限制
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
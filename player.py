from math import ceil

import pygame


class Player:
    """管理玩家位置、鍵盤滑鼠移動、碰撞與互動目標。"""

    def __init__(
        self,
        x,
        y,
        width=40,
        height=40,
        speed=300,
        sprite_path=None,
        visual_scale=1.5
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
        self.path_points = []  # 儲存滑鼠導航剩餘路線的轉折點
        self.path_index = 0

        self.sprite_path = sprite_path  # 正式素材路徑獨立於角色位置狀態
        self.animations = {}
        self.direction = 0  # 方向欄依序代表下右上左
        self.frame_index = 0
        self.animation_timer = 0.0
        self.animation_interval = 0.15
        self.is_moving = False
        if sprite_path is not None:
            self.animations = self._load_sprite_sheet(sprite_path)

        self.visual_scale = visual_scale #角色大小放大倍率

    def _load_sprite_sheet(self, filename, cols=4, rows=4):
        """保留原始透明影格，缺圖時使用矩形備援。"""
        try:
            sheet = pygame.image.load(filename)
            if pygame.display.get_surface() is not None:
                sheet = sheet.convert_alpha()
            width, height = sheet.get_size()
            if width < cols or height < rows or width % cols or height % rows:
                return {}
            frame_width, frame_height = width // cols, height // rows
            animations = {col: [] for col in range(cols)}
            for col in range(cols):
                for row in range(rows):
                    rect = pygame.Rect(
                        col * frame_width, row * frame_height,
                        frame_width, frame_height
                    )
                    animations[col].append(sheet.subsurface(rect).copy())
            return animations  # 原始像素與透明度不進行去背處理
        except (OSError, pygame.error):
            return {}

    def update_direction(self, direction):
        """依主要移動軸更新面向，停止時保留方向。"""
        if direction.length_squared() == 0:
            return
        if abs(direction.x) > abs(direction.y):
            self.direction = 1 if direction.x > 0 else 3
        else:
            self.direction = 0 if direction.y > 0 else 2

    def update_animation(self, dt, movement_direction):
        """依經過秒數切換走路影格，停止回到待機。"""
        self.is_moving = movement_direction.length_squared() > 0
        if not self.is_moving:
            self.frame_index = 0
            self.animation_timer = 0.0
            return
        if self.frame_index not in (1, 3):
            self.frame_index = 1
        self.animation_timer += dt
        if self.animation_timer >= self.animation_interval:
            self.frame_index = 3 if self.frame_index == 1 else 1
            self.animation_timer = 0.0

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

        self.set_path([target_position])

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

        self.set_path([self.get_interaction_stop_point(target)], target)

    def set_path(self, points, interaction_target=None):
        """以新路線替換目前的滑鼠導航。"""
        self.cancel_mouse_movement()
        self.path_points = [pygame.Vector2(point) for point in points]
        if self.path_points:
            self.position.update(self.rect.topleft)  # 航線起點對齊目前可見角色位置
            self.mouse_target = self.path_points[0]
            self.interaction_target = interaction_target

    def cancel_mouse_movement(self):
        """取消目前所有滑鼠自動移動。"""

        self.mouse_target = None
        self.interaction_target = None
        self.path_points = []
        self.path_index = 0

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
        """略過已抵達的轉折點，回傳下一段方向。"""
        center = self.position + (self.rect.width // 2, self.rect.height // 2)
        while self.mouse_target is not None:
            difference = self.mouse_target - center
            if difference.length_squared() > 1e-8:
                return difference.normalize()
            self.path_index += 1
            if self.path_index == len(self.path_points):
                self.cancel_mouse_movement()
            else:
                self.mouse_target = self.path_points[self.path_index]
        return pygame.Vector2()

    # ========================================================
    # Polygon碰撞
    # ========================================================

    def get_collision_rect(self):
        """即時計算角色底部中央的家具碰撞矩形。"""
        return self.get_collision_rect_at(self.rect.center)

    def get_collision_rect_at(self, sprite_center):
        """計算假想角色中心的腳部碰撞矩形。"""
        width = max(1, round(self.rect.width * 0.50))  # 只取角色底部中央一半寬度
        height = max(1, round(self.rect.height * 0.15))  # 使用角色底部百分之十五高度
        sprite_bottom = round(sprite_center[1]) + self.rect.height - self.rect.height // 2
        return pygame.Rect(
            round(sprite_center[0]) - width // 2,
            sprite_bottom - height,
            width,
            height,
        )

    def get_feet_points(self):
        """取得角色腳底三個Polygon碰撞取樣點。"""
        return self.get_feet_points_at(self.rect.center)

    def get_feet_points_at(self, sprite_center):
        collision_rect = self.get_collision_rect_at(sprite_center)
        feet_y = collision_rect.bottom - 1  # 三個取樣點沿碰撞盒最下緣
        return [
            (collision_rect.left, feet_y),
            (collision_rect.centerx, feet_y),
            (collision_rect.right - 1, feet_y),
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

        return self.are_feet_inside_polygon(self.rect.center, walkable_polygon)

    def are_feet_inside_polygon(self, sprite_center, walkable_polygon):
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
            for point in self.get_feet_points_at(sprite_center)
        )

    def is_footprint_walkable(self, sprite_center, obstacles, polygon):
        collision_rect = self.get_collision_rect_at(sprite_center)
        return collision_rect.collidelist(obstacles) == -1 and self.are_feet_inside_polygon(
            sprite_center, polygon
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

            collision_rect = self.get_collision_rect()  # 用修正後的位置重新計算碰撞盒
            if collision_rect.colliderect(obstacle):
                if move_x > 0:
                    self.rect.x -= collision_rect.right - obstacle.left  # 依腳部重疊量向左推回角色
                elif move_x < 0:
                    self.rect.x += obstacle.right - collision_rect.left  # 依腳部重疊量向右推回角色
                self.position.x = self.rect.x

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

            collision_rect = self.get_collision_rect()  # 用修正後的位置重新計算碰撞盒
            if collision_rect.colliderect(obstacle):
                if move_y > 0:
                    self.rect.y -= collision_rect.bottom - obstacle.top  # 依腳部重疊量向上推回角色
                elif move_y < 0:
                    self.rect.y += obstacle.bottom - collision_rect.top  # 依腳部重疊量向下推回角色
                self.position.y = self.rect.y

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

    def follow_path(self, direction, distance_budget, obstacles, walkable_polygon):
        """沿當前路段前進，逐像素驗證以避免跨過薄障礙。"""
        offset = pygame.Vector2(self.rect.width // 2, self.rect.height // 2)
        start = self.position + offset
        distance = min(distance_budget, start.distance_to(self.mouse_target))
        steps = max(1, ceil(distance))
        for step in range(1, steps + 1):
            center = start + direction * (distance * step / steps)
            if not self.is_footprint_walkable(center, obstacles, walkable_polygon):
                self.cancel_mouse_movement()
                return
            self.position = center - offset
            self.rect.center = (round(center.x), round(center.y))
            if self.interaction_target is not None and self.can_interact(self.interaction_target):
                self.cancel_mouse_movement()
                return
        self.get_mouse_direction()  # 到達轉折點後準備下一段路線

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

        self.update_direction(direction)
        self.update_animation(dt, direction)  # 動畫共用鍵盤與滑鼠計算出的方向

        if self.mouse_target is not None:
            self.follow_path(direction, self.speed * dt, obstacles, walkable_polygon)
            if not pygame.Rect(0, 0, screen_width, screen_height).contains(self.rect):
                self.keep_inside_bounds(screen_width, screen_height)
                self.cancel_mouse_movement()
            return

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
        screen
    ):
        """等比例繪製像素角色，腳底貼齊既有碰撞矩形。"""
        if not self.animations:
            pygame.draw.rect(screen, (50, 205, 50), self.rect)
            return
        frame = self.animations[self.direction][self.frame_index]
        base_scale = min(
            self.rect.width / frame.get_width(),
            self.rect.height / frame.get_height()
        )

        scale = base_scale * self.visual_scale

        size = (max(1, round(frame.get_width() * scale)),
                max(1, round(frame.get_height() * scale)))
        image = pygame.transform.scale(frame, size)  # 最近鄰縮放保留角色像素邊緣
        image_rect = image.get_rect(midbottom=self.rect.midbottom)
        screen.blit(image, image_rect)

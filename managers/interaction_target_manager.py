import pygame


class InteractionTargetManager:
    """依互動區域與角色面向選擇場景目標。"""

    def __init__(self, ui_layout, game_ui, game):
        self.ui_layout = ui_layout
        self.game_ui = game_ui
        self.game = game

    def is_in_interaction_region(self, player, space_id, object_id, interaction_rect, screen):
        """先檢查矩形，再精確判斷非矩形互動區域。"""
        if not player.rect.colliderect(interaction_rect):
            return False

        layout = self.ui_layout.get("spaces", {}).get(space_id, {}).get("objects", {}).get(object_id, {})
        points = layout.get("interaction_polygon", [])
        if len(points) < 3:
            return True

        polygon = [
            (self.game_ui.scale_x(screen, x), self.game_ui.scale_y(screen, y))
            for x, y in points
        ]
        corners = (player.rect.topleft, player.rect.topright,
                   player.rect.bottomleft, player.rect.bottomright)
        if any(player.point_in_polygon(point, polygon) for point in corners):
            return True
        return any(
            player.rect.collidepoint(point)
            or player.rect.clipline(point, polygon[(index + 1) % len(polygon)])
            for index, point in enumerate(polygon)
        )

    def get_interaction_target(self, player, space_id, object_rects, interaction_rects, screen):
        """優先選最近的前方物件，否則選範圍內最近者。"""
        nearest_target = None
        nearest_priority = None
        player_center = pygame.Vector2(player.rect.center)
        facing = pygame.Vector2(((0, 1), (1, 0), (0, -1), (-1, 0))[player.direction])
        objects = self.ui_layout.get("spaces", {}).get(space_id, {}).get("objects", {})

        for object_id, interaction_rect in interaction_rects.items():
            required_event = objects.get(object_id, {}).get("visible_after_event")
            if required_event and not self.game.has_event(required_event):
                continue  # 即使傳入未過濾資料仍排除隱藏物件
            if not self.is_in_interaction_region(player, space_id, object_id, interaction_rect, screen):
                continue
            object_rect = object_rects.get(object_id)
            if object_rect is None:
                continue

            offset = pygame.Vector2(object_rect.center) - player_center
            distance = offset.length_squared()
            forward = facing.dot(offset)
            in_front = forward >= 0 and 2 * forward * forward >= distance
            priority = (not in_front, distance)  # 先比較是否在前方，再比較距離
            if nearest_priority is None or priority < nearest_priority:
                nearest_priority = priority
                nearest_target = {"id": object_id, "rect": object_rect, "interaction_rect": interaction_rect}

        return nearest_target

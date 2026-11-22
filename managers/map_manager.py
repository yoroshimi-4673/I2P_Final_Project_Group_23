"""管理探索地圖的版面、碰撞、互動範圍與出生點。"""


class MapManager:
    """將ui_layout中的Space資料轉成遊戲執行時資料。"""

    def __init__(self, ui_layout, game_ui, game):
        self.ui_layout = ui_layout
        self.game_ui = game_ui
        self.game = game  # 依劇情事件啟用場景物件與碰撞

        # 保存Player原始版面供出生點系統使用
        self.player_layouts = {
            space_id: (
                dict(space_data["player"])
                if space_data.get("player") is not None
                else None
            )
            for space_id, space_data
            in ui_layout.get("spaces", {}).items()
        }

        # 正式Player會自行繪製，關閉舊Placeholder
        for space_data in ui_layout.get("spaces", {}).values():
            space_data["player"] = None

    def get_space_layout(self, space_id):
        """取得指定Space的原始版面資料。"""

        return self.ui_layout.get(
            "spaces",
            {}
        ).get(
            space_id,
            {}
        )

    def get_object_rects(self, space_id, screen):
        """建立指定Space所有互動物件的畫面Rect。"""

        space_layout = self.get_space_layout(
            space_id
        )

        object_rects = {}

        for object_id, object_layout in (
            space_layout.get(
                "objects",
                {}
            ).items()
        ):
            required_event = object_layout.get("visible_after_event")
            if required_event and not self.game.has_event(required_event):
                continue  # 未解鎖物件不建立地圖互動範圍
            object_rects[object_id] = (
                self.game_ui.scale_rect(
                    screen,
                    object_layout
                )
            )

        return object_rects

    def get_collision_rects(self, space_id, screen):
        """建立家具等局部障礙物的畫面Rect。"""

        space_layout = self.get_space_layout(
            space_id
        )

        collision_rects = {}

        for zone_id, zone_layout in (
            space_layout.get(
                "collision_zones",
                {}
            ).items()
        ):
            required_event = zone_layout.get("visible_after_event")
            if required_event and not self.game.has_event(required_event):
                continue  # 物件尚未出現時不建立隱形碰撞
            collision_rects[zone_id] = (
                self.game_ui.scale_rect(
                    screen,
                    zone_layout
                )
            )

            # 家具碰撞跟隨圖片等比例縮放範圍
            object_id = zone_layout.get("fit_object_asset")
            if object_id:
                object_layout = space_layout.get("objects", {}).get(object_id, {})
                image = self.game_ui.load_image(object_layout.get("asset"))
                if image is not None:
                    target = self.game_ui.scale_rect(screen, object_layout)
                    fitted = self.game_ui.scale_image_to_fit(image, target)
                    collision_rects[zone_id] = fitted.get_rect(center=target.center)

        return collision_rects

    def get_walkable_polygon(
        self,
        space_id,
        screen
    ):
        """將Base座標的可行走Polygon縮放到目前視窗。"""

        space_layout = self.get_space_layout(
            space_id
        )

        polygon_layout = space_layout.get(
            "walkable_polygon",
            []
        )

        return [
            (
                self.game_ui.scale_x(
                    screen,
                    point[0]
                ),
                self.game_ui.scale_y(
                    screen,
                    point[1]
                )
            )
            for point in polygon_layout
        ]

    def get_interaction_rects(
        self,
        space_id,
        screen,
        object_rects=None
    ):
        """依物件位置與padding建立E鍵互動範圍。"""

        if object_rects is None:
            object_rects = self.get_object_rects(
                space_id,
                screen
            )

        space_layout = self.get_space_layout(
            space_id
        )

        object_layouts = space_layout.get(
            "objects",
            {}
        )

        interaction_rects = {}

        for object_id, rect in object_rects.items():
            object_layout = object_layouts.get(
                object_id,
                {}
            )

            interaction_padding = object_layout.get(
                "interaction_padding",
                40
            )

            padding_x = self.game_ui.scale_x(
                screen,
                interaction_padding
            )

            padding_y = self.game_ui.scale_y(
                screen,
                interaction_padding
            )

            interaction_rects[object_id] = (
                rect.inflate(
                    padding_x * 2,
                    padding_y * 2
                )
            )

        return interaction_rects

    def build_space_runtime_data(self, space_id, screen):
        """一次建立探索模式需要的所有Space物理資料。"""

        object_rects = self.get_object_rects(
            space_id,
            screen
        )

        collision_rects = self.get_collision_rects(
            space_id,
            screen
        )

        walkable_polygon = self.get_walkable_polygon(
            space_id,
            screen
        )

        interaction_rects = self.get_interaction_rects(
            space_id,
            screen,
            object_rects
        )

        return {
            "object_rects": object_rects,
            "collision_rects": collision_rects,
            "walkable_polygon": walkable_polygon,
            "interaction_rects": interaction_rects
        }

    def get_spawn_layout(
        self,
        space_id,
        entry_rift_id=None
    ):
        """依Space與入口裂隙取得Player出生版面。"""

        default_layout = self.player_layouts.get(
            space_id
        )

        if default_layout is None:
            return None

        player_layout = dict(
            default_layout
        )

        if entry_rift_id is None:
            return player_layout

        space_layout = self.get_space_layout(
            space_id
        )

        entry_layout = space_layout.get(
            "entry_spawns",
            {}
        ).get(
            entry_rift_id
        )

        if entry_layout is not None:
            player_layout.update(
                entry_layout
            )

        return player_layout

    def get_object_entry_spawn(
        self,
        space_id,
        object_id
    ):
        """依指定物件Base Rect計算右側出生位置。"""

        if object_id is None:
            return None

        space_layout = (
            self.get_space_layout(
                space_id
            )
        )

        # 人工指定入口優先於門右側的預設計算
        entry_spawn = space_layout.get("entry_spawns", {}).get(object_id)
        if entry_spawn is not None:
            return dict(entry_spawn)

        object_layout = (
            space_layout
            .get(
                "objects",
                {}
            )
            .get(
                object_id
            )
        )

        if object_layout is None:
            return None

        x = (
            object_layout["x"]
            + object_layout["width"]
            + 20
        )

        y = (
            object_layout["y"]
            + object_layout["height"] / 2
        )

        return {
            "x": x,
            "y": y
        }

    def place_player(
        self,
        player,
        space_id,
        screen,
        entry_rift_id=None,
        entry_object_id=None
    ):
        """將Player放到指定Space的正確出生位置。"""

        player_layout = self.get_spawn_layout(
            space_id,
            entry_rift_id
        )

        if player_layout is None:
            return False

        if entry_object_id is not None:

            object_spawn = (
                self.get_object_entry_spawn(
                    space_id,
                    entry_object_id
                )
            )

            if object_spawn is not None:

                player_layout = dict(
                    player_layout
                )

                player_layout.update(
                    object_spawn
                )

        spawn_rect = self.game_ui.scale_rect(
            screen,
            player_layout
        )
        center = player_layout.get("center")  # 獨立縮放明確指定的出生中心
        if center is not None:
            spawn_rect.center = (
                self.game_ui.scale_x(screen, center[0]),
                self.game_ui.scale_y(screen, center[1]),
            )

        # 角色尺寸跟隨目前Space的Player版面，並縮小至75%
        player_width = int(
            spawn_rect.width * 0.75
        )

        player_height = int(
            spawn_rect.height * 0.75
        )

        player.rect.size = (
            player_width,
            player_height
        )

        # 縮小後仍維持原本出生點中心位置
        player.rect.center = (
            spawn_rect.center
        )

        player.position.update(
            player.rect.x,
            player.rect.y
        )

        # 切換Space後取消舊的滑鼠移動目標
        player.cancel_mouse_movement()
        if "direction" in player_layout:
            player.direction = player_layout["direction"]  # 僅指定入口覆寫角色原本朝向
            player.frame_index = 0  # 進門後先顯示該方向的站姿

        return True

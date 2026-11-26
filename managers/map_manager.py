"""管理探索地圖的版面、碰撞、互動範圍與出生點。"""


class MapManager:
    """將ui_layout中的Space資料轉成遊戲執行時資料。"""

    def __init__(self, ui_layout, game_ui):
        self.ui_layout = ui_layout
        self.game_ui = game_ui

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
            object_rects[object_id] = (
                self.game_ui.scale_rect(
                    screen,
                    object_layout
                )
            )

        return object_rects

    def get_collision_rects(self, space_id, screen):
        """建立指定Space所有不可通行區域Rect。"""

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
            collision_rects[zone_id] = (
                self.game_ui.scale_rect(
                    screen,
                    zone_layout
                )
            )

        return collision_rects

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
        """一次建立探索模式需要的所有Space Rect資料。"""

        object_rects = self.get_object_rects(
            space_id,
            screen
        )

        collision_rects = self.get_collision_rects(
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

        # 複製資料避免入口座標改到預設出生點
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

    def place_player(
        self,
        player,
        space_id,
        screen,
        entry_rift_id=None
    ):
        """將Player放到指定Space的正確出生位置。"""

        player_layout = self.get_spawn_layout(
            space_id,
            entry_rift_id
        )

        if player_layout is None:
            return False

        spawn_rect = self.game_ui.scale_rect(
            screen,
            player_layout
        )


        # 角色尺寸跟隨目前Space的Player版面，並將Player尺寸縮小至原版面的75%(原本太大)
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

        # 縮小後仍保持出生點中心不變
        player.rect.center = (
            spawn_rect.center
        )

        player.position.update(
            player.rect.x,
            player.rect.y
        )

        # 切換Space時取消舊滑鼠導航目標
        player.cancel_mouse_movement()

        return True

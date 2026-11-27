class NavigationController:
    """協調一次滑鼠點擊的路徑規劃。"""

    def __init__(self, pathfinding_manager, player, game):
        self.pathfinding_manager = pathfinding_manager
        self.player = player
        self.game = game

    def navigate_to_click(
        self, position, screen, obstacles, walkable_polygon, interaction_target=None
    ):
        interaction_rect = None
        if interaction_target is not None:
            if self.player.can_interact(interaction_target):
                self.player.cancel_mouse_movement()  # 已在互動範圍內便停止導航
                return
            position = self.player.get_interaction_stop_point(interaction_target)
            interaction_rect = interaction_target["interaction_rect"]

        path = self.pathfinding_manager.find_path(
            self.game.current_space,
            screen,
            self.player,
            position,
            obstacles,
            walkable_polygon,
            interaction_rect,
        )
        self.player.set_path(path, interaction_target)  # 空路徑也須清除既有導航狀態

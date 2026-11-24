import pygame


class NavigationController:
    """協調滑鼠路徑與抵達後的場景互動。"""

    def __init__(self, pathfinding_manager, player, game, target_manager, interaction_controller):
        self.pathfinding_manager = pathfinding_manager
        self.player = player
        self.game = game
        self.target_manager = target_manager
        self.interaction_controller = interaction_controller
        self.pending_interaction = None

    def cancel(self):
        self.pending_interaction = None
        self.player.cancel_mouse_movement()

    def navigate_to_click(
        self, position, screen, obstacles, walkable_polygon, object_rects, interaction_rects
    ):
        self.cancel()
        space_id = self.game.current_space
        target = None
        for object_id, object_rect in object_rects.items():
            if object_rect.collidepoint(position):
                target = self.target_manager.get_available_target(
                    space_id, object_id, object_rects, interaction_rects
                )
                if target is not None:
                    break

        interaction_rect = None
        path_options = {}
        if target is not None:
            if self._in_range(space_id, target, screen):
                self._open_target(target)
                return
            position = self.player.get_interaction_stop_point(target)
            interaction_rect = target["interaction_rect"]
            path_options["can_stop"] = lambda rect: self._in_range(space_id, target, screen, rect)

        path = self.pathfinding_manager.find_path(
            space_id,
            screen,
            self.player,
            position,
            obstacles,
            walkable_polygon,
            interaction_rect,
            **path_options,
        )
        if path:
            self.player.set_path(path)
            if target is not None:
                self.pending_interaction = (space_id, target["id"])

    def update_player(
        self, dt, pressed_keys, obstacles, walkable_polygon, screen, object_rects, interaction_rects
    ):
        target = None
        if self.pending_interaction is not None:
            space_id, object_id = self.pending_interaction
            if not pressed_keys and space_id == self.game.current_space:
                target = self.target_manager.get_available_target(
                    space_id, object_id, object_rects, interaction_rects
                )
            if target is None:
                self.cancel()

        path_clear = self.player.update(dt, pressed_keys, obstacles, *screen.get_size(), walkable_polygon)
        if target is None:
            return
        if path_clear is False:
            self.cancel()
        elif self._in_range(space_id, target, screen):
            self._open_target(target)
        elif self.player.mouse_target is None:
            self.cancel()

    def _in_range(self, space_id, target, screen, player_rect=None):
        return self.target_manager.is_in_interaction_region(
            self.player, space_id, target["id"], target["interaction_rect"], screen,
            player_rect=player_rect,
        )

    def _open_target(self, target):
        self.cancel()
        offset = pygame.Vector2(target["rect"].center) - self.player.rect.center
        self.player.update_direction(offset)
        self.player.update_animation(0, pygame.Vector2())
        self.interaction_controller.reset_interaction_focus()
        self.interaction_controller.open_object(target["id"])

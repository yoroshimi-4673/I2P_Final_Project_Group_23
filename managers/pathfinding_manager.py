"""以角色腳部碰撞盒規劃滑鼠導航路線。"""

from heapq import heappop, heappush
from math import ceil, hypot

import pygame


class PathfindingManager:
    GRID_STEP = 5
    GRID_CACHE_LIMIT = 16
    DIRECTIONS = (
        (1, 0), (-1, 0), (0, 1), (0, -1),
        (1, 1), (1, -1), (-1, 1), (-1, -1),
    )

    def __init__(self, game_ui):
        self.game_ui = game_ui
        self.grid_cache = {}

    def is_position_walkable(self, player, position, obstacles, walkable_polygon):
        return player.is_footprint_walkable(position, obstacles, walkable_polygon)

    def find_nearest_walkable_node(self, position, step, grid_size, is_walkable):
        """在有限的畫面網格中選距原位置最近的合法格。"""
        sx, sy = step
        width, height = grid_size
        x, y = position
        nearest = (max(0, min(width - 1, round(x / sx))),
                   max(0, min(height - 1, round(y / sy))))
        if is_walkable(nearest):
            return nearest

        nodes = ((gx, gy) for gx in range(width) for gy in range(height))
        for node in sorted(nodes, key=lambda p: (p[0] * sx - x) ** 2 + (p[1] * sy - y) ** 2):
            if is_walkable(node):
                return node
        return None

    @staticmethod
    def segment_is_walkable(start, end, position_is_walkable):
        """逐像素檢查整段腳部空間，也避免斜向貼角穿越。"""
        dx, dy = end[0] - start[0], end[1] - start[1]
        steps = max(1, ceil(hypot(dx, dy)))  # 密集取樣可攔截窄於網格的家具
        previous = (round(start[0]), round(start[1]))
        if not position_is_walkable(previous):
            return False
        for index in range(1, steps + 1):
            point = (round(start[0] + dx * index / steps), round(start[1] + dy * index / steps))
            if point == previous:
                continue
            if not position_is_walkable(point):
                return False
            if point[0] != previous[0] and point[1] != previous[1]:
                if not (position_is_walkable((point[0], previous[1]))
                        and position_is_walkable((previous[0], point[1]))):
                    return False
            previous = point
        return True

    def find_path(self, space_id, screen, player, target, obstacles, walkable_polygon,
                  interaction_rect=None, *, can_stop=None):
        """回傳從目前角色中心可實際走到的航點。"""
        obstacles = tuple(obstacles)
        polygon = tuple(tuple(point) for point in (walkable_polygon or ()))
        screen_width, screen_height = screen.get_size()
        step = (
            max(1, round(self.game_ui.scale_x(screen, self.GRID_STEP))),
            max(1, round(self.game_ui.scale_y(screen, self.GRID_STEP))),
        )
        sx, sy = step
        grid_size = (screen_width // sx + 1, screen_height // sy + 1)
        cache_key = (
            space_id, screen.get_size(), player.rect.size, step,
            tuple(sorted(tuple(rect) for rect in obstacles)), polygon,
        )
        if cache_key not in self.grid_cache:
            if len(self.grid_cache) >= self.GRID_CACHE_LIMIT:
                del self.grid_cache[next(iter(self.grid_cache))]
            self.grid_cache[cache_key] = {}
        nodes = self.grid_cache[cache_key]
        half_width = player.rect.width // 2
        half_height = player.rect.height // 2
        pixel_cache = {}
        polygon_edges = list(zip(polygon, polygon[1:] + polygon[:1])) if len(polygon) >= 3 else []

        def position_is_walkable(point):
            if point not in pixel_cache:
                left, top = point[0] - half_width, point[1] - half_height
                pixel_cache[point] = (
                    0 <= left <= screen_width - player.rect.width
                    and 0 <= top <= screen_height - player.rect.height
                    and self.is_position_walkable(player, point, obstacles, polygon)
                )
            return pixel_cache[point]

        def to_screen(node):
            return node[0] * sx, node[1] * sy

        def node_is_walkable(node):
            if not (0 <= node[0] < grid_size[0] and 0 <= node[1] < grid_size[1]):
                return False
            if node not in nodes:
                nodes[node] = position_is_walkable(to_screen(node))
            return nodes[node]

        def can_stop_at(point):
            if interaction_rect is None:
                return True
            sprite = player.rect.copy()
            sprite.center = point
            return sprite.colliderect(interaction_rect) and (can_stop is None or can_stop(sprite))

        def segment_clear(start, end):
            if not position_is_walkable(start) or not position_is_walkable(end):
                return False
            first = player.get_collision_rect_at(start)
            last = player.get_collision_rect_at(end)
            body_sweep = first.union(last)
            feet_sweep = pygame.Rect(
                body_sweep.left, min(first.bottom, last.bottom) - 1,
                body_sweep.width, abs(first.bottom - last.bottom) + 1,
            ).inflate(2, 2)  # 讓貼近邊界的路段保留逐像素檢查
            if body_sweep.collidelist(obstacles) == -1 and not any(
                feet_sweep.clipline(edge) for edge in polygon_edges
            ):
                return True  # 掃掠區未接觸家具或多邊形邊界
            return self.segment_is_walkable(start, end, position_is_walkable)

        start = player.rect.center
        target = (round(target[0]), round(target[1]))
        if not position_is_walkable(start) or (start == target and can_stop_at(start)):
            return []
        start_node = self.find_nearest_walkable_node(
            start, step, grid_size,
            lambda n: node_is_walkable(n) and segment_clear(start, to_screen(n)),
        )
        goal_node = self.find_nearest_walkable_node(
            target, step, grid_size, lambda n: can_stop_at(to_screen(n)) and node_is_walkable(n),
        )
        if start_node is None or goal_node is None:
            return []

        route = self._search(start_node, goal_node, to_screen, node_is_walkable, segment_clear, step)
        if not route:
            return []
        points = [start, *(to_screen(node) for node in route)]
        if can_stop_at(target) and segment_clear(points[-1], target):
            points.append(target)  # 點擊位置可安全抵達時保留精確終點
        return self._simplify(points, segment_clear)

    def _search(self, start, goal, to_screen, node_is_walkable, segment_clear, step):
        sx, sy = step

        def estimate(node):
            return hypot((goal[0] - node[0]) * sx, (goal[1] - node[1]) * sy)

        moves = [(dx, dy, hypot(dx * sx, dy * sy)) for dx, dy in self.DIRECTIONS]
        frontier = [(estimate(start), 0, start)]
        costs = {start: 0}
        parents = {}
        while frontier:
            _, cost, node = heappop(frontier)
            if cost != costs[node]:
                continue
            if node == goal:
                route = [node]
                while node in parents:
                    node = parents[node]
                    route.append(node)
                return route[::-1]
            x, y = node
            for dx, dy, weight in moves:
                neighbor = (x + dx, y + dy)
                next_cost = cost + weight
                if next_cost >= costs.get(neighbor, float("inf")) or not node_is_walkable(neighbor):
                    continue
                if dx and dy and not (node_is_walkable((x + dx, y)) and node_is_walkable((x, y + dy))):
                    continue  # 斜向移動需兩側相鄰格皆可走
                if not segment_clear(to_screen(node), to_screen(neighbor)):
                    continue
                costs[neighbor] = next_cost
                parents[neighbor] = node
                heappush(frontier, (next_cost + estimate(neighbor), next_cost, neighbor))
        return []

    @staticmethod
    def _simplify(points, segment_clear):
        corners = [points[0]]
        for point in points[1:]:
            if point == corners[-1]:
                continue
            if len(corners) >= 2:
                first = pygame.Vector2(corners[-1]) - corners[-2]
                second = pygame.Vector2(point) - corners[-1]
                if first.cross(second) == 0 and first.dot(second) > 0:
                    corners[-1] = point
                    continue
            corners.append(point)

        waypoints = []
        anchor = 0
        while anchor < len(corners) - 1:
            end = len(corners) - 1
            while end > anchor + 1 and not segment_clear(corners[anchor], corners[end]):
                end -= 1
            waypoints.append(pygame.Vector2(corners[end]))
            anchor = end
        return waypoints

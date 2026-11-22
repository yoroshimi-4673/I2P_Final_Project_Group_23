import json

import pygame


class PolygonEditorController:
    CURSOR_SPEED = 180
    CURSOR_HOLD_MS = 1000
    CURSOR_DIRECTIONS = {
        pygame.K_LEFT: (-1, 0),
        pygame.K_RIGHT: (1, 0),
        pygame.K_UP: (0, -1),
        pygame.K_DOWN: (0, 1),
    }

    def __init__(self, ui_layout):
        self.ui_layout = ui_layout
        self.resolution = ui_layout["base_resolution"]
        self.active = False
        self.points = []
        self.space_id = None
        self.cursor = [self.resolution["width"] / 2, self.resolution["height"] / 2]
        self.key_started = {}

    def start(self, space_id):
        self.active = True
        self.space_id = space_id
        self.points = []
        self.cursor = [self.resolution["width"] / 2, self.resolution["height"] / 2]
        self.clear_held_keys()
        print(f"[Polygon Editor] 開始編輯 Space {space_id}")

    def close(self):
        self.active = False
        self.points = []
        self.space_id = None
        self.clear_held_keys()

    def cancel(self):
        self.close()
        print("[Polygon Editor] 已取消")

    def toggle(self, space_id):
        if self.active:
            self.close()
            print("[Polygon Editor] 已離開")
        else:
            self.start(space_id)
        return self.active

    def screen_to_base(self, position, screen):
        return (
            round(position[0] * self.resolution["width"] / screen.get_width()),
            round(position[1] * self.resolution["height"] / screen.get_height()),
        )

    def base_to_screen(self, point, screen):
        return (
            round(point[0] * screen.get_width() / self.resolution["width"]),
            round(point[1] * screen.get_height() / self.resolution["height"]),
        )

    def handle_mouse_motion(self, position, screen):
        if self.active:
            self.cursor = list(self.screen_to_base(position, screen))

    def add_point_from_screen(self, position, screen):
        self.handle_mouse_motion(position, screen)
        if self.active:
            self.add_point()

    def add_point(self):
        point = (round(self.cursor[0]), round(self.cursor[1]))
        self.points.append(point)
        print(f"[Polygon Editor] 新增頂點 {len(self.points) - 1}: {point}")

    def undo_point(self):
        if self.points:
            print(f"[Polygon Editor] 撤銷頂點：{self.points.pop()}")

    def clear_points(self):
        self.points = []
        print("[Polygon Editor] 已清空全部頂點")

    def apply(self):
        if len(self.points) < 3:
            print("[Polygon Editor] 至少需要3個頂點。")
            return False

        polygon_data = [list(point) for point in self.points]
        self.ui_layout["spaces"][self.space_id]["walkable_polygon"] = polygon_data  # 只套用到目前執行中的地圖資料
        print(f"\n[Polygon Editor] 請將以下內容貼入 Space {self.space_id}:")
        print('"walkable_polygon": ' + json.dumps(polygon_data, ensure_ascii=False, indent=4))
        print("[Polygon Editor] 已暫時套用至目前遊戲。\n")
        self.close()
        return True

    def handle_keydown(self, key, now_ms):
        if not self.active:
            return
        if key in self.CURSOR_DIRECTIONS:
            if key not in self.key_started:
                self.key_started[key] = now_ms
                dx, dy = self.CURSOR_DIRECTIONS[key]
                self._move_cursor(dx, dy)  # 方向鍵初次按下立即移動一格
        elif key == pygame.K_ESCAPE:
            self.cancel()
        elif key == pygame.K_SPACE:
            self.add_point()
        elif key in (pygame.K_BACKSPACE, pygame.K_DELETE):
            self.undo_point()
        elif key == pygame.K_r:
            self.clear_points()
        elif key == pygame.K_RETURN:
            self.apply()

    def handle_keyup(self, key):
        self.key_started.pop(key, None)

    def clear_held_keys(self):
        self.key_started.clear()

    def _move_cursor(self, dx, dy):
        self.cursor[0] = max(0, min(self.cursor[0] + dx, self.resolution["width"]))
        self.cursor[1] = max(0, min(self.cursor[1] + dy, self.resolution["height"]))

    def update(self, dt, now_ms, keyboard_focused):
        if not self.active or not keyboard_focused:
            self.clear_held_keys()
            return

        movement = pygame.Vector2()
        for key, started in self.key_started.items():
            # 只計算超過長按門檻的幀內時間
            move_dt = min(dt, max(0, now_ms - started - self.CURSOR_HOLD_MS) / 1000)
            movement += pygame.Vector2(self.CURSOR_DIRECTIONS[key]) * move_dt

        if movement.length() > dt:
            movement.scale_to_length(dt)
        self._move_cursor(movement.x * self.CURSOR_SPEED, movement.y * self.CURSOR_SPEED)

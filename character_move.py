import pygame
import sys

pygame.init()
WIDTH, HEIGHT = 800, 600
BG_COLOR = (50, 52, 60) 

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Pygame 2.5D 角色控制")
clock = pygame.time.Clock()


class Player:
    def __init__(self, image_path, x, y, scale=3, speed=4):
        self.animations, self.width, self.height = self._load_sprite_sheet(image_path, scale=scale)
        self.x = x - self.width // 2
        self.y = y - self.height // 2
        self.speed = speed
        self.direction = 0 
        self.frame_index = 0
        self.anim_timer = 0

    def _load_sprite_sheet(self, filename, cols=4, rows=3, scale=3):
        sheet = pygame.image.load(filename).convert_alpha()
        sheet_w, sheet_h = sheet.get_size()
        frame_w = sheet_w // cols
        frame_h = sheet_h // rows
        animations = {0: [], 1: [], 2: [], 3: []}

        for col in range(cols):
            for row in range(rows):
                rect = pygame.Rect(col * frame_w, row * frame_h, frame_w, frame_h)
                frame = pygame.Surface((frame_w, frame_h), pygame.SRCALPHA)
                frame.blit(sheet, (0, 0), rect)

                # 自動去背：把淺色背景變透明
                for px in range(frame_w):
                    for py in range(frame_h):
                        r, g, b, a = frame.get_at((px, py))
                        if r > 200 and g > 200 and b > 200:
                            frame.set_at((px, py), (0, 0, 0, 0))

                scaled_frame = pygame.transform.scale(frame, (frame_w * scale, frame_h * scale))
                animations[col].append(scaled_frame)

        return animations, frame_w * scale, frame_h * scale

    def update(self, keys):
        moving = False

        if keys[pygame.K_w]:
            self.y -= self.speed * 0.7
            self.direction = 2
            moving = True
        if keys[pygame.K_s]:
            self.y += self.speed * 0.7
            self.direction = 0
            moving = True
        if keys[pygame.K_a]:
            self.x -= self.speed
            self.direction = 3
            moving = True
        if keys[pygame.K_d]:
            self.x += self.speed
            self.direction = 1
            moving = True

        # 走路動畫幀切換
        if moving:
            self.anim_timer += 1
            if self.anim_timer >= 8:
                self.anim_timer = 0
                self.frame_index = 1 if self.frame_index != 1 else 2
        else:
            self.frame_index = 0

    def draw(self, surface):
        current_img = self.animations[self.direction][self.frame_index]
        surface.blit(current_img, (self.x, self.y))


if __name__ == "__main__":
    player = Player("main_player.png", WIDTH // 2, HEIGHT // 2, scale=3, speed=4)

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        keys = pygame.key.get_pressed()
        player.update(keys)

        screen.fill(BG_COLOR)
        player.draw(screen)

        pygame.display.flip()
        clock.tick(60)

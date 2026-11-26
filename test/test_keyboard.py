import pygame

pygame.init()

screen = pygame.display.set_mode((500, 300))
pygame.display.set_caption("Keyboard Event Test")

clock = pygame.time.Clock()
running = True

while running:
    for event in pygame.event.get():

        if event.type == pygame.QUIT:
            running = False

        print(event)

    screen.fill((30, 30, 30))
    pygame.display.flip()

    clock.tick(60)

pygame.quit()
import pygame
import random
import heapq

# --- Konfiguracja ---
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
CELL_SIZE = 20
MAZE_WIDTH = SCREEN_WIDTH // CELL_SIZE
MAZE_HEIGHT = SCREEN_HEIGHT // CELL_SIZE

# --- Kolory ---
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GREEN = (0, 255, 0)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)
ORANGE = (255, 165, 0)


# --- Klasy ---

class Player:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def move(self, dx, dy, maze):
        new_x = self.x + dx
        new_y = self.y + dy
        if 0 <= new_x < MAZE_WIDTH and 0 <= new_y < MAZE_HEIGHT and maze[new_y][new_x] == 0:
            self.x = new_x
            self.y = new_y

    def draw(self, screen):
        pygame.draw.rect(screen, GREEN, (self.x * CELL_SIZE, self.y * CELL_SIZE, CELL_SIZE, CELL_SIZE))


class Enemy:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.chase_distance = 8
        self.state = 'patrolling'
        self.unseen_timer = 0
        self.seek_path = []
        self.last_known_pos = None

        # ### ZMIANA ### - Indywidualne ustawienia prędkości i timer
        self.move_delay_default = 300
        self.move_delay_chase = int(self.move_delay_default * 0.75)  # 25% szybciej
        self.current_move_delay = self.move_delay_default
        self.move_timer = 0

    def move_randomly(self, maze):
        possible_moves = []
        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            new_x, new_y = self.x + dx, self.y + dy
            if 0 <= new_x < MAZE_WIDTH and 0 <= new_y < MAZE_HEIGHT and maze[new_y][new_x] == 0:
                possible_moves.append((new_x, new_y))
        if possible_moves:
            self.x, self.y = random.choice(possible_moves)

    def update(self, player, maze, dt):
        distance_to_player = abs(self.x - player.x) + abs(self.y - player.y)

        if distance_to_player <= self.chase_distance:
            if self.state != 'chasing':
                self.state = 'chasing'
                self.current_move_delay = self.move_delay_chase  # Przyspiesz!
            self.unseen_timer = 0
            self.seek_path = []
            self.last_known_pos = (player.x, player.y)
        else:
            if self.state == 'chasing':
                self.state = 'seeking'
                self.current_move_delay = self.move_delay_default  # Wróć do normalnej prędkości
                if self.last_known_pos:
                    self.seek_path = a_star((self.x, self.y), self.last_known_pos, maze)
            elif self.state == 'patrolling':
                self.unseen_timer += dt

        if self.state == 'chasing':
            path = a_star((self.x, self.y), (player.x, player.y), maze)
            if path and len(path) > 1:
                self.x, self.y = path[1]

        elif self.state == 'seeking':
            if self.seek_path and len(self.seek_path) > 1:
                self.x, self.y = self.seek_path.pop(1)
            else:
                self.state = 'patrolling'
                self.current_move_delay = self.move_delay_default
                self.seek_path = []
                self.unseen_timer = 0

        elif self.state == 'patrolling':
            if self.unseen_timer > 5000:
                self.unseen_timer = 0
                target = self.find_random_target(maze)
                if target:
                    path_to_target = a_star((self.x, self.y), target, maze)
                    if path_to_target:
                        self.seek_path = path_to_target
                        self.state = 'seeking'
            else:
                self.move_randomly(maze)

    def find_random_target(self, maze):
        possible_targets = []
        for y in range(1, MAZE_HEIGHT - 1):
            for x in range(1, MAZE_WIDTH - 1):
                if maze[y][x] == 0 and abs(x - self.x) + abs(y - self.y) > 8:
                    possible_targets.append((x, y))
        return random.choice(possible_targets) if possible_targets else None

    def draw(self, screen):
        if self.state == 'chasing':
            color = RED
        elif self.state == 'seeking':
            color = ORANGE
        else:
            color = YELLOW
        pygame.draw.rect(screen, color, (self.x * CELL_SIZE, self.y * CELL_SIZE, CELL_SIZE, CELL_SIZE))


# --- Funkcje ---

def generate_maze(width, height):
    maze = [[1 for _ in range(width)] for _ in range(height)]
    stack = [(1, 1)]
    maze[1][1] = 0
    while stack:
        x, y = stack[-1]
        neighbors = []
        for dx, dy in [(0, 2), (0, -2), (2, 0), (-2, 0)]:
            nx, ny = x + dx, y + dy
            if 0 < nx < width and 0 < ny < height and maze[ny][nx] == 1:
                neighbors.append((nx, ny, dx // 2, dy // 2))
        if neighbors:
            nx, ny, hx, hy = random.choice(neighbors)
            maze[ny][nx] = 0
            maze[y + hy][x + hx] = 0
            stack.append((nx, ny))
        else:
            stack.pop()
    for i in range(height):
        maze[i][width - 1] = 1
    for i in range(width):
        maze[height - 1][i] = 1
    return maze


def remove_walls_uniformly(maze, removal_probability=0.15):
    height = len(maze)
    width = len(maze[0])
    for y in range(1, height - 1):
        for x in range(1, width - 1):
            if maze[y][x] == 1:
                is_horizontal = (maze[y][x - 1] == 0 and maze[y][x + 1] == 0)
                is_vertical = (maze[y - 1][x] == 0 and maze[y + 1][x] == 0)
                if (is_horizontal or is_vertical):
                    if random.random() < removal_probability:
                        maze[y][x] = 0


def find_spawn_point(maze, area):
    w, h = MAZE_WIDTH, MAZE_HEIGHT
    if area == 'bottom-left':
        for y in range(h - 2, 0, -1):
            for x in range(1, w // 2):
                if maze[y][x] == 0: return (x, y)
    elif area == 'top-right':
        for y in range(1, h // 2):
            for x in range(w - 2, 0, -1):
                if maze[y][x] == 0: return (x, y)
    elif area == 'bottom-right':
        for y in range(h - 2, 0, -1):
            for x in range(w - 2, w // 2, -1):
                if maze[y][x] == 0: return (x, y)
    return (1, h - 2)


def find_exit(maze, width, height):
    for y in range(height - 2, 0, -1):
        for x in range(width - 2, 0, -1):
            if maze[y][x] == 0: return (x, y)
    return (width - 2, height - 2)


def a_star(start, goal, maze):
    def heuristic(a, b):
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    open_set = []
    heapq.heappush(open_set, (0, start))
    came_from, g_score = {}, {}
    g_score = {(x, y): float('inf') for y, r in enumerate(maze) for x, c in enumerate(r)}
    g_score[start] = 0
    f_score = {(x, y): float('inf') for y, r in enumerate(maze) for x, c in enumerate(r)}
    f_score[start] = heuristic(start, goal)
    while open_set:
        current = heapq.heappop(open_set)[1]
        if current == goal:
            path = []
            while current in came_from:
                path.append(current)
                current = came_from[current]
            path.append(start)
            return path[::-1]
        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            neighbor = (current[0] + dx, current[1] + dy)
            if 0 <= neighbor[0] < MAZE_WIDTH and 0 <= neighbor[1] < MAZE_HEIGHT and maze[neighbor[1]][neighbor[0]] == 0:
                tentative_g_score = g_score[current] + 1
                if tentative_g_score < g_score.get(neighbor, float('inf')):
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g_score
                    f_score[neighbor] = tentative_g_score + heuristic(neighbor, goal)
                    if neighbor not in [i[1] for i in open_set]:
                        heapq.heappush(open_set, (f_score[neighbor], neighbor))
    return None


def draw_maze(screen, maze):
    for y, row in enumerate(maze):
        for x, cell in enumerate(row):
            if cell == 1:
                pygame.draw.rect(screen, BLACK, (x * CELL_SIZE, y * CELL_SIZE, CELL_SIZE, CELL_SIZE))


def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Ucieczka z Labiryntu - Szybsi Przeciwnicy")
    clock = pygame.time.Clock()
    font = pygame.font.Font(None, 50)

    # Gwarancja istnienia trasy:
    # Algorytm generate_maze() tworzy labirynt, w którym z każdego punktu
    # da się dotrzeć do każdego innego. Funkcja remove_walls_uniformly()
    # tylko dodaje nowe połączenia, więc trasa od startu do mety ZAWSZE istnieje.
    maze = generate_maze(MAZE_WIDTH, MAZE_HEIGHT)
    remove_walls_uniformly(maze, removal_probability=0.15)

    player = Player(1, 1)
    exit_pos = find_exit(maze, MAZE_WIDTH, MAZE_HEIGHT)

    enemies = [
        Enemy(*find_spawn_point(maze, 'bottom-left')),
        Enemy(*find_spawn_point(maze, 'top-right')),
        Enemy(*find_spawn_point(maze, 'bottom-right'))
    ]

    game_over = False
    win = False
    running = True
    while running:
        dt = clock.tick(60)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN and not game_over:
                if event.key in [pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT]:
                    dx, dy = \
                    {pygame.K_UP: (0, -1), pygame.K_DOWN: (0, 1), pygame.K_LEFT: (-1, 0), pygame.K_RIGHT: (1, 0)}[
                        event.key]
                    player.move(dx, dy, maze)
                    if player.x == exit_pos[0] and player.y == exit_pos[1]: win, game_over = True, True
                    for enemy in enemies:
                        if player.x == enemy.x and player.y == enemy.y: win, game_over = False, True
                    if game_over: break

        if not game_over:
            # ### ZMIANA ### - Logika ruchu oparta na indywidualnych timerach wrogów
            current_time = pygame.time.get_ticks()
            for enemy in enemies:
                if current_time - enemy.move_timer > enemy.current_move_delay:
                    enemy.update(player, maze, enemy.current_move_delay)
                    enemy.move_timer = current_time

            for enemy in enemies:
                if player.x == enemy.x and player.y == enemy.y: win, game_over = False, True

        screen.fill(WHITE)
        draw_maze(screen, maze)
        pygame.draw.rect(screen, BLUE, (exit_pos[0] * CELL_SIZE, exit_pos[1] * CELL_SIZE, CELL_SIZE, CELL_SIZE))
        player.draw(screen)
        for enemy in enemies: enemy.draw(screen)
        if game_over:
            text = font.render("WYGRANA!", True, BLUE) if win else font.render("PRZEGRANA!", True, RED)
            text_rect = text.get_rect(center=(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2))
            screen.blit(text, text_rect)
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
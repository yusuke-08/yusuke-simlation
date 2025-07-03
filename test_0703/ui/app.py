import sys
import os
import numpy as np
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'agents')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'core')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'utils')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'config')))

import pygame
import time
import random
from core.museum import Museum
from utils.logger import log_guide_positions
import config




# --- jsonレイアウト反映（1か所のみ） ---
import json
def load_layout_from_json(json_path):
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    grid = data["map"]
    h, w = len(grid), len(grid[0])
    obstacle_list = []
    exhibit_grid = [[False]*w for _ in range(h)]
    for y, row in enumerate(grid):
        for x, v in enumerate(row):
            if v == 1:
                obstacle_list.append((x, y))
            elif v == 2:
                exhibit_grid[y][x] = True
    # --- 展示物: 連結成分ごとに1つの展示物とみなす ---
    from collections import deque
    visited = [[False]*w for _ in range(h)]
    exhibit_groups = []
    for y in range(h):
        for x in range(w):
            if exhibit_grid[y][x] and not visited[y][x]:
                # BFSで連結成分を探索
                q = deque()
                q.append((x, y))
                group = []
                visited[y][x] = True
                while q:
                    cx, cy = q.popleft()
                    group.append((cx, cy))
                    for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]:
                        nx, ny = cx+dx, cy+dy
                        if 0<=nx<w and 0<=ny<h and exhibit_grid[ny][nx] and not visited[ny][nx]:
                            visited[ny][nx] = True
                            q.append((nx, ny))
                exhibit_groups.append(group)
    # グループごとに中心座標も計算
    exhibit_centers = [ (sum(p[0] for p in group)/len(group), sum(p[1] for p in group)/len(group)) for group in exhibit_groups ]
    return obstacle_list, exhibit_centers, exhibit_groups

MAP_JSON_PATH = r"D:\高橋研\高橋研_シミュレーション実装\test_0703\map_json\map1.json"
print(f"[DEBUG] MAP_JSON_PATH = {MAP_JSON_PATH}")
if not os.path.exists(MAP_JSON_PATH):
    print(f"[ERROR] 指定されたMAP_JSON_PATHが存在しません: {MAP_JSON_PATH}")
    print(f"[INFO] カレントディレクトリ: {os.getcwd()}")
    raise FileNotFoundError(f"MAP_JSON_PATHが存在しません: {MAP_JSON_PATH}")
obstacle_list, exhibit_centers, exhibit_groups = load_layout_from_json(MAP_JSON_PATH)
def to_obstacle_lines_from_points(points):
    return [[pt, pt] for pt in points]
OBSTACLE_LINES = to_obstacle_lines_from_points(obstacle_list)
GUIDE_DESTINATIONS = exhibit_centers
EXHIBIT_GROUPS = exhibit_groups
log_ob_path = config.DEFAULT_LOG_OB_PATH
AGENT_POSITION_LOG_PATH = config.DEFAULT_AGENT_POSITION_LOG_PATH

# --- パラメータ設定 ---
WIDTH = config.DEFAULT_WIDTH
HEIGHT = config.DEFAULT_HEIGHT
GUIDE_START_POS = config.DEFAULT_GUIDE_START_POS
LOG_FILE_PATH = config.DEFAULT_LOG_FILE_PATH
# GUIDE_DESTINATIONS_STR = config.DEFAULT_GUIDE_DESTINATIONS  # jsonから取得するため不要
CELL_SIZE = config.DEFAULT_CELL_SIZE
MARGIN = config.DEFAULT_MARGIN
STEPS = config.DEFAULT_STEPS
NUM_VISITORS = config.DEFAULT_NUM_VISITORS
NUM_GUIDES = config.DEFAULT_NUM_GUIDES
NUM_EXHIBITS = len(EXHIBIT_GROUPS)  # 展示物数はjsonから取得



# --- Pygame初期化 ---
pygame.init()
info = pygame.display.Info()
DISPLAY_WIDTH, DISPLAY_HEIGHT = info.current_w, info.current_h

TASKBAR_MARGIN = 80
max_display_width = DISPLAY_WIDTH
max_display_height = DISPLAY_HEIGHT - TASKBAR_MARGIN

max_cell_size_w = max(1, (max_display_width - MARGIN) // WIDTH)
max_cell_size_h = max(1, (max_display_height - MARGIN) // HEIGHT)
CELL_SIZE = min(CELL_SIZE, max_cell_size_w, max_cell_size_h)

WINDOW_WIDTH = min(WIDTH * (CELL_SIZE + MARGIN) + MARGIN, max_display_width)
WINDOW_HEIGHT = min(HEIGHT * (CELL_SIZE + MARGIN) + MARGIN, max_display_height)

if WINDOW_WIDTH > max_display_width or WINDOW_HEIGHT > max_display_height:
    CELL_SIZE = 1
    WINDOW_WIDTH = min(WIDTH * (CELL_SIZE + MARGIN) + MARGIN, max_display_width)
    WINDOW_HEIGHT = min(HEIGHT * (CELL_SIZE + MARGIN) + MARGIN, max_display_height)

screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.RESIZABLE)
pygame.display.set_caption("見学施設シミュレーション (Pygame)")
clock = pygame.time.Clock()

random.seed(1)
np.random.seed(1)
model = Museum(
    WIDTH, HEIGHT, NUM_VISITORS, NUM_GUIDES, NUM_EXHIBITS, 0,
    guide_start_pos=GUIDE_START_POS,
    guide_destinations=GUIDE_DESTINATIONS,
    obstacle_lines=OBSTACLE_LINES,
    visitor_start_pos=config.DEFAULT_VISITOR_START_POS
)
model.dc.collect(model)

if os.path.dirname(LOG_FILE_PATH):
    os.makedirs(os.path.dirname(LOG_FILE_PATH), exist_ok=True)
with open(LOG_FILE_PATH, "w", encoding="utf-8") as log_file:
    log_file.write("シミュレーションログ\n")

if os.path.dirname(AGENT_POSITION_LOG_PATH):
    os.makedirs(os.path.dirname(AGENT_POSITION_LOG_PATH), exist_ok=True)
with open(AGENT_POSITION_LOG_PATH, "w", encoding="utf-8") as f:
    f.write("step,agent_type,unique_id,x,y\n")

def draw_grid(screen, model, cell_size, margin):
    screen.fill((255, 255, 255))
    win_w, win_h = screen.get_size()
    
    ### 変更点 ###
    # 描画エリアを計算する際に、マージンを考慮しないようにして描画のズレを防ぐ
    total_grid_width = WIDTH * cell_size
    total_grid_height = HEIGHT * cell_size
    offset_x = (win_w - total_grid_width) / 2
    offset_y = (win_h - total_grid_height) / 2

    # --- 障害物セルを直接描画 ---
    if hasattr(model, 'grid'):
        for x_grid in range(model.grid.width):
            for y_grid in range(model.grid.height):
                if model.grid.is_obstacle((x_grid, y_grid)):
                    rect = pygame.Rect(
                        offset_x + x_grid * cell_size,
                        offset_y + y_grid * cell_size,
                        cell_size, cell_size
                    )
                    pygame.draw.rect(screen, (100, 100, 100), rect)

    # 展示物（jsonの値そのまま、1マスずつ真四角で描画）
    for group in EXHIBIT_GROUPS:
        for (x, y) in group:
            rect = pygame.Rect(
                offset_x + x * cell_size,
                offset_y + y * cell_size,
                cell_size, cell_size
            )
            pygame.draw.rect(screen, (0, 200, 0), rect)

    # エージェント
    for agent in model.schedule.agents:
        if agent.__class__.__name__.lower().startswith('exhibit'): continue
        pos = getattr(agent, 'pos', None)
        if pos is None: continue
        
        ### 変更点 ###
        # 整数に丸めず、float座標をそのまま使って滑らかに描画
        x_float, y_float = pos
        cx = offset_x + x_float * cell_size + cell_size / 2
        cy = offset_y + y_float * cell_size + cell_size / 2

        cls_name = agent.__class__.__name__.lower()
        if cls_name.startswith('guide') or cls_name.startswith('visitor'):
            color = (0, 128, 255) if cls_name.startswith('guide') else (255, 0, 0)
            gaze = getattr(agent, 'gaze_direction', None)
            if gaze is not None and np.linalg.norm(gaze) > 0:
                import math
                angle = math.atan2(gaze[1], gaze[0])
                r = cell_size / 2 - 2
                tip = (int(cx + r * math.cos(angle)), int(cy + r * math.sin(angle)))
                base_angle1 = angle + math.radians(130)
                base_angle2 = angle - math.radians(130)
                base1 = (int(cx + r * 0.7 * math.cos(base_angle1)), int(cy + r * 0.7 * math.sin(base_angle1)))
                base2 = (int(cx + r * 0.7 * math.cos(base_angle2)), int(cy + r * 0.7 * math.sin(base_angle2)))
                pygame.draw.polygon(screen, color, [tip, base1, base2])
            else:
                pygame.draw.ellipse(screen, color, pygame.Rect(cx - cell_size/2, cy - cell_size/2, cell_size, cell_size))
        else:
            color = (200, 0, 0)
            pygame.draw.ellipse(screen, color, pygame.Rect(cx - cell_size/2, cy - cell_size/2, cell_size, cell_size))

    return offset_x, offset_y

def main_loop():
    running = True
    paused = False
    step = 0
    font = pygame.font.SysFont(None, 18)
    cell_size = CELL_SIZE
    margin = MARGIN
    global screen, model

    steps_per_frame = 3

    replay_message_timer = 0  # リプレイメッセージ表示用
    REPLAY_MESSAGE_DURATION = 60  # フレーム数（約2秒）

    def reset_simulation():
        global model, step
        random.seed(1)
        np.random.seed(1)
        model = Museum(
            WIDTH, HEIGHT, NUM_VISITORS, NUM_GUIDES, NUM_EXHIBITS, 0,
            guide_start_pos=GUIDE_START_POS,
            guide_destinations=GUIDE_DESTINATIONS,
            obstacle_lines=OBSTACLE_LINES,
            visitor_start_pos=config.DEFAULT_VISITOR_START_POS
        )
        model.dc.collect(model)
        step = 0
        # ログファイルもリセット
        if os.path.dirname(LOG_FILE_PATH):
            os.makedirs(os.path.dirname(LOG_FILE_PATH), exist_ok=True)
        with open(LOG_FILE_PATH, "w", encoding="utf-8") as log_file:
            log_file.write("シミュレーションログ\n")
        if os.path.dirname(AGENT_POSITION_LOG_PATH):
            os.makedirs(os.path.dirname(AGENT_POSITION_LOG_PATH), exist_ok=True)
        with open(AGENT_POSITION_LOG_PATH, "w", encoding="utf-8") as f:
            f.write("step,agent_type,unique_id,x,y\n")
        screen.fill((255,255,255))
        pygame.display.flip()
        nonlocal replay_message_timer
        replay_message_timer = REPLAY_MESSAGE_DURATION  # リプレイメッセージ表示

    while running:
        try:
            for event in pygame.event.get():
                if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_x):
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE:
                        paused = not paused
                    elif event.key == pygame.K_UP:
                        cell_size += 2
                    elif event.key == pygame.K_DOWN and cell_size > 4:
                        cell_size -= 2
                    elif event.key == pygame.K_r:
                        reset_simulation()
                        paused = False
            
            if not paused and step < STEPS:
                for _ in range(steps_per_frame):
                    if step >= STEPS: break
                    model.step()
                    with open(AGENT_POSITION_LOG_PATH, "a", encoding="utf-8") as f:
                        for agent in model.schedule.agents:
                            if agent.__class__.__name__.lower().startswith(('guide', 'visitor')):
                                f.write(f"{step},{agent.__class__.__name__},{agent.unique_id},{agent.pos[0]},{agent.pos[1]}\n")
                    step += 1
            offset_x, offset_y = draw_grid(screen, model, cell_size, margin)
            
            # --- 案内人の「説明中」吹き出し描画 ---
            for agent in model.schedule.agents:
                 if agent.__class__.__name__.lower().startswith('guide'):
                    is_waiting = getattr(agent, 'state', None)
                    if is_waiting and str(is_waiting).endswith('WAITING'):
                        pos = getattr(agent, 'pos', None)
                        if pos is not None:
                            cx_float = offset_x + pos[0] * cell_size + cell_size / 2
                            cy_float = offset_y + pos[1] * cell_size + cell_size / 2
                            cx = int(cx_float)
                            cy = int(cy_float)

                            bubble_w, bubble_h = 60, 28
                            bubble_rect = pygame.Rect(cx - bubble_w//2, cy - cell_size//2 - bubble_h - 8, bubble_w, bubble_h)
                            pygame.draw.rect(screen, (255,255,220), bubble_rect, border_radius=8)
                            pygame.draw.rect(screen, (180,180,120), bubble_rect, 2, border_radius=8)
                            triangle = [(cx, cy - cell_size//2 - 8), (cx - 6, cy - cell_size//2), (cx + 6, cy - cell_size//2)]
                            pygame.draw.polygon(screen, (255,255,220), triangle)
                            pygame.draw.line(screen, (180,180,120), (cx-6, cy-cell_size//2), (cx, cy-cell_size//2-8), 2)
                            pygame.draw.line(screen, (180,180,120), (cx+6, cy-cell_size//2), (cx, cy-cell_size//2-8), 2)

                            font_bubble = pygame.font.SysFont(["meiryo", "msgothic", "MS Gothic", "Yu Gothic", "Noto Sans CJK JP"], 18)
                            text_surface = font_bubble.render("説明中", True, (80, 60, 0))
                            text_rect = text_surface.get_rect(center=bubble_rect.center)
                            screen.blit(text_surface, text_rect)
            
            text = font.render(f"Step: {step}/{STEPS}", True, (0, 0, 180))
            screen.blit(text, (5, 5))

            # --- キー操作ガイド描画 ---
            guide_font = pygame.font.SysFont(["meiryo", "msgothic", "MS Gothic", "Yu Gothic", "Noto Sans CJK JP"], 15)
            guide_lines = [
                "SPACE: 一時停止/再開",
                "R: リプレイ",
                "X: 終了",
                "↑↓: 拡大縮小"
            ]
            guide_color = (0,60,200)
            margin_top = 8
            margin_right = 8
            line_height = 18
            for i, line in enumerate(guide_lines):
                guide_surface = guide_font.render(line, True, guide_color)
                guide_rect = guide_surface.get_rect()
                guide_rect.top = margin_top + i * line_height
                guide_rect.right = screen.get_width() - margin_right
                screen.blit(guide_surface, guide_rect)

            # --- 状態メッセージ描画 ---
            center_x = screen.get_width() // 2
            center_y = screen.get_height() // 2
            if paused:
                pause_font = pygame.font.SysFont(["meiryo", "msgothic", "MS Gothic", "Yu Gothic", "Noto Sans CJK JP"], 36, bold=True)
                pause_surface = pause_font.render("一時停止中", True, (0,0,0), (255,255,200))
                pause_rect = pause_surface.get_rect(center=(center_x, center_y))
                screen.blit(pause_surface, pause_rect)
            # リプレイメッセージは非表示に
            # if replay_message_timer > 0:
            #     replay_font = pygame.font.SysFont(["meiryo", "msgothic", "MS Gothic", "Yu Gothic", "Noto Sans CJK JP"], 36, bold=True)
            #     replay_surface = replay_font.render("リプレイ", True, (0,0,120), (220,255,255))
            #     replay_rect = replay_surface.get_rect(center=(center_x, center_y-50))
            #     screen.blit(replay_surface, replay_rect)
            #     replay_message_timer -= 1

            pygame.display.flip()
            clock.tick(30)
        except Exception as e:
            import traceback
            traceback.print_exc()
            running = False

if __name__ == "__main__":
    main_loop()
    pygame.quit()
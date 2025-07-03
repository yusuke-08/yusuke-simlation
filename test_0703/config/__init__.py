import re
import random

# ======================================================================
# --- グリッドサイズをマップに合わせて固定 ---
# ======================================================================
BASE_WIDTH = 40
BASE_HEIGHT = 30
SCALE_FACTOR_X = 1.0
SCALE_FACTOR_Y = 1.0

# ======================================================================
# --- ヘルパー関数 (座標のスケーリング用) ---
# ======================================================================
def scale_value_x(value, scale_x):
    return int(round(value * scale_x))
def scale_value_y(value, scale_y):
    return int(round(value * scale_y))
def scale_pos(pos, scale_x, scale_y):
    if pos is None:
        return None
    return (int(round(pos[0] * scale_x)), int(round(pos[1] * scale_y)))
def scale_line(line, scale_x, scale_y):
    if line is None:
        return None
    start, end = line
    return (scale_pos(start, scale_x, scale_y), scale_pos(end, scale_x, scale_y))
def scale_pos_list(pos_list, scale_x, scale_y):
    return [scale_pos(p, scale_x, scale_y) for p in pos_list]
def scale_line_list(line_list, scale_x, scale_y):
    return [scale_line(line, scale_x, scale_y) for line in line_list]
def scale_grouped_pos_list(grouped_list, scale_x, scale_y):
    return [scale_pos_list(group, scale_x, scale_y) for group in grouped_list]
def scale_destinations_str(dest_str, scale_x, scale_y):
    if not dest_str:
        return ""
    positions = [tuple(map(int, p.strip().split(','))) for p in dest_str.split(';') if p.strip()]
    scaled_positions = scale_pos_list(positions, scale_x, scale_y)
    return ";".join([f"{x},{y}" for x, y in scaled_positions])

# ======================================================================
# --- 基準となる値 (スケール1.0の時のオリジナル設定) ---
# ======================================================================
BASE_GUIDE_START_POS = (4, 4)
BASE_VISITOR_START_POS = (2, 2)

# --- 案内人の目的地リスト ---
DEFAULT_LOG_FILE_PATH = r"simulation_log.txt"
DEFAULT_LOG_OB_PATH = r"log_ob.txt"
DEFAULT_AGENT_POSITION_LOG_PATH = r"agent_position_log.txt"
DEFAULT_CELL_SIZE = 32
DEFAULT_MARGIN = 2
DEFAULT_STEPS = 1000
DEFAULT_NUM_VISITORS = 10
DEFAULT_NUM_GUIDES = 1
VISITOR_SPEEDS = [0.19, 0.19, 0.19, 0.18, 0.18, 0.18, 0.17, 0.17, 0.17, 0.16]

# ======================================================================
## --- スケール適用後の、実際に使われるパラメータ（障害物・展示物はjsonから動的に設定） ---
DEFAULT_WIDTH = scale_value_x(BASE_WIDTH, SCALE_FACTOR_X)
DEFAULT_HEIGHT = scale_value_y(BASE_HEIGHT, SCALE_FACTOR_Y)
DEFAULT_GUIDE_START_POS = scale_pos(BASE_GUIDE_START_POS, SCALE_FACTOR_X, SCALE_FACTOR_Y)
DEFAULT_VISITOR_START_POS = scale_pos(BASE_VISITOR_START_POS, SCALE_FACTOR_X, SCALE_FACTOR_Y)
## OBSTACLE_LINES, EXHIBIT_GROUPS, EXHIBIT_POSITIONS, DEFAULT_GUIDE_DESTINATIONS, DEFAULT_NUM_EXHIBITS は不要
def get_visitor_speeds(num_visitors=None):
    speeds = VISITOR_SPEEDS.copy()
    if num_visitors is None:
        num_visitors = DEFAULT_NUM_VISITORS
    if num_visitors <= len(speeds):
        return speeds[:num_visitors]
    else:
        base = (speeds * ((num_visitors // len(speeds)) + 1))[:num_visitors]
        return [round(s + random.uniform(-0.01, 0.01), 3) for s in base]

import numpy as np
import random
import heapq
from mesa import Agent
from agents.guide import GuideState

class Visitor(Agent):
    """
    自律的な経路計画とステアリング行動を組み合わせた見学者エージェント
    """
    def __init__(self, unique_id, pos, model, guide, max_speed=None):
        super().__init__(unique_id, model)
        # --- 基本的な属性 ---
        self.pos = np.array(pos, dtype=float)
        self.guide = guide
        
        # --- 物理的なパラメータ (論文等を参考に調整) ---
        self.max_speed = (0.23 + random.uniform(-0.01, 0.01)) if max_speed is None else max_speed  # さらに速く
        self.max_force = 2.5  # さらに強く
        self.velocity = np.array([0.0, 0.0])
        self.mass = 1.0

        # --- ナビゲーション用の属性 ---
        self.current_path = []
        self.path_step = 0
        self.replan_timer = 0  # 最初に必ず経路計画を実行
        self.arrival_threshold = 1.0 # ウェイポイントへの到達判定の半径

        # --- 視線 ---
        self.gaze_direction = np.array([1.0, 0.0])
        
        # --- 追加属性 ---
        self.last_guide_state = None  # 案内人の直前状態を記憶
        self.just_started_following = False  # 追従開始フラグ
        self.last_waypoint_step = 0  # ウェイポイントに留まったステップ数
        
    def step(self):
        # 案内人の状態遷移を検知
        if self.last_guide_state is not None and self.last_guide_state != self.guide.state:
            if self.guide.state == GuideState.MOVING:
                self.current_path = []
                self.path_step = 0
                self.just_started_following = True
        self.last_guide_state = self.guide.state

        # --- 障害物回避力は常に計算 ---
        obstacle_avoidance_force = self.avoid_obstacles()
        exhibit_avoid_force = self.avoid_exhibits()

        # 案内人が説明中（停止中）の場合は近くで待機
        if self.guide.state != GuideState.MOVING:
            to_guide = np.array(self.guide.pos) - self.pos
            dist = np.linalg.norm(to_guide)
            # 案内人への吸引
            if dist > 1.0:
                guide_force = to_guide / (dist + 1e-6) * 0.8
            else:
                guide_force = np.array([0.0, 0.0])
            # 他の見学者との距離に応じた吸引・反発
            group_force = np.array([0.0, 0.0])
            for agent in self.model.schedule.agents:
                if isinstance(agent, Visitor) and agent is not self:
                    diff = self.pos - np.array(agent.pos)
                    d = np.linalg.norm(diff)
                    if 0 < d < 0.7:
                        group_force += diff / (d + 1e-6) * 0.2
                    elif 0.7 <= d < 1.5:
                        group_force -= diff / (d + 1e-6) * 0.1
            noise = np.random.uniform(-0.1, 0.1, size=2)
            # --- 必ず障害物・展示物回避を合成 ---
            acceleration = guide_force + group_force + noise + obstacle_avoidance_force * 0.5 + exhibit_avoid_force * 0.5
            self.apply_force(acceleration)
            self.update_position()
            self.update_gaze()
            return

        # --- ここから「案内人が見える場合は直接追従、見えない場合は経路追従」分岐を明示的に復元 ---
        guide_visible = self.is_guide_visible()
        if guide_visible:
            # 視野・遮蔽判定で案内人が見える場合は直接追従
            target_pos = self.guide.pos
            has_path = True
        else:
            # 見えない場合はA*経路追従＋障害物回避
            target_pos, has_path = self.manage_path_and_get_target_v2()

        # 目標地点に向かう力と、他者から離れる力を計算
        # 追従開始直後は追従力を一時的に強化
        if getattr(self, 'just_started_following', False):
            path_following_force = self.seek(target_pos) * 10.0
            self.just_started_following = False
        else:
            path_following_force = self.seek(target_pos) * 5.0
        separation_force = self.separate() * 0.3
        # --- 障害物・展示物回避は補助的に ---
        acceleration = path_following_force + obstacle_avoidance_force * 0.5 + separation_force + exhibit_avoid_force * 0.5
        self.apply_force(acceleration)
        self.update_position()
        self.update_gaze()

    def _astar_search(self, start, end):
        """
        A*探索アルゴリズム（開始点・目標点を必ずグリッドにスナップ）
        """
        start_node = tuple(map(int, np.round(start)))
        end_node = tuple(map(int, np.round(end)))
        open_set = []
        heapq.heappush(open_set, (0, start_node))
        came_from = {}
        g_score = {start_node: 0}
        f_score = {start_node: np.linalg.norm(np.array(start_node) - np.array(end_node))}
        while open_set:
            _, current = heapq.heappop(open_set)
            if np.linalg.norm(np.array(current) - np.array(end_node)) < 1.5:
                path = []
                while current in came_from:
                    path.append(current)
                    current = came_from[current]
                path.append(start_node)
                return [np.array(p, dtype=float) for p in path[::-1]]
            for dx, dy in [(0,1), (0,-1), (1,0), (-1,0), (1,1), (1,-1), (-1,1), (-1,-1)]:
                neighbor = (current[0] + dx, current[1] + dy)
                if not (0 <= neighbor[0] < self.model.grid.width and 0 <= neighbor[1] < self.model.grid.height):
                    continue
                if self.model.grid.is_obstacle(neighbor):
                    continue
                tentative_g_score = g_score[current] + np.linalg.norm(np.array(current) - np.array(neighbor))
                if neighbor not in g_score or tentative_g_score < g_score.get(neighbor, float('inf')):
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g_score
                    f_score[neighbor] = tentative_g_score + np.linalg.norm(np.array(neighbor) - np.array(end_node))
                    if neighbor not in [i[1] for i in open_set]:
                        heapq.heappush(open_set, (f_score[neighbor], neighbor))
        return None

    def find_nearest_free_cell(self, pos):
        """
        障害物の内側や角にいる場合、最も近い空きセルを探索
        """
        from collections import deque
        visited = set()
        queue = deque()
        start = tuple(map(int, np.round(pos)))
        queue.append((start, 0))
        visited.add(start)
        while queue:
            (x, y), dist = queue.popleft()
            if not self.model.grid.is_obstacle((x, y)):
                return np.array([x, y], dtype=float)
            for dx, dy in [(-1,0),(1,0),(0,-1),(0,1),(-1,-1),(-1,1),(1,-1),(1,1)]:
                nx, ny = x+dx, y+dy
                if 0 <= nx < self.model.grid.width and 0 <= ny < self.model.grid.height:
                    if (nx, ny) not in visited:
                        visited.add((nx, ny))
                        queue.append(((nx, ny), dist+1))
        return np.array(start, dtype=float)

    def manage_path_and_get_target_v2(self):
        """
        A*による経路計画を毎ステップ実行し、現在の目標（次のウェイポイント）を返す。
        経路が見つからない場合は障害物の外側に出る方向＋案内人方向＋障害物回避で進む。
        """
        if self.guide.state != GuideState.MOVING:
            self.current_path = []
            return self.guide.pos, True
        # --- A*の開始点・目標点をグリッドにスナップ ---
        path = self._astar_search(self.pos, self.guide.pos)
        if path:
            if not self.current_path or not np.allclose(self.current_path[-1], path[-1]):
                self.current_path = path
                self.path_step = 0
                self.last_waypoint_step = 0
            while self.path_step < len(self.current_path) - 1:
                dist = np.linalg.norm(self.pos - self.current_path[self.path_step])
                if dist < self.arrival_threshold:
                    self.path_step += 1
                    self.last_waypoint_step = 0
                else:
                    break
            if self.path_step < len(self.current_path) - 1:
                if np.linalg.norm(self.pos - self.current_path[self.path_step]) > self.arrival_threshold * 2:
                    self.last_waypoint_step += 1
                    if self.last_waypoint_step > 10:
                        self.path_step += 1
                        self.last_waypoint_step = 0
                        self.just_started_following = True
            return self.current_path[self.path_step], True
        # --- 経路が見つからない場合は障害物の外側に出る方向＋案内人方向＋障害物回避 ---
        free_cell = self.find_nearest_free_cell(self.pos)
        to_free = free_cell - self.pos
        if np.linalg.norm(to_free) > 1e-3:
            to_free = to_free / np.linalg.norm(to_free)
        avoid = self.avoid_obstacles() * 2.0 + self.avoid_exhibits()
        guide_vec = np.array(self.guide.pos) - self.pos
        if np.linalg.norm(guide_vec) > 1e-3:
            guide_vec = guide_vec / np.linalg.norm(guide_vec)
        # 障害物の外側＋案内人方向＋障害物回避を強く合成
        target = self.pos + to_free * 2.0 + guide_vec + avoid
        return target, False

    def separate(self):
        """
        近すぎる他の見学者から離れる「分離」の力を計算する。
        """
        steering = np.array([0.0, 0.0])
        desired_separation = 1.5  # この距離より内側に入ると反発する
        count = 0
        for agent in self.model.schedule.agents:
            if isinstance(agent, Visitor) and agent is not self:
                ### 修正点 ###
                # agent.posがタプルである可能性を考慮し、np.array()でNumPy配列に変換する
                diff = self.pos - np.array(agent.pos)
                dist = np.linalg.norm(diff)
                if 0 < dist < desired_separation:
                    # 距離に反比例した力を加える
                    steering += diff / dist
                    count += 1
        if count > 0:
            steering /= count # 平均化

        return self.calculate_steering_force(steering)

    def seek(self, target):
        """
        目標地点に向かう「追従」の力を計算する。
        """
        ### 修正点 ###
        # targetがタプルである可能性を考慮し、np.array()でNumPy配列に変換する
        target = np.array(target)
        # 目標への望ましい速度ベクトル
        desired = target - self.pos
        if np.linalg.norm(desired) == 0:
            return np.array([0.0, 0.0])
            
        desired = desired / np.linalg.norm(desired) * self.max_speed
        
        # 現在の速度から、目標の速度に変化させるための力を計算
        steering = desired - self.velocity
        return self.calculate_steering_force(steering)

    def apply_force(self, force):
        """力（加速度）を速度に適用する (F=maより a=F/m)"""
        acceleration = force / self.mass
        self.velocity += acceleration

    def update_position(self):
        """速度に基づいて位置を更新し、画面外や障害物への移動を防ぐ"""
        # 速度制限
        norm = np.linalg.norm(self.velocity)
        if norm > self.max_speed:
            self.velocity = self.velocity / norm * self.max_speed

        next_pos = self.pos + self.velocity
        
        # 境界チェックと障害物チェック
        if not self.model.grid.out_of_bounds(tuple(next_pos)) and not self.model.grid.is_obstacle(tuple(next_pos)):
            self.pos = next_pos
            self.model.grid.move_agent(self, tuple(self.pos))
        else:
            # 壁にぶつかった場合は速度をリセット
            self.velocity = np.array([0.0, 0.0])

    def calculate_steering_force(self, steering):
        """力の大きさを制限する"""
        norm = np.linalg.norm(steering)
        if norm > self.max_force:
            steering = steering / norm * self.max_force
        return steering
        
    def update_gaze(self):
        """
        視線の向きを滑らかに更新（移動方向に徐々に追従、急激な反転を防ぐ）
        Helbing & Molnar (1995), Moussaïd et al. (2009) の推奨に基づく
        """
        if np.linalg.norm(self.velocity) > 0.01:
            new_dir = self.velocity / np.linalg.norm(self.velocity)
            alpha = 0.2  # 追従率（0.0:変化なし, 1.0:即座に移動方向）
            self.gaze_direction = (1 - alpha) * self.gaze_direction + alpha * new_dir
            norm = np.linalg.norm(self.gaze_direction)
            if norm > 1e-6:
                self.gaze_direction = self.gaze_direction / norm

    def avoid_obstacles(self):
        """
        障害物を全方向でさらに強く回避する力を返す（Helbing & Molnar, Zanlungo等）。
        """
        steering = np.array([0.0, 0.0])
        check_radius = 3.0
        for dx in range(-3, 4):
            for dy in range(-3, 4):
                if dx == 0 and dy == 0:
                    continue
                check_pos = (int(round(self.pos[0])) + dx, int(round(self.pos[1])) + dy)
                if 0 <= check_pos[0] < self.model.grid.width and 0 <= check_pos[1] < self.model.grid.height:
                    if self.model.grid.is_obstacle(check_pos):
                        diff = self.pos - np.array(check_pos)
                        dist = np.linalg.norm(diff)
                        if 0 < dist < check_radius:
                            steering += diff / (dist + 1e-6) * (2.0 / (dist**2 + 1e-6))  # さらに強化
        return self.calculate_steering_force(steering) * 2.5

    def avoid_exhibits(self):
        """
        展示物に近づきすぎないよう反発力を返す（Helbing & Molnar, Zanlungo等の障害物回避モデルに基づく）
        """
        steering = np.array([0.0, 0.0])
        repel_dist = 1.0
        for ex in self.model.exhibit_positions if hasattr(self.model, 'exhibit_positions') else []:
            diff = self.pos - np.array(ex)
            dist = np.linalg.norm(diff)
            if 0 < dist < repel_dist:
                steering += diff / (dist + 1e-6) * (1.0 / (dist**2 + 1e-6))
        return self.calculate_steering_force(steering)

    def is_guide_visible(self):
        """
        視野角・距離・遮蔽を考慮して案内人が見えるか判定
        """
        # パラメータ
        fov_deg = 120  # 視野角
        view_dist = 5.0  # 視野距離
        # 案内人へのベクトル
        to_guide = np.array(self.guide.pos) - self.pos
        dist = np.linalg.norm(to_guide)
        if dist > view_dist:
            return False
        # 視線方向との角度
        if np.linalg.norm(self.gaze_direction) < 1e-3:
            gaze = np.array([1.0, 0.0])
        else:
            gaze = self.gaze_direction
        cos_angle = np.dot(gaze, to_guide / (dist + 1e-6))
        angle = np.degrees(np.arccos(np.clip(cos_angle, -1.0, 1.0)))
        if angle > fov_deg / 2:
            return False
        # 障害物による遮蔽判定（Bresenham法）
        if self.is_occluded(self.pos, self.guide.pos):
            return False
        return True

    def is_occluded(self, start, end):
        """
        Bresenham法でstart→end間に障害物があるか判定
        """
        x0, y0 = int(round(start[0])), int(round(start[1]))
        x1, y1 = int(round(end[0])), int(round(end[1]))
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        x, y = x0, y0
        sx = 1 if x1 > x0 else -1
        sy = 1 if y1 > y0 else -1
        if dx > dy:
            err = dx / 2.0
            while x != x1:
                if (x, y) != (x0, y0) and (x, y) != (x1, y1):
                    if self.model.grid.is_obstacle((x, y)):
                        return True
                err -= dy
                if err < 0:
                    y += sy
                    err += dx
                x += sx
        else:
            err = dy / 2.0
            while y != y1:
                if (x, y) != (x0, y0) and (x, y) != (x1, y1):
                    if self.model.grid.is_obstacle((x, y)):
                        return True
                err -= dx
                if err < 0:
                    x += sx
                    err += dy
                y += sy
        return False
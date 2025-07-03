import heapq
import numpy as np
from mesa import Agent
from enum import Enum, auto
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'event')))
from event.guide_event import GuideEvent

# 案内人の行動状態を明確に定義
class GuideState(Enum):
    PLANNING = auto()   # 次の目的地と経路を計画中
    MOVING = auto()     # 経路上を移動中
    WAITING = auto()    # 目的地で待機中
    COMPLETED = auto()  # 全ての目的地を訪問完了

class Guide(Agent):
    """
    動的な経路計画で目的地を巡回する案内人エージェント
    """
    def __init__(self, unique_id, pos, model, destinations):
        super().__init__(unique_id, model)
        self.pos = pos
        self.start_position = tuple(pos)
        self.all_destinations = [tuple(d) for d in destinations]
        self.unvisited_destinations = self.all_destinations[:] # 未訪問リストを作成

        self.current_path = []
        self.path_step = 0
        
        self.state = GuideState.PLANNING
        self.wait_steps = 0
        self.wait_duration = 100  # 目的地での待機ステップ数
        self.gaze_direction = np.array([1.0, 0.0])
        self.current_event = None

    @property
    def waiting(self):
        """
        他のエージェント(visitor)が案内人の状態を判定するためのプロパティ。
        'waiting'がTrueであれば、案内人は目的地で待機中であることを示す。
        これにより、以前のvisitor.pyのコードを変更せずに連携できます。
        """
        return self.state == GuideState.WAITING

    def step(self):
        """
        エージェントの1ステップごとの行動。状態に応じて適切な処理を呼び出す。
        """
        if self.state == GuideState.PLANNING:
            self._plan_next_route()
        
        elif self.state == GuideState.MOVING:
            self._follow_path()
            
        elif self.state == GuideState.WAITING:
            # 初期位置（スタート地点）では説明イベントを発生させない
            if tuple(map(float, self.pos)) == tuple(map(float, self.start_position)):
                # 待機カウントのみ進める（イベントは発生させない）
                self.wait_steps += 1
                if self.wait_steps >= self.wait_duration:
                    self.wait_steps = 0
                    self.state = GuideState.PLANNING
                return
            # イベント発生
            if self.current_event is None:
                self.current_event = GuideEvent(self.pos)
                self.current_event.start()
                # 見学者にもイベントを通知
                for agent in self.model.schedule.agents:
                    if hasattr(agent, "on_guide_event"):
                        agent.on_guide_event(self.pos)
            self.wait_steps += 1
            if self.wait_steps >= self.wait_duration:
                self.wait_steps = 0
                if self.current_event:
                    self.current_event.end()
                    self.current_event = None
                self.state = GuideState.PLANNING # 待機完了後、次の計画へ

        elif self.state == GuideState.COMPLETED:
            # 全て完了したら何もしない
            pass

    def _plan_next_route(self):
        """現在位置から、次に訪問すべき目的地への経路を計画する"""
        target = None
        if not self.unvisited_destinations:
            # 全ての展示物を訪問済みの場合、スタート地点に戻る
            if np.linalg.norm(np.array(self.pos) - np.array(self.start_position)) > 0.1:
                target = self.start_position
            else:
                self.state = GuideState.COMPLETED
                return
        else:
            # 現在位置から最も近い「未訪問」の目的地を探す
            distances = [np.linalg.norm(np.array(self.pos) - np.array(dest)) for dest in self.unvisited_destinations]
            nearest_index = np.argmin(distances)
            target = self.unvisited_destinations.pop(nearest_index)

        # A*アルゴリズムで現在位置から目的地への経路を探索
        path = self._astar_search(self.pos, target)
        
        if path and len(path) > 1:
            self.current_path = path
            self.path_step = 0 # パスの最初からスタート
            self.state = GuideState.MOVING
        elif path and len(path) <= 1:
            # 既に目的地にいるか、非常に近い場合
            self.state = GuideState.WAITING # 即座に待機状態へ
        else:
            # 経路が見つからない場合（エラーケース）
            # print(f"警告: 案内人 {self.unique_id} は {self.pos} から {target} への経路を見つけられませんでした。")
            # 訪問リストに戻して、次のステップで再試行
            if target != self.start_position:
               self.unvisited_destinations.append(target)
            self.state = GuideState.PLANNING

    def _follow_path(self):
        """計画された経路(self.current_path)に沿って1ステップ移動する"""
        if not self.current_path or self.path_step >= len(self.current_path):
            self.state = GuideState.WAITING # パスの終点に到着
            return

        next_pos = self.current_path[self.path_step]
        direction = np.array(next_pos) - np.array(self.pos)
        dist = np.linalg.norm(direction)

        if dist > 0:
            self.gaze_direction = direction / dist
        
        speed = 0.12  # 案内人の移動速度を遅くする（例: 0.12）
        if dist > speed:
            move_pos = tuple(np.array(self.pos) + self.gaze_direction * speed)
            self.model.grid.move_agent(self, move_pos)
        else:
            self.model.grid.move_agent(self, next_pos)
            self.path_step += 1 # パスの次の waypoint へ

        # パスの最後に到達したか最終チェック
        if self.path_step >= len(self.current_path):
            self.state = GuideState.WAITING

    def _astar_search(self, start, end):
        """A*探索アルゴリズム（障害物回避）"""
        start_node = tuple(map(round, start))
        end_node = tuple(map(round, end))
        
        open_set = []
        heapq.heappush(open_set, (0, start_node))
        came_from = {}
        g_score = {start_node: 0}
        f_score = {start_node: np.linalg.norm(np.array(start_node) - np.array(end_node))}
        
        while open_set:
            _, current = heapq.heappop(open_set)
            
            if np.linalg.norm(np.array(current) - np.array(end_node)) < 1.0:
                path = []
                while current in came_from:
                    path.append(current)
                    current = came_from[current]
                path.append(start_node)
                # Mesaはfloat座標で動作するため、最終的なパスもfloatに戻す
                return [tuple(map(float, p)) for p in path[::-1]]

            # 8方向の隣接ノードをチェック
            for dx, dy in [(0,1), (0,-1), (1,0), (-1,0), (1,1), (1,-1), (-1,1), (-1,-1)]:
                neighbor = (current[0] + dx, current[1] + dy)
                
                if self.model.grid.out_of_bounds(neighbor) or self.model.grid.is_obstacle(neighbor):
                    continue
                
                tentative_g_score = g_score[current] + np.linalg.norm(np.array(current) - np.array(neighbor))
                
                if neighbor not in g_score or tentative_g_score < g_score.get(neighbor, float('inf')):
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g_score
                    f_score[neighbor] = tentative_g_score + np.linalg.norm(np.array(neighbor) - np.array(end_node))
                    if neighbor not in [i[1] for i in open_set]:
                        heapq.heappush(open_set, (f_score[neighbor], neighbor))
        return None # 経路が見つからない場合
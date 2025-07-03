# 展示物エージェントのクラス定義ファイル
# このクラスは、動かない展示物を表現します。
# シミュレーション空間内に静的に配置されます。

from mesa import Agent
import numpy as np

class Exhibit(Agent):
    """
    展示物エージェント（動かない）
    - pos: 配置座標
    """
    def __init__(self, unique_id, pos, model):
        # unique_id: エージェント固有のID
        # pos: 配置座標
        # model: シミュレーションモデル
        super().__init__(unique_id, model)
        self.pos = pos  # 展示物の位置
        self.visitor_watch_times = {}  # visitor_id: 累積滞在時間

    def step(self):
        # 展示物は毎ステップ、見学者の視野内にいるかをカウント
        for agent in self.model.schedule.agents:
            if agent.__class__.__name__.lower().startswith('visitor'):
                if self.is_visitor_watching(agent):
                    vid = getattr(agent, 'unique_id', None)
                    if vid is not None:
                        self.visitor_watch_times[vid] = self.visitor_watch_times.get(vid, 0) + 1

    def is_visitor_watching(self, visitor):
        # 視野角・距離・視線方向で判定（仮: 120度, 2.5セル以内, cosθ>0.5）
        pos_vec = np.array(self.pos) - np.array(visitor.pos)
        dist = np.linalg.norm(pos_vec)
        if dist > 2.5:
            return False
        gaze = getattr(visitor, 'gaze_direction', np.array([1.0,0.0]))
        if np.linalg.norm(gaze) == 0 or dist == 0:
            return False
        gaze = gaze / np.linalg.norm(gaze)
        pos_vec = pos_vec / dist
        cos_theta = np.dot(gaze, pos_vec)
        return cos_theta > 0.5  # 60度以内

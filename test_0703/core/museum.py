# 見学施設モデルのクラス定義ファイル
# このクラスは、エージェントや障害物の初期化、シミュレーションの進行管理を行います。
# 各メソッドや変数の役割は下記コメントを参照してください。

import random
import pandas as pd
import numpy as np
from mesa import Model
from mesa.time import RandomActivation
from mesa.datacollection import DataCollector
from .environment import Environment
from .id_generator import UniqueIDGenerator
from agents.visitor import Visitor
from agents.guide import Guide
from agents.exhibit import Exhibit
from config import get_visitor_speeds
import config

class Museum(Model):
    """
    見学施設モデル
    - エージェントや障害物の初期化
    - シミュレーションの進行管理
    """
    def __init__(self, width, height, num_visitors=0, num_guides=0, num_exhibits=4, num_obstacles=20, guide_start_pos=(1,1), guide_destinations=None, obstacle_lines=None, visitor_start_pos=None):
        self.grid = Environment(width, height, grid_width=width, grid_height=height, obstacle_lines=obstacle_lines)
        self.schedule = RandomActivation(self)
        self.id_generator = UniqueIDGenerator()
        self.dc = DataCollector(
            agent_reporters={
                "x": lambda a: a.pos[0],
                "y": lambda a: a.pos[1],
                "AgentType": lambda a: a.__class__.__name__,
            }
        )
        self.exhibit_positions = []
        self.create_exhibits(num_exhibits)
        self.set_obstacles(num_obstacles)
        if guide_destinations is None:
            guide_destinations = [exhibit.pos for exhibit in getattr(self, 'exhibits', [])]
        self.set_init_agent(Guide, num_guides, guide_start_pos, guide_destinations)
        self.set_init_agent(Visitor, num_visitors, guide_start_pos, None, visitor_start_pos=visitor_start_pos)
        self.running = True

    def create_exhibits(self, num_exhibits):
        self.exhibits = []
        exhibit_positions = getattr(config, 'EXHIBIT_POSITIONS', None)
        if exhibit_positions:
            self.exhibit_positions = list(dict.fromkeys(exhibit_positions))
            self.exhibit_lines = [[pos] for pos in self.exhibit_positions]
            for i, pos in enumerate(self.exhibit_positions):
                exhibit = Exhibit(f"Exhibit_{i}", pos, self)
                self.exhibits.append(exhibit)
                self.schedule.add(exhibit)
        else:
            self.exhibit_positions = [(2, y) for y in range(1, 6)]
            for i in range(num_exhibits):
                pos = self.exhibit_positions[i] if i < len(self.exhibit_positions) else (random.uniform(0, self.grid.width-1), random.uniform(0, self.grid.height-1))
                exhibit = Exhibit(f"Exhibit_{i}", pos, self)
                self.exhibits.append(exhibit)
                self.schedule.add(exhibit)

    def set_obstacles(self, num_obstacles):
        for _ in range(num_obstacles):
            while True:
                pos = (random.uniform(0, self.grid.width-1), random.uniform(0, self.grid.height-1))
                if not self.grid.is_obstacle(pos):
                    self.grid.place_obstacle(pos)
                    break

    def set_init_agent(self, agent_class, num_agents, guide_start_pos=(1,1), guide_destinations=None, visitor_start_pos=None):
        destinations = guide_destinations if guide_destinations is not None else [exhibit.pos for exhibit in getattr(self, 'exhibits', [])]
        guides = [agent for agent in self.schedule.agents if isinstance(agent, Guide)]
        visitor_speeds = get_visitor_speeds(num_agents) if agent_class.__name__ == "Visitor" else None
        for i in range(num_agents):
            if agent_class == Visitor:
                if not guides: raise ValueError("案内人エージェントが存在しません。")
                guide = random.choice(guides)
                pos = visitor_start_pos if visitor_start_pos else (guide.pos[0] + random.uniform(-0.5, 0.5), guide.pos[1] + random.uniform(-0.5, 0.5))
                agent = agent_class(f"Visitor_{i}", pos, self, guide, visitor_speeds[i] if visitor_speeds else None)
            elif agent_class == Guide:
                agent = agent_class(f"Guide_{i}", guide_start_pos, self, destinations)
            self.grid.place_agent(agent, agent.pos)
            self.schedule.add(agent)

    def step(self):
        self.schedule.step()
        self.dc.collect(self)

    ### 変更点 ###
    def get_guide_path_info(self):
        """
        見学者が案内人の経路情報を取得するためのヘルパー。
        複数案内人の場合は最初の案内人を返す。
        """
        guide = next((agent for agent in self.schedule.agents if isinstance(agent, Guide)), None)
        if guide and guide.current_path:
            return guide.current_path, guide.path_step
        else:
            return [], 0
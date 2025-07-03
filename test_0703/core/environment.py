# グリッド環境のクラス定義ファイル
# このクラスは、障害物や壁の配置を管理するグリッド環境を表現します。
# シミュレーション空間の外周や館内レイアウトの障害物もここで定義します。
# 各メソッドや変数の役割は下記コメントを参照してください。

from mesa.space import ContinuousSpace

class Environment(ContinuousSpace):
    """
    連続空間環境
    - 障害物や壁の配置
    - 連続座標(float)でエージェントを管理
    """
    def __init__(self, width, height, grid_width=None, grid_height=None, obstacle_lines=None):
        # width, height: 連続空間の幅・高さ（float）
        # grid_width, grid_height: 描画や障害物配置用のグリッドサイズ（int）
        super().__init__(width, height, torus=False)
        self.grid_width = grid_width or int(width)
        self.grid_height = grid_height or int(height)
        self.obstacles = set()  # 障害物のグリッド座標集合（int, int）
        self.obstacle_lines = obstacle_lines
        self.create_boundary_obstacles()
        self.create_museum_layout()

    def place_obstacle(self, pos):
        # pos: (x, y) int座標またはfloat座標
        ix, iy = int(round(pos[0])), int(round(pos[1]))
        self.obstacles.add((ix, iy))
        # 8近傍も障害物なら必ず繋げる
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                if dx == 0 and dy == 0:
                    continue
                neighbor = (ix + dx, iy + dy)
                if neighbor in self.obstacles:
                    self.obstacles.add(neighbor)

    def is_obstacle(self, pos):
        # pos: (x, y) float座標も許容
        x, y = pos
        ix, iy = int(round(x)), int(round(y))
        # 8近傍も障害物とみなす
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                if (ix + dx, iy + dy) in self.obstacles:
                    # 0.5未満の誤差なら障害物とみなす
                    if abs(x - (ix + dx)) < 0.5 and abs(y - (iy + dy)) < 0.5:
                        return True
        return False

    def out_of_bounds(self, pos):
        # pos: (x, y) float座標も許容
        x, y = pos
        return x < 0 or x >= self.width or y < 0 or y >= self.height

    def create_boundary_obstacles(self):
        # グリッド外周に壁を設置（int座標）
        for x in range(self.grid_width):
            if (x, 0) != (2, 2):
                self.place_obstacle((x, 0))
            if (x, self.grid_height - 1) != (2, 2):
                self.place_obstacle((x, self.grid_height - 1))
        for y in range(self.grid_height):
            if (0, y) != (2, 2):
                self.place_obstacle((0, y))
            if (self.grid_width - 1, y) != (2, 2):
                self.place_obstacle((self.grid_width - 1, y))

    def create_museum_layout(self):
        # パラメータから障害物線分リストを取得
        lines = self.obstacle_lines or []
        for start, end in lines:
            x0, y0 = start
            x1, y1 = end
            dx = x1 - x0
            dy = y1 - y0
            steps = max(abs(dx), abs(dy))
            if steps == 0:
                self.place_obstacle((x0, y0))
                continue
            for i in range(steps+1):
                x = x0 + dx * i / steps
                y = y0 + dy * i / steps
                self.place_obstacle((x, y))

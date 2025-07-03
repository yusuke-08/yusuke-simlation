# エージェントごとにユニークIDを発行するクラス定義ファイル
# このクラスは、各エージェントクラスごとに連番IDを発行します。
# シミュレーション内でエージェントを一意に識別するために利用します。

class UniqueIDGenerator:
    """
    エージェントごとにユニークIDを発行
    """
    def __init__(self):
        # 各エージェントクラスごとのカウンタを保持します。
        self._counters = {}

    def get_next_id(self, AgentClass):
        # AgentClassごとに連番IDを発行します。
        if AgentClass not in self._counters:
            self._counters[AgentClass] = 0
        self._counters[AgentClass] += 1
        return f"{AgentClass.__name__}_{self._counters[AgentClass]}"

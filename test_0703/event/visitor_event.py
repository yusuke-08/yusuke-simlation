class VisitorEvent:
    """
    見学者が案内人の説明イベント中に話を聞いている状態を管理するクラス
    """
    def __init__(self, exhibit_pos):
        self.exhibit_pos = exhibit_pos
        self.listening = True

    def start(self):
        # print(f"見学者が展示物 {self.exhibit_pos} で案内人の説明を聞いています。")
        self.listening = True

    def end(self):
        print(f"見学者が展示物 {self.exhibit_pos} での説明を聞き終えました。")
        self.listening = False

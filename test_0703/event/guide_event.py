class GuideEvent:
    """
    案内人が展示物に到着した際に説明イベントを発生させるクラス
    """
    def __init__(self, exhibit_pos):
        self.exhibit_pos = exhibit_pos
        self.active = True

    def start(self):
        # print(f"案内人が展示物 {self.exhibit_pos} で説明を始めました。")
        self.active = True

    def end(self):
        print(f"案内人の展示物 {self.exhibit_pos} での説明が終了しました。")
        self.active = False

# ガイドの位置をログファイルに追記する関数定義ファイル
# この関数は、各ステップごとにガイドのIDと座標をログファイルに記録します。
# シミュレーションの進行状況を外部ファイルに保存する用途で利用します。

import os

def log_guide_positions(model, log_file_path):
    # model: シミュレーションモデル
    # log_file_path: ログファイルのパス
    # 各ステップごとにガイドのIDと座標を記録します。
    with open(log_file_path, "a", encoding="utf-8") as log_file:
        log_file.write(f"Step {model.schedule.steps}:\n")
        for agent in model.schedule.agents:
            if agent.__class__.__name__ == "Guide":
                log_file.write(f"  {agent.unique_id}: {agent.pos}\n")

def log_visitor_scores(model, log_file_path):
    # 各見学者の展示物ごとの滞在スコアを記録
    with open(log_file_path, "w", encoding="utf-8") as log_file:
        log_file.write("visitor_id,exhibit_id,watch_time\n")
        for agent in model.schedule.agents:
            if agent.__class__.__name__.lower().startswith('visitor'):
                for eid, score in getattr(agent, 'exhibit_watch_times', {}).items():
                    log_file.write(f"{agent.unique_id},{eid},{score}\n")

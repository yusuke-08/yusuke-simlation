環境周り
①言語
Python 3.12.1

②マルチエージェントシミュレーション
Mesa 2.1.5

③可視化
Plotly 5.19.0

④アプリ化
Streamlit 1.31.1




# シミュレーション分割構成と役割まとめ

simulation/
├─ agents/
│    ├─ visitor.py      # 見学者エージェント（Visitorクラス）
│    ├─ guide.py        # 案内人エージェント（Guideクラス）
│    └─ exhibit.py      # 展示物エージェント（Exhibitクラス）
├─ core/
│    ├─ environment.py  # 環境（グリッド・障害物管理 Environmentクラス）
│    ├─ museum.py       # モデル本体（Museumクラス）
│    └─ id_generator.py # ユニークID生成（UniqueIDGeneratorクラス）
├─ utils/
│    └─ logger.py       # ログ記録用関数
├─ ui/
│    └─ app.py          # Streamlit UI・実行部
├─ config.py            # 定数・設定

【役割説明】
- agents/         : エージェント（見学者・案内人・展示物）ごとにクラスを分割
- core/           : 環境やモデル本体、ID生成などシミュレーションの中核
- utils/          : ログ記録など補助的な機能
- ui/             : StreamlitによるUI・実行スクリプト
- config.py       : 定数やパスなどの設定

この構成により、各役割ごとにファイルが整理され、保守性・拡張性が向上します。

【実行方法】
1. コマンドプロンプトやPowerShellで simulation ディレクトリ直下に移動
   例: cd D:\高橋研\高橋研_シミュレーション実装\simulation

2. Streamlitアプリを起動
   例: streamlit run ui/app.py

3. ブラウザで http://localhost:8501 などにアクセスし、シミュレーションUIを操作

【VSCodeでの実行方法】
1. VSCodeで simulation フォルダをワークスペースとして開く。
2. 左側の「ターミナル」パネルを開く（メニュー「ターミナル」→「新しいターミナル」）。
3. ターミナルで simulation ディレクトリ直下になっていることを確認。
   例: cd D:\高橋研\高橋研_シミュレーション実装\simulation
4. 以下のコマンドをターミナルで実行：
   streamlit run ui/app.py
5. VSCode右下に「Streamlit」拡張機能が入っていれば、エディタ内でプレビューも可能。
   （なければブラウザで http://localhost:8501 を開く）

【補足】
- requirements.txt を作成しておくと VSCode のターミナルで `pip install -r requirements.txt` で依存パッケージを一括インストールできます。
- VSCodeの「Python」拡張機能を有効にしておくと便利です。

【注意】
- Pythonの仮想環境を推奨。必要なパッケージ（mesa, streamlit, plotly, numpy, pandas等）をインストールしてください。
- Windowsパスのバックスラッシュに注意。
- 各ディレクトリに __init__.py が必要です。

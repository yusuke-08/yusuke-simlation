import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser
import json
import os
from PIL import Image, ImageTk
import math


class MapEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("見学施設マップ作成ソフト")
        self.root.geometry("1200x800")

        # 設定ファイルのパス
        self.config_file = "map_editor_config.json"

        # デフォルト設定
        self.default_config = {
            "cell_types": {
                "0": {"name": "通路", "color": "#FFFFFF"},
                "1": {"name": "壁", "color": "#000000"},
                "2": {"name": "展示物", "color": "#0000FF"},
            }
        }

        # ドラッグ選択用フラグ
        self.is_dragging = False

        # 設定読み込み
        self.load_config()

        # マップデータ
        self.map_width = 10
        self.map_height = 10
        self.map_data = [
            [0 for _ in range(self.map_width)] for _ in range(self.map_height)
        ]

        # 表示設定
        self.cell_size = 30
        self.zoom_factor = 1.0
        self.show_grid = True
        self.current_cell_type = 0

        # 下絵設定
        self.background_image = None
        self.background_photo = None
        self.background_alpha = 0.5

        # UI構築
        self.create_widgets()
        self.update_canvas()

    def load_config(self):
        """設定ファイルを読み込み"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, "r", encoding="utf-8") as f:
                    self.config = json.load(f)
            else:
                self.config = self.default_config.copy()
                self.save_config()
        except Exception as e:
            messagebox.showerror("エラー", f"設定ファイルの読み込みに失敗しました: {e}")
            self.config = self.default_config.copy()

    def save_config(self):
        """設定ファイルを保存"""
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            messagebox.showerror("エラー", f"設定ファイルの保存に失敗しました: {e}")

    def create_widgets(self):
        """UI要素を作成"""
        # メインフレーム
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 左側のコントロールパネル
        control_frame = ttk.Frame(main_frame, width=250)
        control_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5))
        control_frame.pack_propagate(False)

        # ファイル操作
        file_frame = ttk.LabelFrame(control_frame, text="ファイル操作")
        file_frame.pack(fill=tk.X, pady=(0, 5))

        ttk.Button(file_frame, text="新規作成", command=self.new_map).pack(
            fill=tk.X, pady=2
        )
        ttk.Button(file_frame, text="開く", command=self.load_map).pack(
            fill=tk.X, pady=2
        )
        ttk.Button(file_frame, text="保存", command=self.save_map).pack(
            fill=tk.X, pady=2
        )

        # マップサイズ設定
        size_frame = ttk.LabelFrame(control_frame, text="マップサイズ")
        size_frame.pack(fill=tk.X, pady=(0, 5))

        ttk.Label(size_frame, text="幅:").grid(row=0, column=0, sticky=tk.W)
        self.width_var = tk.IntVar(value=self.map_width)
        ttk.Entry(size_frame, textvariable=self.width_var, width=8).grid(
            row=0, column=1
        )

        ttk.Label(size_frame, text="高さ:").grid(row=1, column=0, sticky=tk.W)
        self.height_var = tk.IntVar(value=self.map_height)
        ttk.Entry(size_frame, textvariable=self.height_var, width=8).grid(
            row=1, column=1
        )

        ttk.Button(size_frame, text="適用", command=self.resize_map).grid(
            row=2, column=0, columnspan=2, pady=5
        )

        # セル種類選択
        cell_frame = ttk.LabelFrame(control_frame, text="セル種類")
        cell_frame.pack(fill=tk.X, pady=(0, 5))

        self.cell_type_var = tk.IntVar(value=self.current_cell_type)
        self.cell_buttons = []
        self.update_cell_type_buttons(cell_frame)

        # 表示設定
        display_frame = ttk.LabelFrame(control_frame, text="表示設定")
        display_frame.pack(fill=tk.X, pady=(0, 5))

        # グリッド表示
        self.grid_var = tk.BooleanVar(value=self.show_grid)
        ttk.Checkbutton(
            display_frame,
            text="グリッド表示",
            variable=self.grid_var,
            command=self.toggle_grid,
        ).pack(anchor=tk.W)

        # ズーム
        zoom_frame = ttk.Frame(display_frame)
        zoom_frame.pack(fill=tk.X, pady=2)
        ttk.Label(zoom_frame, text="ズーム:").pack(side=tk.LEFT)
        ttk.Button(zoom_frame, text="-", command=self.zoom_out, width=3).pack(
            side=tk.LEFT, padx=2
        )
        ttk.Button(zoom_frame, text="+", command=self.zoom_in, width=3).pack(
            side=tk.LEFT, padx=2
        )
        ttk.Button(zoom_frame, text="リセット", command=self.zoom_reset).pack(
            side=tk.LEFT, padx=2
        )

        # 下絵設定
        bg_frame = ttk.LabelFrame(control_frame, text="下絵設定")
        bg_frame.pack(fill=tk.X, pady=(0, 5))

        ttk.Button(bg_frame, text="画像読み込み", command=self.load_background).pack(
            fill=tk.X, pady=2
        )
        ttk.Button(bg_frame, text="画像クリア", command=self.clear_background).pack(
            fill=tk.X, pady=2
        )

        # 透明度調整
        ttk.Label(bg_frame, text="透明度:").pack(anchor=tk.W)
        self.alpha_var = tk.DoubleVar(value=self.background_alpha)
        alpha_scale = ttk.Scale(
            bg_frame,
            from_=0.0,
            to=1.0,
            variable=self.alpha_var,
            command=self.update_background_alpha,
        )
        alpha_scale.pack(fill=tk.X, pady=2)

        # 設定管理
        config_frame = ttk.LabelFrame(control_frame, text="設定管理")
        config_frame.pack(fill=tk.X, pady=(0, 5))

        ttk.Button(
            config_frame, text="セル種類設定", command=self.open_cell_config
        ).pack(fill=tk.X, pady=2)

        # 右側のキャンバスエリア
        canvas_frame = ttk.Frame(main_frame)
        canvas_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # スクロールバー付きキャンバス
        self.canvas = tk.Canvas(canvas_frame, bg="white")

        h_scrollbar = ttk.Scrollbar(
            canvas_frame, orient=tk.HORIZONTAL, command=self.canvas.xview
        )
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)

        v_scrollbar = ttk.Scrollbar(
            canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview
        )
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.canvas.configure(
            xscrollcommand=h_scrollbar.set, yscrollcommand=v_scrollbar.set
        )

        # キャンバスイベント
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_release)
        self.canvas.bind("<MouseWheel>", self.on_mouse_wheel)

    def update_cell_type_buttons(self, parent):
        """セル種類ボタンを更新"""
        # 既存のボタンを削除
        for widget in parent.winfo_children():
            if isinstance(widget, tk.Radiobutton):
                widget.destroy()

        self.cell_buttons.clear()

        # 新しいボタンを作成
        for cell_type, info in self.config["cell_types"].items():
            btn = tk.Radiobutton(
                parent,
                text=f"{cell_type}: {info['name']}",
                variable=self.cell_type_var,
                value=int(cell_type),
                bg=info["color"],
                command=self.change_cell_type,
            )
            btn.pack(anchor=tk.W, pady=1)
            self.cell_buttons.append(btn)

    def change_cell_type(self):
        """選択されたセル種類を変更"""
        self.current_cell_type = self.cell_type_var.get()

    def new_map(self):
        """新規マップ作成"""
        self.map_width = 10
        self.map_height = 10
        self.map_data = [
            [0 for _ in range(self.map_width)] for _ in range(self.map_height)
        ]
        self.width_var.set(self.map_width)
        self.height_var.set(self.map_height)
        self.clear_background()
        self.update_canvas()

    def resize_map(self):
        """マップサイズを変更"""
        new_width = self.width_var.get()
        new_height = self.height_var.get()

        if new_width <= 0 or new_height <= 0:
            messagebox.showerror("エラー", "サイズは1以上にしてください")
            return

        # 新しいマップデータを作成
        new_map_data = [[0 for _ in range(new_width)] for _ in range(new_height)]

        # 既存データをコピー
        for y in range(min(self.map_height, new_height)):
            for x in range(min(self.map_width, new_width)):
                new_map_data[y][x] = self.map_data[y][x]

        self.map_width = new_width
        self.map_height = new_height
        self.map_data = new_map_data
        self.update_canvas()

    def load_map(self):
        """マップファイルを読み込み"""
        filename = filedialog.askopenfilename(
            title="マップファイルを開く",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )

        if filename:
            try:
                with open(filename, "r", encoding="utf-8") as f:
                    data = json.load(f)

                if "map" not in data:
                    messagebox.showerror("エラー", "不正なマップファイルです")
                    return

                self.map_data = data["map"]
                self.map_height = len(self.map_data)
                self.map_width = len(self.map_data[0]) if self.map_height > 0 else 0

                self.width_var.set(self.map_width)
                self.height_var.set(self.map_height)
                self.update_canvas()

                messagebox.showinfo("成功", "マップを読み込みました")

            except Exception as e:
                messagebox.showerror("エラー", f"ファイルの読み込みに失敗しました: {e}")

    def save_map(self):
        """マップファイルを保存"""
        filename = filedialog.asksaveasfilename(
            title="マップファイルを保存",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )

        if filename:
            try:
                data = {"map": self.map_data}
                with open(filename, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)

                messagebox.showinfo("成功", "マップを保存しました")

            except Exception as e:
                messagebox.showerror("エラー", f"ファイルの保存に失敗しました: {e}")

    def load_background(self):
        """下絵画像を読み込み"""
        filename = filedialog.askopenfilename(
            title="下絵画像を開く",
            filetypes=[
                ("PNG files", "*.png"),
                ("JPEG files", "*.jpg"),
                ("All files", "*.*"),
            ],
        )

        if filename:
            try:
                self.background_image = Image.open(filename)
                self.update_canvas()
                messagebox.showinfo("成功", "下絵を読み込みました")
            except Exception as e:
                messagebox.showerror("エラー", f"画像の読み込みに失敗しました: {e}")

    def clear_background(self):
        """下絵をクリア"""
        self.background_image = None
        self.background_photo = None
        self.update_canvas()

    def update_background_alpha(self, value):
        """下絵の透明度を更新"""
        self.background_alpha = float(value)
        self.update_canvas()

    def toggle_grid(self):
        """グリッド表示を切り替え"""
        self.show_grid = self.grid_var.get()
        self.update_canvas()

    def zoom_in(self):
        """ズームイン"""
        self.zoom_factor *= 1.2
        self.update_canvas()

    def zoom_out(self):
        """ズームアウト"""
        self.zoom_factor /= 1.2
        self.update_canvas()

    def zoom_reset(self):
        """ズームリセット"""
        self.zoom_factor = 1.0
        self.update_canvas()

    def on_mouse_wheel(self, event):
        """マウスホイールでズーム"""
        if event.delta > 0:
            self.zoom_in()
        else:
            self.zoom_out()

    def on_canvas_click(self, event):
        """キャンバスクリック処理（ドラッグ開始）"""
        self.is_dragging = True
        self.paint_cell(event)

    def on_canvas_drag(self, event):
        """ドラッグ中のセル塗りつぶし"""
        if self.is_dragging:
            self.paint_cell(event)

    def on_canvas_release(self, event):
        """ドラッグ終了"""
        self.is_dragging = False

    def paint_cell(self, event):
        """指定位置のセルを塗りつぶす"""
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        cell_size = self.cell_size * self.zoom_factor
        grid_x = int(canvas_x // cell_size)
        grid_y = int(canvas_y // cell_size)
        if 0 <= grid_x < self.map_width and 0 <= grid_y < self.map_height:
            if self.map_data[grid_y][grid_x] != self.current_cell_type:
                self.map_data[grid_y][grid_x] = self.current_cell_type
                self.update_canvas()

    def update_canvas(self):
        """キャンバスを更新"""
        self.canvas.delete("all")

        cell_size = self.cell_size * self.zoom_factor
        canvas_width = self.map_width * cell_size
        canvas_height = self.map_height * cell_size

        # スクロール領域を設定
        self.canvas.configure(scrollregion=(0, 0, canvas_width, canvas_height))

        # 下絵を描画
        if self.background_image:
            # 画像をマップサイズに合わせてリサイズ
            bg_image = self.background_image.resize(
                (int(canvas_width), int(canvas_height)), Image.Resampling.LANCZOS
            )

            # 透明度を適用
            if bg_image.mode != "RGBA":
                bg_image = bg_image.convert("RGBA")

            # アルファチャンネルを調整
            alpha = int(255 * self.background_alpha)
            bg_image.putalpha(alpha)

            self.background_photo = ImageTk.PhotoImage(bg_image)
            self.canvas.create_image(0, 0, anchor=tk.NW, image=self.background_photo)

        # マップを描画
        for y in range(self.map_height):
            for x in range(self.map_width):
                x1 = x * cell_size
                y1 = y * cell_size
                x2 = x1 + cell_size
                y2 = y1 + cell_size

                cell_type = str(self.map_data[y][x])
                color = self.config["cell_types"].get(cell_type, {"color": "#CCCCCC"})[
                    "color"
                ]

                # セルを描画（下絵がある場合は半透明）
                if self.background_image:
                    # 半透明の効果を出すために線だけ描画
                    self.canvas.create_rectangle(
                        x1, y1, x2, y2, outline=color, width=2, fill=""
                    )
                else:
                    self.canvas.create_rectangle(
                        x1, y1, x2, y2, fill=color, outline="black"
                    )

        # グリッド線を描画
        if self.show_grid:
            for x in range(self.map_width + 1):
                x_pos = x * cell_size
                self.canvas.create_line(
                    x_pos, 0, x_pos, canvas_height, fill="gray", width=1
                )

            for y in range(self.map_height + 1):
                y_pos = y * cell_size
                self.canvas.create_line(
                    0, y_pos, canvas_width, y_pos, fill="gray", width=1
                )

    def open_cell_config(self):
        """セル種類設定ウィンドウを開く"""
        config_window = tk.Toplevel(self.root)
        config_window.title("セル種類設定")
        config_window.geometry("400x300")

        # リストボックス
        list_frame = ttk.Frame(config_window)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.cell_listbox = tk.Listbox(list_frame)
        self.cell_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(
            list_frame, orient=tk.VERTICAL, command=self.cell_listbox.yview
        )
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.cell_listbox.configure(yscrollcommand=scrollbar.set)

        # セル種類リストを更新
        self.update_cell_listbox()

        # ボタンフレーム
        button_frame = ttk.Frame(config_window)
        button_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        ttk.Button(button_frame, text="追加", command=self.add_cell_type).pack(
            side=tk.LEFT, padx=2
        )
        ttk.Button(button_frame, text="編集", command=self.edit_cell_type).pack(
            side=tk.LEFT, padx=2
        )
        ttk.Button(button_frame, text="削除", command=self.delete_cell_type).pack(
            side=tk.LEFT, padx=2
        )
        ttk.Button(
            button_frame,
            text="適用",
            command=lambda: self.apply_cell_config(config_window),
        ).pack(side=tk.RIGHT, padx=2)

    def update_cell_listbox(self):
        """セル種類リストボックスを更新"""
        self.cell_listbox.delete(0, tk.END)
        for cell_type, info in self.config["cell_types"].items():
            self.cell_listbox.insert(
                tk.END, f"{cell_type}: {info['name']} ({info['color']})"
            )

    def add_cell_type(self):
        """セル種類を追加"""
        self.edit_cell_type_dialog()

    def edit_cell_type(self):
        """セル種類を編集"""
        selection = self.cell_listbox.curselection()
        if not selection:
            messagebox.showwarning("警告", "編集するセル種類を選択してください")
            return

        index = selection[0]
        cell_types = list(self.config["cell_types"].keys())
        cell_type = cell_types[index]
        self.edit_cell_type_dialog(cell_type)

    def delete_cell_type(self):
        """セル種類を削除"""
        selection = self.cell_listbox.curselection()
        if not selection:
            messagebox.showwarning("警告", "削除するセル種類を選択してください")
            return

        index = selection[0]
        cell_types = list(self.config["cell_types"].keys())
        cell_type = cell_types[index]

        if messagebox.askyesno("確認", f"セル種類 '{cell_type}' を削除しますか？"):
            del self.config["cell_types"][cell_type]
            self.update_cell_listbox()

    def edit_cell_type_dialog(self, cell_type=None):
        """セル種類編集ダイアログ"""
        dialog = tk.Toplevel(self.root)
        dialog.title("セル種類編集" if cell_type else "セル種類追加")
        dialog.geometry("300x150")

        # 現在の値を取得
        if cell_type:
            current_name = self.config["cell_types"][cell_type]["name"]
            current_color = self.config["cell_types"][cell_type]["color"]
        else:
            cell_type = ""
            current_name = ""
            current_color = "#FFFFFF"

        # 入力フィールド
        ttk.Label(dialog, text="番号:").grid(
            row=0, column=0, sticky=tk.W, padx=5, pady=5
        )
        type_var = tk.StringVar(value=cell_type)
        ttk.Entry(dialog, textvariable=type_var).grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(dialog, text="名前:").grid(
            row=1, column=0, sticky=tk.W, padx=5, pady=5
        )
        name_var = tk.StringVar(value=current_name)
        ttk.Entry(dialog, textvariable=name_var).grid(row=1, column=1, padx=5, pady=5)

        ttk.Label(dialog, text="色:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        color_var = tk.StringVar(value=current_color)
        color_frame = ttk.Frame(dialog)
        color_frame.grid(row=2, column=1, padx=5, pady=5)

        color_entry = ttk.Entry(color_frame, textvariable=color_var, width=10)
        color_entry.pack(side=tk.LEFT)

        def choose_color():
            color = colorchooser.askcolor(initialcolor=color_var.get())[1]
            if color:
                color_var.set(color)

        ttk.Button(color_frame, text="選択", command=choose_color).pack(
            side=tk.LEFT, padx=5
        )

        # ボタン
        button_frame = ttk.Frame(dialog)
        button_frame.grid(row=3, column=0, columnspan=2, pady=10)

        def save_cell_type():
            new_type = type_var.get().strip()
            new_name = name_var.get().strip()
            new_color = color_var.get().strip()

            if not new_type or not new_name or not new_color:
                messagebox.showerror("エラー", "すべての項目を入力してください")
                return

            try:
                # 番号が数字かチェック
                int(new_type)
            except ValueError:
                messagebox.showerror("エラー", "番号は数字で入力してください")
                return

            self.config["cell_types"][new_type] = {"name": new_name, "color": new_color}
            self.update_cell_listbox()
            dialog.destroy()

        ttk.Button(button_frame, text="保存", command=save_cell_type).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(button_frame, text="キャンセル", command=dialog.destroy).pack(
            side=tk.LEFT, padx=5
        )

    def apply_cell_config(self, window):
        """セル種類設定を適用"""
        self.save_config()
        # セル種類ボタンを更新
        for widget in self.root.winfo_children():
            self.update_cell_type_buttons_recursive(widget)
        window.destroy()
        self.update_canvas()

    def update_cell_type_buttons_recursive(self, widget):
        """再帰的にセル種類ボタンを更新"""
        if hasattr(widget, "winfo_children"):
            for child in widget.winfo_children():
                if (
                    isinstance(child, ttk.LabelFrame)
                    and child.cget("text") == "セル種類"
                ):
                    self.update_cell_type_buttons(child)
                else:
                    self.update_cell_type_buttons_recursive(child)


def main():
    root = tk.Tk()
    app = MapEditor(root)
    root.mainloop()


if __name__ == "__main__":
    main()

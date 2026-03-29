import logging
import os
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from tkinter import filedialog
from typing import Callable


def _rate_str_to_pct(rate: str) -> int:
    """edge-ttsのrate文字列（例: '+50%', '-20%', '+0%'）をパーセント整数（150, 80, 100）に変換."""
    try:
        val = int(rate.replace("%", "").replace("+", ""))
        return max(0, min(300, 100 + val))
    except (ValueError, AttributeError):
        return 100


def _pct_to_rate_str(pct: int) -> str:
    """パーセント整数（150, 80, 100）をedge-ttsのrate文字列に変換."""
    diff = pct - 100
    if diff >= 0:
        return f"+{diff}%"
    return f"{diff}%"


@dataclass
class FormResult:
    file_path: str
    rate: str
    volume: int


class TkTextHandler(logging.Handler):
    """logging.Handler that writes to a tkinter Text widget (thread-safe)."""

    def __init__(self, text_widget: tk.Text, root: tk.Tk) -> None:
        super().__init__()
        self._text = text_widget
        self._root = root

    def emit(self, record: logging.LogRecord) -> None:
        msg = self.format(record) + "\n"
        try:
            self._root.after(0, self._append, msg)
        except RuntimeError:
            pass  # window already destroyed

    def _append(self, msg: str) -> None:
        self._text.insert(tk.END, msg)
        self._text.see(tk.END)


class StartupForm:
    def __init__(
        self,
        initial_file: str,
        initial_rate: str,
        initial_volume: int = 100,
        filters_path: Path | None = None,
        on_start: Callable[[FormResult], None] | None = None,
        on_stop: Callable[[], None] | None = None,
        on_rate_change: Callable[[str], None] | None = None,
        on_volume_change: Callable[[int], None] | None = None,
    ) -> None:
        self._initial_file = initial_file
        self._initial_rate = initial_rate
        self._initial_volume = initial_volume
        self._filters_path = filters_path
        self._on_start = on_start
        self._on_stop = on_stop
        self._on_rate_change = on_rate_change
        self._on_volume_change = on_volume_change
        self._running = False
        self._result: FormResult | None = None

    def show(self) -> FormResult | None:
        root = tk.Tk()
        root.title("sl_say - 設定")
        root.option_add("*Font", "メイリオ 10")

        # ウィンドウアイコン設定
        import sys
        base = Path(getattr(sys, '_MEIPASS', Path(__file__).parent))
        icon_path = base / "app" / "icon.ico"
        if not icon_path.exists():
            icon_path = Path(__file__).parent / "icon.ico"
        if icon_path.exists():
            root.iconbitmap(str(icon_path))

        # --- 設定フレーム ---
        config_frame = tk.Frame(root, padx=16, pady=16)
        config_frame.pack(fill="x")

        # ログファイルパス
        tk.Label(config_frame, text="ログファイルパス:").grid(
            row=0, column=0, sticky="w", pady=(0, 4),
        )
        file_var = tk.StringVar(value=self._initial_file)
        file_entry = tk.Entry(config_frame, textvariable=file_var, width=60)
        file_entry.grid(row=1, column=0, padx=(0, 8), pady=(0, 8))

        def browse() -> None:
            current = file_var.get().strip()
            initial_dir = ""
            if current:
                if os.path.isfile(current):
                    initial_dir = os.path.dirname(current)
                elif os.path.isdir(current):
                    initial_dir = current
            path = filedialog.askopenfilename(
                title="ログファイルを選択",
                initialdir=initial_dir or None,
                filetypes=[("テキストファイル", "*.txt"), ("すべて", "*.*")],
            )
            if path:
                file_var.set(path)

        browse_btn = tk.Button(config_frame, text="参照...", command=browse)
        browse_btn.grid(row=1, column=1, pady=(0, 8))

        # 再生速度（0-300%、スライダー）
        initial_rate_pct = _rate_str_to_pct(self._initial_rate)
        rate_label_var = tk.StringVar(value=f"再生速度: {initial_rate_pct}%")
        tk.Label(config_frame, textvariable=rate_label_var).grid(
            row=2, column=0, sticky="w", pady=(0, 4),
        )
        rate_var = tk.IntVar(value=initial_rate_pct)

        def on_rate_slider(v: str) -> None:
            rate_label_var.set(f"再生速度: {v}%")
            if self._running and self._on_rate_change:
                self._on_rate_change(_pct_to_rate_str(int(v)))

        rate_scale = tk.Scale(
            config_frame, from_=0, to=300, orient="horizontal",
            variable=rate_var, showvalue=False, length=300,
            command=on_rate_slider,
        )
        rate_scale.grid(row=3, column=0, columnspan=2, sticky="w", pady=(0, 12))

        # 音量
        volume_label_var = tk.StringVar(value=f"音量: {self._initial_volume}")
        tk.Label(config_frame, textvariable=volume_label_var).grid(
            row=4, column=0, sticky="w", pady=(0, 4),
        )
        volume_var = tk.IntVar(value=self._initial_volume)

        def on_volume_slider(v: str) -> None:
            volume_label_var.set(f"音量: {v}")
            if self._running and self._on_volume_change:
                self._on_volume_change(int(v))

        volume_scale = tk.Scale(
            config_frame, from_=0, to=100, orient="horizontal",
            variable=volume_var, showvalue=False, length=300,
            command=on_volume_slider,
        )
        volume_scale.grid(row=5, column=0, columnspan=2, sticky="w", pady=(0, 12))

        # エラー表示用ラベル
        error_var = tk.StringVar()
        tk.Label(config_frame, textvariable=error_var, fg="red").grid(
            row=6, column=0, columnspan=2, sticky="w", pady=(0, 8),
        )

        # --- ログフレーム（初期非表示） ---
        log_frame = tk.Frame(root, padx=16)
        log_text = tk.Text(log_frame, height=15, width=80, state="disabled", wrap="word")
        scrollbar = tk.Scrollbar(log_frame, command=log_text.yview)
        log_text.configure(yscrollcommand=scrollbar.set)
        log_text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # カスタムログハンドラ
        log_handler = TkTextHandler(log_text, root)
        log_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))

        # 無効化対象ウィジェット
        input_widgets = [file_entry, browse_btn]

        def switch_to_running_mode() -> None:
            for w in input_widgets:
                w.configure(state="disabled")
            start_btn.configure(state="disabled")
            stop_btn.configure(state="normal")
            self._running = True
            log_frame.pack(fill="both", expand=True, pady=(0, 16))
            log_text.configure(state="normal")
            root.resizable(True, True)
            root.geometry("700x500")
            logging.getLogger().addHandler(log_handler)

        def switch_to_config_mode() -> None:
            self._running = False
            for w in input_widgets:
                w.configure(state="normal")
            start_btn.configure(state="normal")
            stop_btn.configure(state="disabled")
            log_frame.pack_forget()
            root.resizable(False, False)
            root.geometry("")
            logging.getLogger().removeHandler(log_handler)
            log_text.delete("1.0", tk.END)

        def on_start() -> None:
            file_path = file_var.get().strip()
            if not file_path:
                error_var.set("ログファイルパスを入力してください。")
                return
            if not os.path.exists(file_path):
                error_var.set(f"ファイルが見つかりません: {file_path}")
                return
            error_var.set("")
            self._result = FormResult(
                file_path=file_path,
                rate=_pct_to_rate_str(rate_var.get()),
                volume=volume_var.get(),
            )
            switch_to_running_mode()
            if self._on_start:
                self._on_start(self._result)

        def on_stop() -> None:
            if self._on_stop:
                self._on_stop()
            switch_to_config_mode()

        btn_frame = tk.Frame(config_frame)
        btn_frame.grid(row=7, column=0, columnspan=2, pady=(4, 0))
        start_btn = tk.Button(btn_frame, text="開始", command=on_start, width=12)
        start_btn.pack(side="left", padx=(0, 8))
        stop_btn = tk.Button(btn_frame, text="停止", command=on_stop, width=12, state="disabled")
        stop_btn.pack(side="left")

        # フィルタ設定を開くリンク
        if self._filters_path:
            def open_filters() -> None:
                if self._filters_path and self._filters_path.exists():
                    os.startfile(self._filters_path)  # type: ignore[attr-defined]

            link = tk.Label(config_frame, text="フィルタ設定を開く", fg="blue", cursor="hand2")
            link.grid(row=8, column=0, columnspan=2, pady=(8, 0))
            link.bind("<Button-1>", lambda e: open_filters())

        def on_close() -> None:
            logging.getLogger().removeHandler(log_handler)
            root.destroy()

        root.protocol("WM_DELETE_WINDOW", on_close)
        root.mainloop()
        return self._result

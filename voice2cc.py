"""
Voice2CC v2 — 语音输入到 Claude Code（带 GUI 悬浮窗 + 实时音量条 + 自检）

热键（默认）：按住 Ctrl+Shift+Space → 松开转写并粘贴
拖动悬浮窗：鼠标按住窗口拖动到任何位置
退出：点窗口右上角 ×（或终端 Ctrl+C）
"""
import os
import re
import sys
import time

# 让 emoji 在 Windows GBK 终端也能 print
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import queue
import threading
import tempfile
import tkinter as tk
from pathlib import Path

import numpy as np
import sounddevice as sd
import soundfile as sf
import requests
import pyperclip
from pynput import keyboard
from dotenv import load_dotenv

try:
    import winsound

    def beep(freq=800, dur=80):
        try:
            winsound.Beep(freq, dur)
        except Exception:
            pass
except ImportError:
    def beep(freq=800, dur=80):
        pass


ROOT = Path(__file__).parent
load_dotenv(ROOT / "config.env")

API_KEY = os.environ.get("SILICONFLOW_API_KEY", "").strip()
API_URL = "https://api.siliconflow.cn/v1/audio/transcriptions"
MODEL = os.environ.get("STT_MODEL", "FunAudioLLM/SenseVoiceSmall")
SAMPLE_RATE = 16000
CHANNELS = 1

# Hotkey config — 默认 Ctrl+Shift+Space（避开中文输入法占用 Ctrl+Space / Ctrl+Alt+Space）
HOT_KEYS = {keyboard.Key.ctrl_l, keyboard.Key.shift, keyboard.Key.space}
HOT_KEYS_LABEL = "Ctrl + Shift + Space"


# ────────── 状态机 ──────────
class State:
    IDLE = "idle"
    RECORDING = "rec"
    TRANSCRIBING = "stt"
    DONE = "done"
    ERROR = "err"


state = State.IDLE
audio_q: "queue.Queue[np.ndarray]" = queue.Queue()
audio_buf: list = []
record_lock = threading.Lock()
ui_q: "queue.Queue[dict]" = queue.Queue()  # GUI 更新通道
current_keys: set = set()
last_text = "（待机中）"
volume_level = 0.0  # 0.0-1.0


# ────────── 录音 ──────────
def audio_callback(indata, frames, time_info, status):
    global volume_level
    if state == State.RECORDING:
        audio_q.put(indata.copy())
    # 不论是否在录音都计算音量，便于"待机时也能看到麦工作"
    rms = float(np.sqrt(np.mean(indata.astype(np.float32) ** 2)))
    volume_level = min(1.0, rms * 12)  # 经验放大


def start_record():
    global state, audio_buf
    with record_lock:
        if state == State.RECORDING:
            return
        audio_buf = []
        while not audio_q.empty():
            try:
                audio_q.get_nowait()
            except queue.Empty:
                break
        state = State.RECORDING
    ui_q.put({"state": State.RECORDING, "t0": time.time()})
    beep(800, 60)


def stop_record_and_transcribe():
    global state
    with record_lock:
        if state != State.RECORDING:
            return
        state = State.TRANSCRIBING

    time.sleep(0.05)
    while not audio_q.empty():
        try:
            audio_buf.append(audio_q.get_nowait())
        except queue.Empty:
            break

    if not audio_buf:
        ui_q.put({"state": State.IDLE, "msg": "（没录到声音）"})
        with record_lock:
            globals()["state"] = State.IDLE
        return

    audio = np.concatenate(audio_buf, axis=0)
    duration = len(audio) / SAMPLE_RATE
    if duration < 0.3:
        ui_q.put({"state": State.IDLE, "msg": f"（太短 {duration:.2f}s · 忽略）"})
        with record_lock:
            globals()["state"] = State.IDLE
        return

    beep(600, 40)
    ui_q.put({"state": State.TRANSCRIBING, "duration": duration})

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        wav_path = tmp.name
    sf.write(wav_path, audio, SAMPLE_RATE)

    text, err = transcribe(wav_path)
    try:
        os.unlink(wav_path)
    except OSError:
        pass

    if err:
        ui_q.put({"state": State.ERROR, "msg": err})
        with record_lock:
            globals()["state"] = State.IDLE
        return

    if not text:
        ui_q.put({"state": State.IDLE, "msg": "（识别为空）"})
        with record_lock:
            globals()["state"] = State.IDLE
        return

    pyperclip.copy(text)
    paste_to_focus()
    beep(1000, 60)
    ui_q.put({"state": State.DONE, "text": text})
    with record_lock:
        globals()["state"] = State.IDLE


def transcribe(wav_path: str):
    """返回 (text, error_str)"""
    try:
        t0 = time.time()
        with open(wav_path, "rb") as f:
            r = requests.post(
                API_URL,
                headers={"Authorization": f"Bearer {API_KEY}"},
                files={"file": ("voice.wav", f, "audio/wav")},
                data={"model": MODEL},
                timeout=60,
            )
        if r.status_code != 200:
            return None, f"HTTP {r.status_code}: {r.text[:160]}"
        text = r.json().get("text", "").strip()
        text = clean_sensevoice_tokens(text)
        return text, None
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"


def clean_sensevoice_tokens(text: str) -> str:
    """SenseVoice 会输出 <|zh|><|HAPPY|> 之类的标记 + 末尾 emoji；去掉。"""
    text = re.sub(r"<\|[^|]*\|>", "", text)
    # 移除常见尾部 emoji/special chars
    text = text.strip()
    return text


def paste_to_focus():
    """模拟 Ctrl+V 粘贴。等 0.15s 让焦点稳定。"""
    time.sleep(0.15)
    kbd = keyboard.Controller()
    kbd.press(keyboard.Key.ctrl)
    kbd.press("v")
    kbd.release("v")
    kbd.release(keyboard.Key.ctrl)


# ────────── 热键 ──────────
def on_key_press(key):
    current_keys.add(key)
    # 兼容左右 shift / ctrl
    aliases = {
        keyboard.Key.ctrl: keyboard.Key.ctrl_l,
        keyboard.Key.ctrl_r: keyboard.Key.ctrl_l,
        keyboard.Key.shift_r: keyboard.Key.shift,
        keyboard.Key.shift_l: keyboard.Key.shift,
    }
    if key in aliases:
        current_keys.add(aliases[key])
    if HOT_KEYS.issubset(current_keys) and state == State.IDLE:
        threading.Thread(target=start_record, daemon=True).start()


def on_key_release(key):
    current_keys.discard(key)
    aliases = {
        keyboard.Key.ctrl: keyboard.Key.ctrl_l,
        keyboard.Key.ctrl_r: keyboard.Key.ctrl_l,
        keyboard.Key.shift_r: keyboard.Key.shift,
        keyboard.Key.shift_l: keyboard.Key.shift,
    }
    if key in aliases:
        current_keys.discard(aliases[key])
    if state == State.RECORDING and not HOT_KEYS.issubset(current_keys):
        threading.Thread(target=stop_record_and_transcribe, daemon=True).start()


# ────────── 自检 ──────────
def self_test() -> str:
    """启动时调一次 API，确认通路正常。返回状态字符串。"""
    if not API_KEY:
        return "❌ SILICONFLOW_API_KEY 未配置"
    try:
        sr = SAMPLE_RATE
        t = np.linspace(0, 0.5, int(sr * 0.5), endpoint=False)
        y = (0.2 * np.sin(2 * np.pi * 440 * t)).astype("float32")
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            wav_path = tmp.name
        sf.write(wav_path, y, sr)
        with open(wav_path, "rb") as f:
            r = requests.post(
                API_URL,
                headers={"Authorization": f"Bearer {API_KEY}"},
                files={"file": ("test.wav", f, "audio/wav")},
                data={"model": MODEL},
                timeout=20,
            )
        os.unlink(wav_path)
        if r.status_code == 200:
            return f"✅ API OK · 模型 {MODEL}"
        return f"❌ API HTTP {r.status_code}: {r.text[:120]}"
    except Exception as e:
        return f"❌ 自检异常: {e}"


# ────────── GUI ──────────
class FloatingPanel:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("Voice2CC")
        root.overrideredirect(True)
        root.attributes("-topmost", True)
        root.attributes("-alpha", 0.94)
        root.configure(bg="#1e1e2e")

        # 放右下角
        sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
        w, h = 460, 92
        root.geometry(f"{w}x{h}+{sw - w - 24}+{sh - h - 80}")

        bg = "#1e1e2e"
        fg = "#cdd6f4"
        accent = "#89b4fa"

        frm = tk.Frame(root, bg=bg, padx=12, pady=8)
        frm.pack(fill="both", expand=True)

        top = tk.Frame(frm, bg=bg)
        top.pack(fill="x")

        self.dot = tk.Canvas(top, width=14, height=14, bg=bg, highlightthickness=0)
        self.dot_circle = self.dot.create_oval(2, 2, 12, 12, fill="#6c7086", outline="")
        self.dot.pack(side="left", padx=(0, 8))

        self.status_lbl = tk.Label(
            top, text="待机", bg=bg, fg=fg, font=("Microsoft YaHei UI", 10, "bold")
        )
        self.status_lbl.pack(side="left")

        self.timer_lbl = tk.Label(top, text="", bg=bg, fg="#a6adc8", font=("Consolas", 9))
        self.timer_lbl.pack(side="left", padx=(10, 0))

        self.hotkey_lbl = tk.Label(
            top, text=HOT_KEYS_LABEL, bg=bg, fg="#7f849c", font=("Consolas", 9)
        )
        self.hotkey_lbl.pack(side="right")

        close_btn = tk.Label(
            top, text="×", bg=bg, fg="#f38ba8", font=("Arial", 14, "bold"), cursor="hand2"
        )
        close_btn.pack(side="right", padx=(8, 0))
        close_btn.bind("<Button-1>", lambda e: self.quit())

        # 音量条
        self.vol_canvas = tk.Canvas(frm, height=10, bg="#11111b", highlightthickness=0)
        self.vol_canvas.pack(fill="x", pady=(8, 6))
        self.vol_bar = self.vol_canvas.create_rectangle(0, 0, 0, 10, fill=accent, outline="")

        # 文字
        self.text_lbl = tk.Label(
            frm,
            text=last_text,
            bg=bg,
            fg=fg,
            font=("Microsoft YaHei UI", 9),
            anchor="w",
            wraplength=420,
            justify="left",
        )
        self.text_lbl.pack(fill="x")

        # 拖动
        for w in (frm, top, self.status_lbl, self.timer_lbl, self.text_lbl):
            w.bind("<Button-1>", self._drag_start)
            w.bind("<B1-Motion>", self._drag_move)

        self._drag_x = 0
        self._drag_y = 0
        self._t0 = None

        self.root.after(40, self._tick)

    def _drag_start(self, e):
        self._drag_x = e.x_root - self.root.winfo_x()
        self._drag_y = e.y_root - self.root.winfo_y()

    def _drag_move(self, e):
        self.root.geometry(f"+{e.x_root - self._drag_x}+{e.y_root - self._drag_y}")

    def _tick(self):
        # 更新音量条（始终显示，让用户看到麦工作）
        w = self.vol_canvas.winfo_width()
        bar_w = int(w * volume_level)
        color = "#f38ba8" if state == State.RECORDING else "#45475a"
        self.vol_canvas.itemconfig(self.vol_bar, fill=color)
        self.vol_canvas.coords(self.vol_bar, 0, 0, bar_w, 10)

        # 计时
        if state == State.RECORDING and self._t0:
            self.timer_lbl.config(text=f"{time.time() - self._t0:.1f}s")

        # 拉取消息
        try:
            while True:
                msg = ui_q.get_nowait()
                self._apply(msg)
        except queue.Empty:
            pass

        self.root.after(40, self._tick)

    def _apply(self, msg: dict):
        st = msg.get("state")
        if st == State.RECORDING:
            self.dot.itemconfig(self.dot_circle, fill="#f38ba8")
            self.status_lbl.config(text="● 录音中", fg="#f38ba8")
            self.text_lbl.config(text="（说话中…松开热键结束）")
            self._t0 = msg.get("t0", time.time())
        elif st == State.TRANSCRIBING:
            self.dot.itemconfig(self.dot_circle, fill="#f9e2af")
            self.status_lbl.config(text="◉ 转写中", fg="#f9e2af")
            self.timer_lbl.config(text=f"{msg.get('duration', 0):.1f}s ➜")
            self.text_lbl.config(text="正在调用 SiliconFlow Whisper…")
        elif st == State.DONE:
            self.dot.itemconfig(self.dot_circle, fill="#a6e3a1")
            self.status_lbl.config(text="✓ 已粘贴", fg="#a6e3a1")
            self.timer_lbl.config(text="")
            self.text_lbl.config(text=msg.get("text", ""))
        elif st == State.ERROR:
            self.dot.itemconfig(self.dot_circle, fill="#f38ba8")
            self.status_lbl.config(text="✗ 错误", fg="#f38ba8")
            self.timer_lbl.config(text="")
            self.text_lbl.config(text=msg.get("msg", "未知错误"))
        elif st == State.IDLE:
            self.dot.itemconfig(self.dot_circle, fill="#6c7086")
            self.status_lbl.config(text="待机", fg="#cdd6f4")
            self.timer_lbl.config(text="")
            if "msg" in msg:
                self.text_lbl.config(text=msg["msg"])

    def quit(self):
        self.root.quit()
        self.root.destroy()


# ────────── 主流程 ──────────
def main():
    print("=" * 56)
    print(" Voice2CC v2 启动")
    print(f" 模型: {MODEL}")
    print(f" 热键: 按住 {HOT_KEYS_LABEL}")
    print("=" * 56)

    print(" 自检中…")
    test_result = self_test()
    print(f" {test_result}")
    if test_result.startswith("❌"):
        print(" 自检失败，请修好 config.env / 网络后重启。")

    # 启动音频流
    try:
        stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            callback=audio_callback,
            dtype="float32",
        )
        stream.start()
        print(f" 麦克风: {sd.query_devices(kind='input')['name']}")
    except Exception as e:
        print(f" ❌ 麦克风启动失败: {e}")
        return

    # 启动热键监听器
    listener = keyboard.Listener(on_press=on_key_press, on_release=on_key_release)
    listener.daemon = True
    listener.start()
    print(" 热键监听 ✅")
    print(" 悬浮窗已显示（右下角，可拖动）")

    # GUI
    root = tk.Tk()
    panel = FloatingPanel(root)
    if test_result.startswith("❌"):
        ui_q.put({"state": State.ERROR, "msg": test_result})
    else:
        ui_q.put({"state": State.IDLE, "msg": test_result + " · 按住热键开始说话"})

    try:
        root.mainloop()
    finally:
        try:
            stream.stop()
            stream.close()
        except Exception:
            pass
        listener.stop()
        print("\n[bye]")


if __name__ == "__main__":
    main()

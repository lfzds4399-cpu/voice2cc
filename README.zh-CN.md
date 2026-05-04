# voice2cc

> Windows 上的语音输入工具。按住热键，说话，松开 — 转写好的文字自动粘贴到焦点输入框。

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Platform: Windows](https://img.shields.io/badge/platform-Windows-blue.svg)](#install)

> 🌏 [English README](./README.md)

```
[按住热键]   →   ● 录音中   （计时器 + 实时音量条 + pre-roll 防丢首字）
[松开]       →   ◉ 转写中
                 →   ✓ 已粘贴   （Ctrl+V，已处理 modifier 残留 bug）
```

## 为什么做这个

在 Claude Code / Cursor / 任何聊天 UI 里写长 prompt 是手指马拉松。Whisper 级别的 STT 现在快到 **按住一个键说话比打字还快**了 — 但市面上工具要么塞太多功能，要么订阅 $30/月。我只要**一个键、一次粘贴、UI 不挡路**，所以做了这个。

## v0.3 更新（与 v0.2 对比）

v0.1/v0.2 是单文件 proof-of-concept，证明思路可行。v0.3 做到真正能用：

| v0.2 痛点 | v0.3 修复 |
|---|---|
| 松开 Ctrl+Shift+Space 后粘贴有时打开 VS Code 命令面板 | `paste_to_focus` 先 release 所有 modifier，等 200ms 再发 Ctrl+V |
| 每次录音第一个字被吃 | 待机时持续灌入 300ms 环形 pre-roll buffer，热键按下时 prepend 到录音 |
| 只支持 SiliconFlow | 4 个 provider：SiliconFlow / OpenAI / Groq / Azure（全是 OpenAI 兼容 HTTP） |
| 改 key 要 Notepad 编辑 config.env | 首次运行向导 + 设置对话框（provider、麦、热键、语言） |
| 没托盘 — 关掉悬浮窗就找不回来 | pystray 托盘菜单：显示/隐藏/设置/诊断/退出 |
| 只有英文 UI | 中英文双语，跟随系统 |
| 出错没法 debug | 内置诊断 + 滚动日志 `voice2cc.log` |
| 必须装 Python | PyInstaller spec 一键打包 `.exe` |

## 安装

### 给开发者

需要 Python 3.10+。

```bash
git clone https://github.com/lfzds4399-cpu/voice2cc.git
cd voice2cc
pip install -r requirements.txt
python app.py
```

第一次运行会弹设置向导。选 provider、粘贴 API key、点 Test、点 Save。

或者双击 `install.bat` 装依赖，然后 `start.bat` 启动。

### 给普通用户（不装 Python）

我们暂时不发布签名后的 `.exe`（代码签名证书 ≈$300/年）。自己 build：

```bash
pip install pyinstaller
build_tools\build.bat
# 出 dist\voice2cc\voice2cc.exe
```

把 `dist\voice2cc\` 整个文件夹打包成 zip 分发。

## Provider 选哪个

| Provider | 推荐模型 | 适合 |
|---|---|---|
| **SiliconFlow** | `FunAudioLLM/SenseVoiceSmall` | 免费、中文最好、国内可用 |
| **OpenAI** | `whisper-1` / `gpt-4o-mini-transcribe` | 国际、付费、英文强 |
| **Groq** | `whisper-large-v3-turbo` | 最快（~1s 往返）、免费额度大方 |
| **Azure** | `whisper` 部署 | 企业 / 数据合规要求 |

向导里 4 个都列出来，随时可以在设置里改。

## 热键

默认：**Ctrl + Shift + Space**

如果你的输入法（中/日/韩）抢这个组合，去 **设置 → 热键** 改，或选 preset：

- `ctrl+alt+v`
- `ctrl+\``
- `f8` / `f9`
- `right ctrl`

## 工作原理

```
麦克风 ──[InputStream]──┐
                        ├── 待机时持续灌入 300ms pre-roll 环形 buffer
热键 ──[pynput]─────────┘
   │                          ┌── prepend pre-roll
   ↓ 按下                     ↓
RECORDING → audio 队列 → wav 文件
   ↓ 松开
TRANSCRIBING → provider (SiliconFlow / OpenAI / Groq / Azure)
   ↓
release modifiers → 等 200ms → Ctrl+V
   ↓
DONE / ERROR（错误进 voice2cc.log）
```

pre-roll buffer 解决"按住热键瞬间说话第一个字总丢"的高频问题。
modifier-release-then-wait 解决"粘贴变成 Ctrl+Shift+V"的高频问题（VS Code / Cursor / 浏览器都中招过）。

## 项目结构

```
voice2cc/
├── app.py                       # 入口 shim
├── start.bat / install.bat
├── requirements.txt
├── pytest.ini
├── config.env (gitignored)      # 你的本地配置
├── .env.example                 # 模板
├── src/voice2cc/
│   ├── main.py                  # 编排器
│   ├── config.py                # Settings + 读/写
│   ├── i18n.py                  # 中英文字符串表
│   ├── audio.py                 # 麦克风 + pre-roll
│   ├── hotkey.py                # 全局热键
│   ├── paste.py                 # modifier-safe Ctrl+V
│   ├── diagnostics.py           # 启动自检
│   ├── autostart.py             # Windows 注册表 HKCU\Run
│   ├── providers/               # STT 服务商
│   └── ui/                      # 悬浮窗、托盘、向导、设置对话框
├── tests/                       # 38 个单元测试，不需要 GUI / 网络
└── build_tools/                 # PyInstaller spec + build.bat
```

## 排错

| 现象 | 解决 |
|---|---|
| 热键没反应 | 输入法抢了 Ctrl+Shift+Space — 在设置里换 |
| 悬浮窗看不到 | 右键托盘图标 → 显示悬浮窗 |
| 红点亮但音量条不动 | Windows 设置 → 隐私 → 麦克风 → 允许桌面应用 |
| 识别错字多 | 设置里换模型（Groq 的 whisper-large-v3 英文最强） |
| `pip install sounddevice` 卡死 | `pip install sounddevice --no-binary :all:` 或换镜像 |
| 没粘贴成功 | 录音期间别切焦点；检查目标 app 是不是禁了 Ctrl+V |
| 麦被占用 | 另一个 app 占用麦（Zoom / Discord / 钉钉）— 关掉它 |
| 没托盘图标 | pystray 没装上 — voice2cc 还能跑，只是没托盘菜单 |
| SiliconFlow 超时 | 你不在国内 — 设置里换 provider |

诊断（托盘 → 诊断…）一次跑完所有检查。

## 隐私

音频会发到你配置的 STT provider。**本地不存任何录音**，只有滚动日志 `voice2cc.log`（总共 ~1.5MB）。无遥测、无自动更新、无统计。代码 < 2k 行，自己读一遍。

## 开发

```bash
git clone https://github.com/lfzds4399-cpu/voice2cc.git
cd voice2cc
pip install -r requirements.txt pytest
python -m pytest tests/ -q
```

欢迎 PR。详 [CONTRIBUTING.md](./CONTRIBUTING.md)。安全问题 [SECURITY.md](./SECURITY.md)。

## License

MIT — 见 [LICENSE](./LICENSE)。

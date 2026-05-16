# voice2ai

Windows 按住说话工具。按住热键讲话，松开后把转写结果粘到当前焦点窗口。我自己拿它往 VS Code、Cursor、Claude Code 和微信里塞文字。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Platform: Windows](https://img.shields.io/badge/platform-Windows-blue.svg)](#install)

[English README](./README.md)

目前只支持 Windows，粘贴后端直接调 Win32 键盘接口。provider、配置、音频、VAD 这些代码本身和平台无关，但 macOS 和 Linux 的粘贴后端还没人写。

## Install

需要 Python 3.10 或更新版本。

```powershell
git clone https://github.com/lfzds4399-cpu/voice2ai.git
cd voice2ai
python -m pip install -r requirements.txt
python app.py
```

首次运行会弹设置向导。选 provider、贴 API key、点测试、保存。也可以直接双击 `install.bat` 再 `start.bat`。

## 热键和模式

默认热键 `ctrl+shift+space`。其他预设有 `f8`、`f9`、`right ctrl`、`ctrl+alt+v`。按 `f9` 进连续模式，EnergyVAD 等到停顿再把刚才那段话转写出来。

开始录音的瞬间会记住当前前台窗口句柄。转写回来后先恢复那个窗口再发粘贴，所以中途切了标签页文字也不会塞错地方。已知终端和编辑器走 `ctrl+shift+v`，其他窗口走 `ctrl+v`。

## Provider

| Provider | 我自己用的模型 | 备注 |
|---|---|---|
| SiliconFlow | `FunAudioLLM/SenseVoiceSmall` | 中文还行，国内能直连。 |
| OpenAI | `whisper-1` 或 `gpt-4o-mini-transcribe` | 全球付费 API。 |
| Groq | `whisper-large-v3-turbo` | Whisper 兼容接口，延迟低。 |
| Azure | `whisper` deployment | 需要 Azure OpenAI resource。 |

`config.env` 同时认规范字段和 `.env.example` 里的 provider 别名，例如 `GROQ_MODEL`、`OPENAI_MODEL`、`SILICONFLOW_MODEL`、`AZURE_SPEECH_KEY`、`AZURE_SPEECH_REGION`。

## 粘贴这块花了最久

voice2ai 不逐字模拟输入。它先把转写写进剪贴板，释放残留 modifier，等几毫秒，尽量恢复目标窗口，再发粘贴快捷键。

原因挺蠢但是真的：按 `ctrl+shift+space` 讲完话松开热键时，`shift` 可能还物理按着，Windows 这时把 `ctrl+v` 当成 `ctrl+shift+v`，终端就把粘贴吃掉了。modifier 释放这段逻辑在 `tests/test_paste.py` 里有覆盖。

## 开发

```powershell
python -m pip install -r requirements.txt
python -m pip install pytest ruff
python -m pytest tests/ -q
python -m ruff check src tests app.py
```

测试默认离线跑，不调 provider API，不驱动真键盘，也不做 GUI 自动化。

## 隐私

音频只发给你自己配的那个 STT provider。没有遥测、统计、自动更新或者监听端口。API key 写在本地 `config.env`，已经 gitignore。安全问题走 [SECURITY.md](./SECURITY.md)。

## License

MIT，详见 [LICENSE](./LICENSE)。

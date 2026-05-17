# voice2ai

Windows 按住说话听写工具。按住热键讲话，松开后把转写结果粘到焦点窗口。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Platform: Windows](https://img.shields.io/badge/platform-Windows-blue.svg)](#install)

[English README](./README.md)

仅支持 Windows，粘贴后端直接调用 Win32 键盘接口。provider、配置、音频、VAD 层与平台无关；macOS 和 Linux 粘贴后端未实现。

## Install

需要 Python 3.10 或更新版本。

```powershell
git clone https://github.com/lfzds4399-cpu/voice2ai.git
cd voice2ai
python -m pip install -r requirements.txt
python app.py
```

首次运行打开设置向导：选 provider、贴 API key、测试、保存。也可双击 `install.bat` 再 `start.bat`。

## 热键和模式

默认热键 `ctrl+shift+space`。内置预设 `f8`、`f9`、`right ctrl`、`ctrl+alt+v`。按 `f9` 进入连续模式，由 EnergyVAD 检测停顿并对前一段语音进行转写。

按下热键时记录前台窗口句柄。转写返回后先恢复该窗口再发送粘贴指令，避免录音中途切换焦点导致文字落到错误的应用。已知终端和编辑器使用 `ctrl+shift+v`，其他窗口使用 `ctrl+v`。

## Provider

| Provider | 模型 | 备注 |
|---|---|---|
| SiliconFlow | `FunAudioLLM/SenseVoiceSmall` | 支持中文，国内可直连。 |
| OpenAI | `whisper-1`、`gpt-4o-mini-transcribe` | 全球付费 API。 |
| Groq | `whisper-large-v3-turbo` | Whisper 兼容接口，延迟低。 |
| Azure | `whisper` deployment | 需要 Azure OpenAI resource。 |

`config.env` 同时识别规范字段和 `.env.example` 中的 provider 别名，例如 `GROQ_MODEL`、`OPENAI_MODEL`、`SILICONFLOW_MODEL`、`AZURE_SPEECH_KEY`、`AZURE_SPEECH_REGION`。

## Modifier 处理

voice2ai 不模拟逐字键入。流程为：将转写写入剪贴板，释放残留 modifier 键，等待数毫秒，尽量恢复目标窗口，再发送粘贴快捷键。

若 `shift` 在粘贴触发时仍被物理按住，Windows 会把 `ctrl+v` 解析为 `ctrl+shift+v`，部分终端会拦截并丢弃该粘贴。modifier 释放路径由 `tests/test_paste.py` 覆盖。

## 开发

```powershell
python -m pip install -r requirements.txt
python -m pip install pytest ruff
python -m pytest tests/ -q
python -m ruff check src tests app.py
```

测试离线运行，不调用 provider API，不驱动真实键盘，不做 GUI 自动化。

## 隐私

音频仅发送至所配置的 STT provider。无遥测、统计、自动更新或监听端口。API key 存于本地 `config.env`，已 gitignore。安全问题：[SECURITY.md](./SECURITY.md)。

## License

MIT，详见 [LICENSE](./LICENSE)。

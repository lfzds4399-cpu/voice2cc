# Voice2CC v2 · 语音输入到 Claude Code

按住热键说话 → 松开自动转写并粘贴到当前焦点。带**悬浮窗 + 实时音量条 + 启动自检 + 提示音**反馈。

## 用法

| 步骤 | 命令 |
|---|---|
| 装一次 | 双击 `install.bat` |
| 启动 | 双击 `start.bat`（保持窗口开着） |
| 录音 | 焦点放在 CC 输入框 → 按住 **Ctrl + Shift + 空格** → 说 → 松开 |
| 退出 | 点悬浮窗右上角 × |

## 视觉反馈

启动后右下角出现一个悬浮窗，可拖动到任意位置。状态：

| 颜色 | 含义 |
|---|---|
| ⚪ 灰 待机 | 按热键开录 |
| 🔴 红 录音中 + 计时 + 红色音量条跳动 | 说话中 |
| 🟡 黄 转写中 + 录音长度 | 上传 SiliconFlow 中 |
| 🟢 绿 ✓ 已粘贴 + 显示原文 | 完成（同时播 1000Hz 提示音） |
| 🔴 ✗ 错误 + 详细错误 | 出错 |

音量条**待机时也实时显示麦克风音量**——你能立刻看到麦是不是工作。

## 现状

- STT 引擎：SiliconFlow `FunAudioLLM/SenseVoiceSmall`（OpenAI 兼容 API）
- 录音：16kHz mono · 在线转写 · 通常 1-3 秒返回
- 粘贴：自动 `Ctrl+V` 到当前焦点
- 太短（<0.3s）自动忽略，避免误触

## 调参

改 `config.env`：
- `STT_MODEL` — 备选 `iic/SenseVoiceSmall`、`openai-whisper-large-v3`
- `SILICONFLOW_API_KEY` — 你的 key

## 改热键

`voice2cc.py` 顶部的 `HOT_KEYS` 集合，例如换成右 Ctrl + Shift + Space：

```python
HOT_KEYS = {keyboard.Key.ctrl_r, keyboard.Key.shift, keyboard.Key.space}
```

## 提示音

- 开始录音：800Hz 短嗡（"开始")
- 结束录音：600Hz 短嗡（"开始转写"）
- 粘贴成功：1000Hz 短嗡（"完成"）

## 启动自检

每次 start.bat 启动会自动调一次 SiliconFlow API 验证 key + 模型 + 网络：
- ✅ API OK · 模型 ... — 通路正常
- ❌ HTTP xxx — 拷贝错误信息发给我

## 故障排查

| 现象 | 解法 |
|---|---|
| 热键无反应 | 大概率是中文输入法占用 — 默认已避开 Ctrl+Space / Ctrl+Alt+Space；如还冲突，改 voice2cc.py 顶部 `HOT_KEYS` 集合 |
| 看不到悬浮窗 | 可能在屏幕外 — 关掉 start.bat 重启 |
| 录音红色指示亮但音量条不动 | 麦克风权限：Windows 设置 → 隐私 → 麦克风 → 允许桌面应用访问 |
| 转写说出来不准 | SenseVoiceSmall 对中文不错，对技术英文略弱 — 改 `STT_MODEL` 为其他模型试试（注意 SF 上 openai/whisper-1 不存在） |
| `pip install` 卡 sounddevice | 装 PortAudio：`pip install sounddevice --no-binary :all:` 或换 pip 镜像 |
| 粘贴没出现 | 焦点跑了 — 录完前别切窗口；或检查目标软件是否拦截 Ctrl+V |
| 启动报 sd error | 麦被独占了 — 关掉占用麦的程序（钉钉/腾讯会议/Discord）再启 |

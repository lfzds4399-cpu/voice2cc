"""i18n.py — lightweight string table.

Auto-detects from settings.language (auto → system locale → fallback en).

Usage:
    from voice2ai.i18n import t, set_language
    set_language("auto")  # or "zh" / "en"
    print(t("status.idle"))
"""
from __future__ import annotations

import locale
import logging

logger = logging.getLogger("voice2ai.i18n")

_STRINGS = {
    "en": {
        # status bar / floating widget
        "status.idle": "idle",
        "status.recording": "● recording",
        "status.transcribing": "◉ transcribing",
        "status.pasted": "✓ pasted",
        "status.copied": "✓ copied",
        "status.error": "✗ error",
        "status.ready": "ready · hold {hotkey} to talk",
        "status.recording_hint": "(speaking… release {hotkey} to stop)",
        "status.calling_api": "calling {provider}…",
        "status.too_short": "(too short, ignored)",
        "status.empty_result": "(empty result)",
        "status.no_audio": "(no audio captured)",

        # tray
        "tray.show": "Show widget",
        "tray.hide": "Hide widget",
        "tray.settings": "Settings…",
        "tray.diagnose": "Diagnose…",
        "tray.open_log": "Open log file",
        "tray.about": "About voice2ai",
        "tray.quit": "Quit",

        # diagnostics
        "diag.api_ok": "API OK · model {model}",
        "diag.api_no_key": "API key not configured",
        "diag.api_http": "API HTTP {status}: {body}",
        "diag.api_exception": "API exception: {err}",
        "diag.mic_ok": "Microphone OK · {name}",
        "diag.mic_fail": "Microphone failed: {err}",
        "diag.network_ok": "Network OK · {ms}ms",
        "diag.network_fail": "Network failed: {err}",
        "diag.hotkey_ok": "Hotkey listener OK",
        "diag.hotkey_fail": "Hotkey listener failed: {err}",
        "diag.dependency_ok": "All dependencies installed",
        "diag.dependency_missing": "Missing dependency: {name} (pip install {name})",

        # wizard
        "wizard.title": "voice2ai · first-run setup",
        "wizard.welcome": "Welcome. Pick your STT provider and paste your API key.",
        "wizard.provider": "Provider:",
        "wizard.provider_hint_siliconflow": "Free Mandarin model · Chinese mainland",
        "wizard.provider_hint_openai": "Whisper · global · paid",
        "wizard.provider_hint_groq": "Whisper-Large-v3 · fast · free tier",
        "wizard.provider_hint_azure": "Azure Speech · enterprise",
        "wizard.api_key": "API key:",
        "wizard.model": "Model:",
        "wizard.test_button": "Test connection",
        "wizard.save_button": "Save and start",
        "wizard.cancel_button": "Cancel",
        "wizard.testing": "Testing…",

        # settings
        "settings.title": "voice2ai · Settings",
        "settings.tab_provider": "Provider",
        "settings.tab_audio": "Audio",
        "settings.tab_hotkey": "Hotkey",
        "settings.tab_general": "General",
        "settings.input_device": "Input device:",
        "settings.test_record": "Test record (3s)",
        "settings.hotkey_record": "Press the new hotkey…",
        "settings.hotkey_current": "Current: {hotkey}",
        "settings.autostart": "Start with Windows",
        "settings.language": "Language:",
        "settings.language_auto": "Auto-detect",
        "settings.show_widget": "Show floating widget",
        "settings.play_cues": "Play audio cues",
        "settings.paste_mode": "Paste after transcribe (otherwise copy only)",
        "settings.save": "Save",
        "settings.cancel": "Cancel",

        # generic
        "btn.ok": "OK",
        "btn.cancel": "Cancel",
        "btn.close": "Close",
        "btn.retry": "Retry",
    },
    "zh": {
        "status.idle": "待机",
        "status.recording": "● 录音中",
        "status.transcribing": "◉ 转写中",
        "status.pasted": "✓ 已粘贴",
        "status.copied": "✓ 已复制",
        "status.error": "✗ 错误",
        "status.ready": "就绪 · 按住 {hotkey} 说话",
        "status.recording_hint": "（说话中…松开 {hotkey} 结束）",
        "status.calling_api": "调用 {provider} 中…",
        "status.too_short": "（太短 · 忽略）",
        "status.empty_result": "（识别为空）",
        "status.no_audio": "（没录到声音）",

        "tray.show": "显示悬浮窗",
        "tray.hide": "隐藏悬浮窗",
        "tray.settings": "设置…",
        "tray.diagnose": "诊断…",
        "tray.open_log": "打开日志文件",
        "tray.about": "关于 voice2ai",
        "tray.quit": "退出",

        "diag.api_ok": "API 通 · 模型 {model}",
        "diag.api_no_key": "API key 未配置",
        "diag.api_http": "API HTTP {status}: {body}",
        "diag.api_exception": "API 异常：{err}",
        "diag.mic_ok": "麦克风通 · {name}",
        "diag.mic_fail": "麦克风启动失败：{err}",
        "diag.network_ok": "网络通 · {ms}ms",
        "diag.network_fail": "网络不通：{err}",
        "diag.hotkey_ok": "热键监听 OK",
        "diag.hotkey_fail": "热键监听失败：{err}",
        "diag.dependency_ok": "依赖完整",
        "diag.dependency_missing": "缺依赖：{name}（pip install {name}）",

        "wizard.title": "voice2ai · 首次设置",
        "wizard.welcome": "欢迎使用。选 STT 服务商，填 API key。",
        "wizard.provider": "服务商：",
        "wizard.provider_hint_siliconflow": "免费中文模型 · 国内可用",
        "wizard.provider_hint_openai": "Whisper · 国际 · 付费",
        "wizard.provider_hint_groq": "Whisper-Large-v3 · 极快 · 有免费额度",
        "wizard.provider_hint_azure": "Azure 语音 · 企业级",
        "wizard.api_key": "API key：",
        "wizard.model": "模型：",
        "wizard.test_button": "测试连接",
        "wizard.save_button": "保存并启动",
        "wizard.cancel_button": "取消",
        "wizard.testing": "测试中…",

        "settings.title": "voice2ai · 设置",
        "settings.tab_provider": "服务商",
        "settings.tab_audio": "音频",
        "settings.tab_hotkey": "热键",
        "settings.tab_general": "通用",
        "settings.input_device": "输入设备：",
        "settings.test_record": "试录 3 秒",
        "settings.hotkey_record": "按下新热键…",
        "settings.hotkey_current": "当前：{hotkey}",
        "settings.autostart": "开机自启",
        "settings.language": "语言：",
        "settings.language_auto": "跟随系统",
        "settings.show_widget": "显示悬浮窗",
        "settings.play_cues": "播放提示音",
        "settings.paste_mode": "转写后自动粘贴（否则仅复制）",
        "settings.save": "保存",
        "settings.cancel": "取消",

        "btn.ok": "确定",
        "btn.cancel": "取消",
        "btn.close": "关闭",
        "btn.retry": "重试",
    },
}


_current_lang = "en"


def detect_system_language() -> str:
    """Return 'zh' if system locale starts with zh / cmn, else 'en'."""
    loc = ""
    # Prefer modern API; fall back to deprecated getdefaultlocale on older Pythons
    try:
        loc = locale.getlocale()[0] or ""
    except Exception:
        pass
    if not loc:
        try:
            loc = locale.getdefaultlocale()[0] or ""
        except Exception:
            loc = ""
    if not loc:
        import os
        loc = os.environ.get("LANG", "")
    loc = loc.lower()
    if loc.startswith(("zh", "cmn")):
        return "zh"
    return "en"


def set_language(lang: str) -> None:
    global _current_lang
    if lang == "auto":
        _current_lang = detect_system_language()
    elif lang in _STRINGS:
        _current_lang = lang
    else:
        logger.warning("unknown language %r, falling back to en", lang)
        _current_lang = "en"
    logger.info("language set to %s", _current_lang)


def current_language() -> str:
    return _current_lang


def t(key: str, **kwargs) -> str:
    """Translate a key to the current language. Falls back to en, then to the key itself."""
    table = _STRINGS.get(_current_lang) or _STRINGS["en"]
    s = table.get(key) or _STRINGS["en"].get(key) or key
    if kwargs:
        try:
            return s.format(**kwargs)
        except (KeyError, IndexError):
            return s
    return s

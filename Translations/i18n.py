import json
import logging
import os
from typing import Any, Dict, Optional

from PyQt5.QtCore import QObject, pyqtSignal

logger = logging.getLogger("I18n")

SUPPORTED_LANGUAGES = {
    "en_US": "English",
    "zh_CN": "简体中文",
    "ja_JP": "日本語",
}

DEFAULT_LANGUAGE = "en_US"

_LANGUAGE_ALIASES = {
    "en": "en_US",
    "en_us": "en_US",
    "en-us": "en_US",
    "english": "en_US",
    "zh": "zh_CN",
    "zh_cn": "zh_CN",
    "zh-cn": "zh_CN",
    "cn": "zh_CN",
    "ja": "ja_JP",
    "ja_jp": "ja_JP",
    "ja-jp": "ja_JP",
    "jp": "ja_JP",
}


def normalize_language_code(language: Optional[str]) -> str:
    if not language:
        return DEFAULT_LANGUAGE
    normalized = str(language).strip()
    if normalized in SUPPORTED_LANGUAGES:
        return normalized

    key = normalized.lower()
    mapped = _LANGUAGE_ALIASES.get(key)
    if mapped:
        return mapped
    return DEFAULT_LANGUAGE


class I18nManager(QObject):
    languageChanged = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._locales: Dict[str, Dict[str, Any]] = {}
        self._language = DEFAULT_LANGUAGE
        self._load_locales()

    @property
    def language(self) -> str:
        return self._language

    def set_language(self, language: Optional[str]) -> str:
        normalized = normalize_language_code(language)
        if normalized == self._language:
            return self._language
        self._language = normalized
        self.languageChanged.emit(self._language)
        return self._language

    def translate(self, key: str, default: Optional[str] = None, **kwargs: Any) -> str:
        text = self._lookup(self._locales.get(self._language, {}), key)
        if text is None and self._language != DEFAULT_LANGUAGE:
            text = self._lookup(self._locales.get(DEFAULT_LANGUAGE, {}), key)
        if text is None:
            text = default if default is not None else key

        if kwargs:
            try:
                return str(text).format(**kwargs)
            except Exception:
                return str(text)
        return str(text)

    def _load_locales(self) -> None:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        locales_dir = os.path.join(base_dir, "locales")
        for lang_code in SUPPORTED_LANGUAGES.keys():
            file_path = os.path.join(locales_dir, f"{lang_code}.json")
            if not os.path.exists(file_path):
                self._locales[lang_code] = {}
                logger.warning("Locale file not found: %s", file_path)
                continue

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    self._locales[lang_code] = json.load(f)
            except Exception as e:
                logger.error("Failed to load locale file %s: %s", file_path, e)
                self._locales[lang_code] = {}

    @staticmethod
    def _lookup(messages: Dict[str, Any], key: str) -> Optional[str]:
        if not key:
            return None

        if key in messages and isinstance(messages[key], (str, int, float)):
            return str(messages[key])

        current: Any = messages
        for part in key.split("."):
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None

        if isinstance(current, (str, int, float)):
            return str(current)
        return None


_instance: Optional[I18nManager] = None


def get_i18n() -> I18nManager:
    global _instance
    if _instance is None:
        _instance = I18nManager()
    return _instance


def tr(key: str, default: Optional[str] = None, **kwargs: Any) -> str:
    return get_i18n().translate(key, default=default, **kwargs)


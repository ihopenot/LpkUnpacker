from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout
from qfluentwidgets import CardWidget, SubtitleLabel, BodyLabel, CaptionLabel, ComboBox, InfoBar, InfoBarPosition

from Core.settings_manager import SettingsManager
from Translations import get_i18n, normalize_language_code, tr


class SettingsPage(QFrame):
    """Application settings page."""

    languageChanged = pyqtSignal(str)
    themeChanged = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("settingsPage")

        self.settings_manager = SettingsManager()
        self.i18n = get_i18n()

        self._language_codes = ["en_US", "zh_CN", "ja_JP"]
        self._theme_values = ["auto", "light", "dark"]
        self._syncing_ui = False

        self.title_label = None
        self.language_section_title = None
        self.language_label = None
        self.language_desc = None
        self.language_combo = None
        self.language_note = None

        self.theme_section_title = None
        self.theme_label = None
        self.theme_desc = None
        self.theme_combo = None

        self.setup_ui()
        self.retranslate_ui()
        self.load_current_settings()
        self.i18n.languageChanged.connect(self.retranslate_ui)

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(16)

        self.title_label = SubtitleLabel("", self)
        main_layout.addWidget(self.title_label)

        language_card = CardWidget(self)
        language_layout = QVBoxLayout(language_card)
        language_layout.setContentsMargins(16, 16, 16, 16)
        language_layout.setSpacing(10)

        self.language_section_title = SubtitleLabel("", language_card)
        language_layout.addWidget(self.language_section_title)

        language_row = QHBoxLayout()
        language_row.setSpacing(12)

        language_text_layout = QVBoxLayout()
        language_text_layout.setSpacing(4)
        self.language_label = BodyLabel("", language_card)
        self.language_desc = CaptionLabel("", language_card)
        self.language_desc.setWordWrap(True)
        language_text_layout.addWidget(self.language_label)
        language_text_layout.addWidget(self.language_desc)

        self.language_combo = ComboBox(language_card)
        self.language_combo.setMinimumWidth(180)
        self.language_combo.currentIndexChanged.connect(self.on_language_combo_changed)

        language_row.addLayout(language_text_layout, 1)
        language_row.addWidget(self.language_combo, 0, Qt.AlignRight)
        language_layout.addLayout(language_row)

        self.language_note = CaptionLabel("", language_card)
        self.language_note.setWordWrap(True)
        language_layout.addWidget(self.language_note)

        main_layout.addWidget(language_card)

        theme_card = CardWidget(self)
        theme_layout = QVBoxLayout(theme_card)
        theme_layout.setContentsMargins(16, 16, 16, 16)
        theme_layout.setSpacing(10)

        self.theme_section_title = SubtitleLabel("", theme_card)
        theme_layout.addWidget(self.theme_section_title)

        theme_row = QHBoxLayout()
        theme_row.setSpacing(12)

        theme_text_layout = QVBoxLayout()
        theme_text_layout.setSpacing(4)
        self.theme_label = BodyLabel("", theme_card)
        self.theme_desc = CaptionLabel("", theme_card)
        self.theme_desc.setWordWrap(True)
        theme_text_layout.addWidget(self.theme_label)
        theme_text_layout.addWidget(self.theme_desc)

        self.theme_combo = ComboBox(theme_card)
        self.theme_combo.setMinimumWidth(180)
        self.theme_combo.currentIndexChanged.connect(self.on_theme_combo_changed)

        theme_row.addLayout(theme_text_layout, 1)
        theme_row.addWidget(self.theme_combo, 0, Qt.AlignRight)
        theme_layout.addLayout(theme_row)

        main_layout.addWidget(theme_card)
        main_layout.addStretch(1)

    def load_current_settings(self):
        self._syncing_ui = True
        try:
            language = normalize_language_code(self.settings_manager.get("language", "en_US"))
            self._set_combo_by_value(self.language_combo, self._language_codes, language)

            theme = str(self.settings_manager.get("theme", "auto")).lower()
            if theme not in self._theme_values:
                theme = "auto"
            self._set_combo_by_value(self.theme_combo, self._theme_values, theme)
        finally:
            self._syncing_ui = False

    def retranslate_ui(self):
        self._syncing_ui = True
        try:
            self.title_label.setText(tr("settings.title"))

            self.language_section_title.setText(tr("settings.section.language"))
            self.language_label.setText(tr("settings.language_label"))
            self.language_desc.setText(tr("settings.language_desc"))
            self.language_note.setText(tr("settings.language_note"))

            current_language = self._current_combo_value(self.language_combo, self._language_codes)
            self.language_combo.clear()
            for code in self._language_codes:
                if code == "en_US":
                    label = tr("settings.language.english")
                elif code == "zh_CN":
                    label = tr("settings.language.chinese")
                else:
                    label = tr("settings.language.japanese")
                self.language_combo.addItem(label)
            self._set_combo_by_value(self.language_combo, self._language_codes, current_language)

            self.theme_section_title.setText(tr("settings.section.appearance"))
            self.theme_label.setText(tr("settings.theme_label"))
            self.theme_desc.setText(tr("settings.theme_desc"))

            current_theme = self._current_combo_value(self.theme_combo, self._theme_values)
            self.theme_combo.clear()
            for theme in self._theme_values:
                if theme == "auto":
                    label = tr("settings.theme.auto")
                elif theme == "light":
                    label = tr("settings.theme.light")
                else:
                    label = tr("settings.theme.dark")
                self.theme_combo.addItem(label)
            self._set_combo_by_value(self.theme_combo, self._theme_values, current_theme)
        finally:
            self._syncing_ui = False

    def on_language_combo_changed(self, index: int):
        if self._syncing_ui:
            return
        if index < 0 or index >= len(self._language_codes):
            return

        language = self._language_codes[index]
        self.settings_manager.set("language", language)
        self.i18n.set_language(language)
        self.languageChanged.emit(language)

        InfoBar.success(
            title=tr("common.success"),
            content=tr("settings.language_saved"),
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2500,
            parent=self
        )

    def on_theme_combo_changed(self, index: int):
        if self._syncing_ui:
            return
        if index < 0 or index >= len(self._theme_values):
            return

        theme = self._theme_values[index]
        self.settings_manager.set("theme", theme)
        self.themeChanged.emit(theme)

        InfoBar.success(
            title=tr("common.success"),
            content=tr("settings.theme_saved"),
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2500,
            parent=self
        )

    @staticmethod
    def _set_combo_by_value(combo: ComboBox, values: list, value: str):
        if value in values:
            combo.setCurrentIndex(values.index(value))
        elif values:
            combo.setCurrentIndex(0)

    @staticmethod
    def _current_combo_value(combo: ComboBox, values: list):
        index = combo.currentIndex()
        if 0 <= index < len(values):
            return values[index]
        return values[0] if values else ""

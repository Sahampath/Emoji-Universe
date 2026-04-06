import sys
import json
import os
import random
import re
from collections import defaultdict
from functools import partial

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QScrollArea, QListView, QAbstractItemView,
    QLabel, QSplitter, QFrame, QStyledItemDelegate, QGraphicsOpacityEffect,
    QStyle, QToolTip, QShortcut, QSystemTrayIcon, QMenu, QAction
)
from PyQt5.QtCore import (
    Qt, QTimer, QAbstractListModel, QModelIndex, QSize, QRect,
    QPropertyAnimation, QEasingCurve, QPoint
)
from PyQt5.QtGui import (
    QFont, QPainter, QBrush, QColor, QPen, QLinearGradient,
    QPalette, QIcon, QPixmap, QPainterPath, QCursor, QKeySequence
)

if sys.platform == "win32":
    import ctypes
    from ctypes import wintypes

    WM_SETICON = 0x0080
    ICON_SMALL = 0
    ICON_BIG = 1
    GCL_HICON = -14
    GCL_HICONSM = -34

    user32 = ctypes.windll.user32


def generate_emojis_json():
    try:
        import emoji
        data = []
        for emj, info in emoji.EMOJI_DATA.items():
            data.append({"emoji": emj, "name": info.get("en", "").lower()})
        with open("emojis.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True, len(data)
    except ImportError:
        return False, "emoji library not installed. Run: pip install emoji"
    except Exception as e:
        return False, str(e)

def load_emoji_data():
    if not os.path.exists("emojis.json"):
        success, result = generate_emojis_json()
        if not success:
            return None, f"Could not generate emojis.json: {result}"
    try:
        with open("emojis.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data, None
            return None, "Invalid format"
    except Exception as e:
        return None, str(e)

def guess_category_from_name(name: str) -> str:
    name_clean = name.strip(':').lower().replace('_', ' ')
    if name_clean.endswith(' flag') or 'flag:' in name_clean:
        return "flags"
    if 'heart' in name_clean or 'love' in name_clean:
        return "hearts"
    if any(w in name_clean for w in ['face', 'smile', 'grin', 'laugh', 'tear']):
        return "smileys"
    if any(w in name_clean for w in ['cat', 'dog', 'bird', 'fish', 'tree', 'flower', 'moon', 'star']):
        return "animals_nature"
    if any(w in name_clean for w in ['food', 'drink', 'coffee', 'beer', 'pizza', 'fruit']):
        return "food_drink"
    if any(w in name_clean for w in ['car', 'bus', 'train', 'plane', 'bicycle', 'mountain']):
        return "travel_places"
    if any(w in name_clean for w in ['sport', 'ball', 'game', 'music', 'movie', 'camera']):
        return "activities"
    if any(w in name_clean for w in ['arrow', 'symbol', 'sign', 'button', 'warning']):
        return "symbols"
    if any(w in name_clean for w in ['hand', 'finger', 'wave', 'clap', 'person', 'man', 'woman']):
        return "people"
    return "other"

def build_categories_with_counts(emoji_list):
    counts = defaultdict(int)
    for item in emoji_list:
        cat = guess_category_from_name(item.get("name", ""))
        item["category"] = cat
        counts[cat] += 1
    display_map = {
        "flags": ("🏁", "Flags"), "hearts": ("❤️", "Hearts"), "smileys": ("😃", "Smileys"),
        "animals_nature": ("🐾", "Animals & Nature"), "food_drink": ("🍔", "Food & Drink"),
        "travel_places": ("✈️", "Travel & Places"), "activities": ("⚽", "Activities"),
        "symbols": ("🔣", "Symbols"), "people": ("👥", "People"), "other": ("📦", "Other")
    }
    categories = {}
    for cat, cnt in sorted(counts.items()):
        icon, name = display_map.get(cat, ("🔸", cat.replace('_', ' ').title()))
        categories[name] = (cat, icon, cnt)
    return categories


class EmojiModel(QAbstractListModel):
    def __init__(self, emoji_data, parent=None):
        super().__init__(parent)
        self.all_emojis = emoji_data
        self.filtered_indices = []
        self.current_category = "all"
        self.current_search = ""

    def set_filter(self, category, search_text):
        self.current_category = category
        self.current_search = search_text.lower().strip()
        self.refresh_filter()

    def refresh_filter(self):
        self.beginResetModel()
        self.filtered_indices.clear()
        for idx, emoji in enumerate(self.all_emojis):
            cat_match = (self.current_category == "all") or (emoji.get("category", "other") == self.current_category)
            name = emoji.get("name", "").lower()
            name_clean = name.strip(':').replace('_', ' ')
            search_match = (not self.current_search) or (self.current_search in name_clean)
            if cat_match and search_match:
                self.filtered_indices.append(idx)
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        return len(self.filtered_indices)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or index.row() >= len(self.filtered_indices):
            return None
        real_idx = self.filtered_indices[index.row()]
        emoji = self.all_emojis[real_idx]
        if role == Qt.DisplayRole:
            return emoji["emoji"]
        elif role == Qt.ToolTipRole:
            name = emoji.get("name", "").strip(':').replace('_', ' ')
            return f"{name}\n(category: {emoji.get('category', 'other')})"
        elif role == Qt.UserRole:
            return emoji
        return None

class EmojiDelegate(QStyledItemDelegate):
    def __init__(self, parent=None, copy_callback=None):
        super().__init__(parent)
        self.copy_callback = copy_callback

    def paint(self, painter, option, index):
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)

        is_hovered = bool(option.state & QStyle.State_MouseOver)
        rect = option.rect.adjusted(2, 2, -2, -2)
        if is_hovered:
            gradient = QLinearGradient(rect.topLeft(), rect.bottomRight())
            gradient.setColorAt(0, QColor("#facc15"))
            gradient.setColorAt(1, QColor("#eab308"))
            painter.setBrush(QBrush(gradient))
        else:
            painter.setBrush(QBrush(QColor("#1e1e2e")))

        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(rect, 14, 14)

        emoji = index.data(Qt.DisplayRole)
        painter.setPen(QColor(255, 255, 255))
        font = QFont("Segoe UI Emoji", 30)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignCenter, emoji)

        painter.restore()

    def sizeHint(self, option, index):
        return QSize(95, 95)

    def editorEvent(self, event, model, option, index):
        if event.type() == event.MouseButtonRelease and event.button() == Qt.LeftButton:
            emoji_data = index.data(Qt.UserRole)
            if emoji_data and self.copy_callback:
                self.copy_callback(emoji_data["emoji"])
                return True
        return super().editorEvent(event, model, option, index)


class ModernEmojiSearch(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Emoji Universe — Golden")
        self.setGeometry(100, 100, 1200, 850)

        emoji_data, error = load_emoji_data()
        if emoji_data is None:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Error", f"{error}\n\nUsing minimal fallback.")
            emoji_data = [
                {"emoji": "😀", "name": "grinning face"},
                {"emoji": "❤️", "name": "red heart"},
                {"emoji": "🐶", "name": "dog face"},
                {"emoji": "🍕", "name": "pizza"},
            ]
        self.emoji_list = emoji_data
        self.categories = build_categories_with_counts(self.emoji_list)

        self.setup_ui()
        self.setup_shortcuts()
        self.apply_filter()

        self.setup_tray_icon()


    @staticmethod
    def create_app_icon():
        base_dir = os.path.dirname(os.path.abspath(__file__))
        icon_path = os.path.join(base_dir, "assets", "icon.png")
        ico_path = os.path.join(base_dir, "assets", "icon.ico")

        if os.path.exists(ico_path):
            return QIcon(ico_path)
        if os.path.exists(icon_path):
            original = QIcon(icon_path)
            icon = QIcon()
            for size in [16, 32, 48, 64, 128, 256]:
                pix = original.pixmap(QSize(size, size))
                if not pix.isNull():
                    icon.addPixmap(pix)
            return icon
        else:
            icon = QIcon()
            for size in [16, 32, 48, 64, 128, 256]:
                pixmap = QPixmap(size, size)
                pixmap.fill(QColor("#eab308"))
                painter = QPainter(pixmap)
                painter.setFont(QFont("Segoe UI Emoji", size // 2))
                painter.drawText(pixmap.rect(), Qt.AlignCenter, "😀")
                painter.end()
                icon.addPixmap(pixmap)
            print("Info: No assets/icon.png found. Using built-in gold smiley icon.", file=sys.stderr)
            return icon


    def setup_tray_icon(self):
        icon = self.create_app_icon()
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(icon)
        self.tray_icon.setToolTip("Emoji Universe")

        tray_menu = QMenu()
        show_action = QAction("Show Window", self)
        show_action.triggered.connect(self.show_normal)
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(QApplication.quit)

        tray_menu.addAction(show_action)
        tray_menu.addSeparator()
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.on_tray_icon_activated)
        self.tray_icon.show()

    def on_tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick or reason == QSystemTrayIcon.Trigger:
            if self.isVisible():
                self.hide()
            else:
                self.show_normal()

    def show_normal(self):
        self.show()
        self.raise_()
        self.activateWindow()

    def closeEvent(self, event):
        event.ignore()
        self.hide()
        self.tray_icon.showMessage(
            "Emoji Universe",
            "Application minimized to system tray. Click the icon to restore.",
            QSystemTrayIcon.Information,
            2000
        )


    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)


        self.sidebar = QFrame()
        self.sidebar.setFixedWidth(280)
        self.sidebar.setStyleSheet("""
            QFrame {
                background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1a1a1a, stop:1 #2d2d2d);
                border-right: 1px solid #3e3e3e;
            }
            QLabel#title {
                font-size: 24px;
                font-weight: bold;
                color: #facc15;
                padding: 30px 20px 10px 20px;
                font-family: 'Segoe UI', 'Segoe UI Emoji';
            }
            QLabel#subtitle {
                color: #d4d4d8;
                font-size: 12px;
                padding: 0 20px 20px 20px;
                border-bottom: 1px solid #3e3e3e;
            }
            QLabel#infoFooter {
                color: #a1a1aa;
                font-size: 11px;
                padding: 20px;
                border-top: 1px solid #3e3e3e;
                margin-top: 20px;
            }
        """)
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        title = QLabel("✨ EMOJI UNIVERSE")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignCenter)
        sidebar_layout.addWidget(title)

        subtitle = QLabel("Click any emoji to copy · Search by name")
        subtitle.setObjectName("subtitle")
        subtitle.setAlignment(Qt.AlignCenter)
        sidebar_layout.addWidget(subtitle)

        self.category_scroll = QScrollArea()
        self.category_scroll.setWidgetResizable(True)
        self.category_scroll.setFrameShape(QScrollArea.NoFrame)
        self.category_scroll.setStyleSheet("background: transparent; border: none;")
        cat_container = QWidget()
        self.cat_layout = QVBoxLayout(cat_container)
        self.cat_layout.setSpacing(8)
        self.cat_layout.setContentsMargins(15, 20, 15, 20)
        self.cat_layout.setAlignment(Qt.AlignTop)

        self.all_btn = self.create_category_button("🌟 All Emojis", "all", total_count=len(self.emoji_list))
        self.cat_layout.addWidget(self.all_btn)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background-color: #3e3e3e; max-height: 1px; margin: 10px 0;")
        self.cat_layout.addWidget(sep)

        self.cat_buttons = {}
        for display_name, (cat_key, icon, cnt) in self.categories.items():
            btn = self.create_category_button(f"{icon} {display_name}", cat_key, cnt)
            self.cat_layout.addWidget(btn)
            self.cat_buttons[cat_key] = btn

        self.category_scroll.setWidget(cat_container)
        sidebar_layout.addWidget(self.category_scroll)

        footer = QLabel("💡 Tip: Use Ctrl+F to search\n🎨 Golden theme · Smooth scrolling")
        footer.setObjectName("infoFooter")
        footer.setWordWrap(True)
        sidebar_layout.addWidget(footer)


        main_area = QWidget()
        main_area.setStyleSheet("background-color: #121212;")
        main_layout_main = QVBoxLayout(main_area)
        main_layout_main.setContentsMargins(30, 30, 30, 30)
        main_layout_main.setSpacing(20)


        search_row = QHBoxLayout()
        search_row.setSpacing(12)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Search emojis... (e.g., 'heart', 'flag', 'smile')")
        self.search_input.setFixedHeight(56)
        self.search_input.setFont(QFont("Segoe UI", 12))
        self.search_input.setStyleSheet("""
            QLineEdit {
                background-color: #1e1e2e;
                border: 2px solid #3e3e3e;
                border-radius: 28px;
                padding: 12px 24px;
                color: #facc15;
                font-size: 13pt;
            }
            QLineEdit:focus {
                border: 2px solid #facc15;
                background-color: #1e1e2e;
            }
        """)
        self.search_input.textChanged.connect(self.on_search_debounced)

        self.clear_btn = QPushButton("✖")
        self.clear_btn.setFixedSize(40, 40)
        self.clear_btn.setCursor(Qt.PointingHandCursor)
        self.clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #3e3e3e;
                border-radius: 20px;
                color: #facc15;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #ef4444;
                color: white;
            }
        """)
        self.clear_btn.clicked.connect(self.clear_search)
        self.clear_btn.hide()

        self.random_btn = QPushButton("🎲")
        self.random_btn.setFixedSize(56, 56)
        self.random_btn.setCursor(Qt.PointingHandCursor)
        self.random_btn.setToolTip("Random emoji")
        self.random_btn.setStyleSheet("""
            QPushButton {
                background-color: #facc15;
                border-radius: 28px;
                color: #121212;
                font-size: 24px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #fde047;
            }
        """)
        self.random_btn.clicked.connect(self.pick_random_emoji)

        search_row.addWidget(self.search_input)
        search_row.addWidget(self.clear_btn)
        search_row.addWidget(self.random_btn)

        self.result_label = QLabel()
        self.result_label.setAlignment(Qt.AlignLeft)
        self.result_label.setFont(QFont("Segoe UI", 11))
        self.result_label.setStyleSheet("""
            QLabel {
                color: #a3e635;
                background-color: #1e1e2e;
                padding: 8px 16px;
                border-radius: 24px;
            }
        """)
        self.result_label.hide()

        self.list_view = QListView()
        self.list_view.setViewMode(QListView.IconMode)
        self.list_view.setGridSize(QSize(95, 95))
        self.list_view.setIconSize(QSize(95, 95))
        self.list_view.setResizeMode(QListView.Adjust)
        self.list_view.setMovement(QListView.Static)
        self.list_view.setSpacing(10)
        self.list_view.setWordWrap(False)
        self.list_view.setSelectionMode(QAbstractItemView.NoSelection)
        self.list_view.setStyleSheet("""
            QListView {
                background-color: transparent;
                border: none;
                outline: none;
            }
            QListView::item {
                background-color: transparent;
            }
        """)

        self.model = EmojiModel(self.emoji_list)
        self.delegate = EmojiDelegate(self.list_view, copy_callback=self.copy_emoji)
        self.list_view.setModel(self.model)
        self.list_view.setItemDelegate(self.delegate)
        self.model.modelReset.connect(self.update_result_label)

        main_layout_main.addLayout(search_row)
        main_layout_main.addWidget(self.result_label)
        main_layout_main.addWidget(self.list_view)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self.sidebar)
        splitter.addWidget(main_area)
        splitter.setSizes([280, 920])
        splitter.setHandleWidth(2)
        splitter.setStyleSheet("QSplitter::handle { background-color: #3e3e3e; }")
        main_layout.addWidget(splitter)

        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.apply_filter)

        self.current_category = "all"
        self.highlight_category_button("all")

        self.statusBar().setStyleSheet("""
            QStatusBar {
                background-color: #121212;
                color: #d4d4d8;
                padding: 4px;
                font-size: 12px;
            }
        """)

    def setup_shortcuts(self):
        ctrl_f = QShortcut(QKeySequence("Ctrl+F"), self)
        ctrl_f.activated.connect(lambda: self.search_input.setFocus())
        esc = QShortcut(QKeySequence("Esc"), self)
        esc.activated.connect(self.clear_search)

    def create_category_button(self, text, cat_key, total_count=None):
        btn = QPushButton()
        layout = QHBoxLayout(btn)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(8)

        label = QLabel(text)
        label.setStyleSheet("color: #e4e4e7; font-size: 13px; background: transparent;")
        label.setFont(QFont("Segoe UI", 11))
        layout.addWidget(label)

        if total_count is not None:
            count_label = QLabel(str(total_count))
            count_label.setStyleSheet("""
                background-color: #3e3e3e;
                border-radius: 12px;
                padding: 2px 8px;
                color: #facc15;
                font-size: 11px;
                font-weight: bold;
            """)
            layout.addWidget(count_label)

        layout.addStretch()
        btn.setCursor(Qt.PointingHandCursor)
        btn.setFixedHeight(44)
        btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border-radius: 12px;
                text-align: left;
            }
            QPushButton:hover {
                background-color: #3e3e3e;
            }
        """)
        btn.clicked.connect(lambda: self.set_category_filter(cat_key))
        return btn

    def highlight_category_button(self, active_key):
        default_style = """
            QPushButton {
                background-color: transparent;
                border-radius: 12px;
            }
            QPushButton:hover {
                background-color: #3e3e3e;
            }
        """
        active_style = """
            QPushButton {
                background-color: #facc15;
                border-radius: 12px;
            }
            QPushButton:hover {
                background-color: #fde047;
            }
        """
        for btn in self.cat_buttons.values():
            btn.setStyleSheet(default_style)
            for child in btn.findChildren(QLabel):
                if child.text().startswith(("🌟", "🏁", "❤️", "😃", "🐾", "🍔", "✈️", "⚽", "🔣", "👥", "📦")):
                    child.setStyleSheet("color: #e4e4e7; font-size: 13px; background: transparent;")
        self.all_btn.setStyleSheet(default_style)
        if active_key == "all":
            self.all_btn.setStyleSheet(active_style)
            for child in self.all_btn.findChildren(QLabel):
                child.setStyleSheet("color: #ffffff; font-size: 13px; background: transparent; font-weight: bold;")
        else:
            btn = self.cat_buttons.get(active_key)
            if btn:
                btn.setStyleSheet(active_style)
                for child in btn.findChildren(QLabel):
                    child.setStyleSheet("color: #ffffff; font-size: 13px; background: transparent; font-weight: bold;")

    def on_search_debounced(self):
        text = self.search_input.text()
        self.clear_btn.setVisible(bool(text.strip()))
        self.search_timer.start(300)

    def clear_search(self):
        self.search_input.clear()
        self.search_input.setFocus()

    def set_category_filter(self, category_key):
        self.current_category = category_key
        self.highlight_category_button(category_key)
        self.apply_filter()

    def apply_filter(self):
        search_text = self.search_input.text()
        self.model.set_filter(self.current_category, search_text)

    def update_result_label(self):
        count = self.model.rowCount()
        if count == 0:
            self.result_label.setText("😕 No emojis match your search")
            self.result_label.show()
        else:
            self.result_label.setText(f"✨ {count} emoji{'s' if count != 1 else ''} found")
            self.result_label.show()
            effect = QGraphicsOpacityEffect()
            self.result_label.setGraphicsEffect(effect)
            anim = QPropertyAnimation(effect, b"opacity")
            anim.setDuration(300)
            anim.setStartValue(0.0)
            anim.setEndValue(1.0)
            anim.start()

    def copy_emoji(self, emoji_char):
        QApplication.clipboard().setText(emoji_char)
        self.statusBar().showMessage(f"✅ Copied {emoji_char} to clipboard!", 2000)
        pos = self.mapFromGlobal(QCursor.pos())
        QToolTip.showText(self.mapToGlobal(pos), f"Copied {emoji_char}", self, QRect(), 1500)

    def pick_random_emoji(self):
        count = self.model.rowCount()
        if count == 0:
            return
        random_row = random.randint(0, count - 1)
        index = self.model.index(random_row, 0)
        emoji_data = self.model.data(index, Qt.UserRole)
        if emoji_data:
            self.copy_emoji(emoji_data["emoji"])
            self.list_view.scrollTo(index, QAbstractItemView.PositionAtCenter)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    if sys.platform == "win32":
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("EmojiUniverse.App")
        except Exception:
            pass

    app_icon = ModernEmojiSearch.create_app_icon()

    app.setWindowIcon(app_icon)

    window = ModernEmojiSearch()
    window.setWindowIcon(app_icon)

    if sys.platform == "win32":
        try:
            hwnd = int(window.winId())
            big_pix = app_icon.pixmap(32, 32)
            small_pix = app_icon.pixmap(16, 16)
            if hasattr(big_pix, "toWinHICON") and hasattr(small_pix, "toWinHICON"):
                big_hicon = big_pix.toWinHICON()
                small_hicon = small_pix.toWinHICON()
                if big_hicon and small_hicon:
                    user32.SendMessageW(hwnd, WM_SETICON, ICON_BIG, big_hicon)
                    user32.SendMessageW(hwnd, WM_SETICON, ICON_SMALL, small_hicon)
                    user32.SetClassLongW(hwnd, GCL_HICON, big_hicon)
                    user32.SetClassLongW(hwnd, GCL_HICONSM, small_hicon)
        except Exception as e:
            print(f"Could not force taskbar icon via WM_SETICON: {e}")

    window.show()
    sys.exit(app.exec_())
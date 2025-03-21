import sys
import os
import requests
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton, 
                            QTreeWidget, QTreeWidgetItem, QScrollArea, QLabel, QHBoxLayout, 
                            QFrame, QToolButton, QDialog, QLineEdit, QTableWidget, QTableWidgetItem,
                            QHeaderView, QMessageBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QFontDatabase, QPixmap, QIcon
from PyQt5.QtWidgets import QStyle  # 引入 QStyle 以使用內建圖示
from datetime import datetime
import traceback
import urllib.request
from io import BytesIO

# 動態獲取資源文件路徑（適應 PyInstaller 打包）
def resource_path(relative_path):
    """獲取資源文件的絕對路徑，適應 PyInstaller 打包"""
    if hasattr(sys, '_MEIPASS'):
        print("臨時目錄:", sys._MEIPASS)
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

# 獲取 characters.txt 的儲存路徑（用戶家目錄下的 Documents 資料夾）
def get_characters_file_path():
    documents_path = os.path.expanduser("~/Documents")
    if not os.path.exists(documents_path):
        os.makedirs(documents_path)
    return os.path.join(documents_path, "characters.txt")

# 定義職業顏色表
CLASS_COLORS = {
    "Death Knight": "#C41E3A",
    "Demon Hunter": "#A330C9",
    "Druid": "#FF7C0A",
    "Evoker": "#33937F",
    "Hunter": "#AAD372",
    "Mage": "#3FC7EB",
    "Monk": "#00FF98",
    "Paladin": "#F48CBA",
    "Priest": "#FFFFFF",
    "Rogue": "#FFF468",
    "Shaman": "#0070DD",
    "Warlock": "#8788EE",
    "Warrior": "#C69B6D"
}

# 定義副本名稱映射表（英文 -> 繁體中文）
DUNGEON_NAME_MAPPING = {
    "Darkflame Cleft": "暗焰裂隙",
    "Operation: Floodgate": "水閘行動",
    "Cinderbrew Meadery": "燼釀酒莊",
    "The MOTHERLODE!!": "晶礦母脈",
    "The Rookery": "鴉巢",
    "Theater of Pain": "苦痛劇場",
    "Priory of the Sacred Flame": "聖焰隱修院",
    "Mechagon Workshop": "機械岡行動：工坊"
}

class CharacterManagerWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("角色管理")
        self.setGeometry(200, 200, 600, 400)

        # 移除標題欄中的問號按鈕
        self.setWindowFlags(Qt.WindowCloseButtonHint | Qt.Dialog)

        self.setStyleSheet("""
            QDialog {
                background-color: #0f1318;
                color: #ffffff;
            }
            QLineEdit {
                background-color: #1D2128;
                color: #ffffff;
                border: 1px solid #2A2F36;
                padding: 5px;
                border-radius: 4px;
            }
            QTableWidget {
                background-color: #1D2128;
                color: #ffffff;
                border: 1px solid #2A2F36;
                gridline-color: #2A2F36;
                alternate-background-color: #252C38;
            }
            QTableWidget::item {
                padding: 5px;
            }
            QHeaderView::section {
                background-color: #252C38;
                color: #999999;
                padding: 5px;
                border: none;
            }
            QPushButton {
                background-color: #FF9A00;
                color: #ffffff;
                padding: 5px 10px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #FF8500;
            }
            QPushButton:pressed {
                background-color: #E07800;
            }
        """)

        # 將視窗移到螢幕中心
        self.center_window()

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)
        self.layout.setSpacing(10)

        # 輸入區域
        input_layout = QHBoxLayout()
        self.region_input = QLineEdit()
        self.region_input.setPlaceholderText("地區 (預設為 tw)")
        self.region_input.setText("tw")  # 預設地區為 tw
        input_layout.addWidget(self.region_input)

        self.realm_input = QLineEdit()
        self.realm_input.setPlaceholderText("伺服器 (例如 illidan)")
        input_layout.addWidget(self.realm_input)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("角色名稱")
        input_layout.addWidget(self.name_input)

        add_button = QPushButton("新增")
        add_button.clicked.connect(self.add_character)
        input_layout.addWidget(add_button)

        self.layout.addLayout(input_layout)

        # 角色名單表格
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["地區", "伺服器", "角色名稱"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.DoubleClicked)  # 允許雙擊編輯
        self.table.setAlternatingRowColors(True)  # 啟用交替行背景色
        self.table.itemSelectionChanged.connect(self.on_selection_changed)
        self.layout.addWidget(self.table)

        # 按鈕區域
        button_layout = QHBoxLayout()
        self.edit_button = QPushButton("編輯")
        self.edit_button.setEnabled(False)
        self.edit_button.clicked.connect(self.edit_character)
        button_layout.addWidget(self.edit_button)

        self.delete_button = QPushButton("刪除")
        self.delete_button.setEnabled(False)
        self.delete_button.clicked.connect(self.delete_character)
        button_layout.addWidget(self.delete_button)

        save_button = QPushButton("儲存")
        save_button.clicked.connect(self.save_characters)
        button_layout.addWidget(save_button)

        self.layout.addLayout(button_layout)

        # 載入角色名單
        self.characters = []
        self.load_characters()

    def center_window(self):
        # 獲取螢幕的可用幾何形狀
        screen = QApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        screen_center = screen_geometry.center()

        # 獲取視窗的幾何形狀
        window_geometry = self.frameGeometry()
        window_geometry.moveCenter(screen_center)
        self.move(window_geometry.topLeft())

    def load_characters(self):
        self.characters = []
        filepath = get_characters_file_path()
        if not os.path.exists(filepath):
            # 如果檔案不存在，創建一個空的 characters.txt
            try:
                with open(filepath, "w", encoding="utf-8") as file:
                    file.write("# 角色資料格式：地區,伺服器,角色名稱\n")
            except Exception as e:
                QMessageBox.warning(self, "錯誤", f"無法創建角色檔案: {str(e)}")
                return

        try:
            with open(filepath, "r", encoding="utf-8") as file:
                for line in file:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        parts = line.split(",")
                        if len(parts) == 3:
                            region, realm, name = [p.strip() for p in parts]
                            self.characters.append((region, realm, name))
        except Exception as e:
            QMessageBox.warning(self, "錯誤", f"無法讀取角色檔案: {str(e)}")

        # 更新表格
        self.table.setRowCount(len(self.characters))
        for row, (region, realm, name) in enumerate(self.characters):
            self.table.setItem(row, 0, QTableWidgetItem(region))
            self.table.setItem(row, 1, QTableWidgetItem(realm))
            self.table.setItem(row, 2, QTableWidgetItem(name))

    def add_character(self):
        region = self.region_input.text().strip() or "tw"  # 預設為 tw
        realm = self.realm_input.text().strip()
        name = self.name_input.text().strip()

        if not realm or not name:
            QMessageBox.warning(self, "錯誤", "請填寫伺服器和角色名稱！")
            return

        self.characters.append((region, realm, name))
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(region))
        self.table.setItem(row, 1, QTableWidgetItem(realm))
        self.table.setItem(row, 2, QTableWidgetItem(name))

        # 清空輸入框（除了地區，保持為 tw）
        self.realm_input.clear()
        self.name_input.clear()

    def on_selection_changed(self):
        selected_rows = self.table.selectionModel().selectedRows()
        self.edit_button.setEnabled(len(selected_rows) > 0)
        self.delete_button.setEnabled(len(selected_rows) > 0)

        if selected_rows:
            row = selected_rows[0].row()
            region = self.table.item(row, 0).text()
            realm = self.table.item(row, 1).text()
            name = self.table.item(row, 2).text()
            self.region_input.setText(region)
            self.realm_input.setText(realm)
            self.name_input.setText(name)

    def edit_character(self):
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            return

        row = selected_rows[0].row()
        region = self.region_input.text().strip() or "tw"  # 預設為 tw
        realm = self.realm_input.text().strip()
        name = self.name_input.text().strip()

        if not realm or not name:
            QMessageBox.warning(self, "錯誤", "請填寫伺服器和角色名稱！")
            return

        self.characters[row] = (region, realm, name)
        self.table.setItem(row, 0, QTableWidgetItem(region))
        self.table.setItem(row, 1, QTableWidgetItem(realm))
        self.table.setItem(row, 2, QTableWidgetItem(name))

        # 清空輸入框（除了地區，保持為 tw）
        self.realm_input.clear()
        self.name_input.clear()
        self.table.clearSelection()

    def delete_character(self):
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            return

        row = selected_rows[0].row()
        reply = QMessageBox.question(self, "確認", f"確定要刪除角色 {self.characters[row][2]} 嗎？",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.characters.pop(row)
            self.table.removeRow(row)
            self.region_input.setText("tw")  # 恢復預設值
            self.realm_input.clear()
            self.name_input.clear()
            self.table.clearSelection()

    def save_characters(self):
        # 從表格獲取資料
        self.characters = []
        for row in range(self.table.rowCount()):
            region = self.table.item(row, 0).text().strip() or "tw"  # 預設為 tw
            realm = self.table.item(row, 1).text().strip()
            name = self.table.item(row, 2).text().strip()
            if realm and name:  # 確保伺服器和角色名稱不為空
                self.characters.append((region, realm, name))

        try:
            filepath = get_characters_file_path()
            with open(filepath, "w", encoding="utf-8") as file:
                file.write("# 角色資料格式：地區,伺服器,角色名稱\n")
                for region, realm, name in self.characters:
                    file.write(f"{region},{realm},{name}\n")
            QMessageBox.information(self, "成功", "角色資料已儲存！")
            self.accept()  # 關閉視窗
        except Exception as e:
            QMessageBox.warning(self, "錯誤", f"無法儲存角色檔案: {str(e)}")

class DataFetcher(QThread):
    data_fetched = pyqtSignal(list)

    def __init__(self, characters):
        super().__init__()
        self.characters = characters

    def run(self):
        results = []
        for region, realm, name in self.characters:
            result = self.fetch_character_data(region, realm, name)
            results.append((region, realm, name, result))
        self.data_fetched.emit(results)

    def fetch_character_data(self, region, realm, character_name):
        base_url = "https://raider.io/api/v1/characters/profile"
        params = {
            "region": region,
            "realm": realm,
            "name": character_name,
            "fields": "mythic_plus_scores_by_season:current,mythic_plus_best_runs,mythic_plus_recent_runs,thumbnail_url,class"
        }
        try:
            response = requests.get(base_url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e)}

    @staticmethod
    def format_time(milliseconds):
        seconds = milliseconds / 1000
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    
    @staticmethod
    def format_datetime(datetime_str):
        try:
            dt = datetime.strptime(datetime_str, "%Y-%m-%dT%H:%M:%S.%fZ")
            return dt.strftime("%Y/%m/%d %H:%M")
        except Exception:
            return datetime_str

class RaiderIOMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Raider.IO Mythic+ 查詢工具")
        self.setGeometry(100, 100, 1000, 800)

        # 設置視窗圖標和工作列圖標
        icon_path = resource_path("icon.ico")
        print("視窗圖標路徑:", icon_path)
        icon = QIcon(icon_path)
        if icon.isNull():
            print("視窗圖標載入失敗:", icon_path)
        else:
            print("視窗圖標載入成功:", icon_path)
        self.setWindowIcon(icon)

        # 將視窗移到螢幕中心
        self.center_window()

        # 設置視窗背景顏色，與程式內部一致
        self.setStyleSheet("""
            QMainWindow {
                background-color: #0f1318;
                color: #ffffff;
            }
            QWidget {
                background-color: #0f1318;
                color: #ffffff;
            }
            QScrollArea {
                border: none;
                background-color: #0f1318;
            }
            QLabel {
                color: #ffffff;
            }
        """)

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        logo_label = QLabel("上班摸魚做ㄉ")
        logo_label.setFont(QFont("Arial", 18, QFont.Bold))
        logo_label.setStyleSheet("color: #FF9A00;")
        header_layout.addWidget(logo_label)
        
        header_layout.addStretch()

        # 添加詞綴顯示區域，放在「更新資料」按鈕的左邊
        self.affixes_frame = QFrame()
        self.affixes_frame.setStyleSheet("background-color: #252C38; border-radius: 4px; padding: 2px;")
        self.affixes_layout = QHBoxLayout(self.affixes_frame)
        self.affixes_layout.setContentsMargins(5, 0, 5, 0)
        self.affixes_layout.setSpacing(5)
        header_layout.addWidget(self.affixes_frame)
        self.load_affixes()  # 載入本週詞綴

        # 在詞綴區塊和「更新資料」按鈕之間添加間距，向左移動詞綴區塊
        header_layout.addSpacing(20)  # 添加 20 像素間距，讓詞綴區塊更靠近左邊
        
        self.update_button = QPushButton()
        self.update_button.setFont(QFont("Noto Sans TC", 11))
        self.update_button.setCursor(Qt.PointingHandCursor)
        self.update_button.setMinimumHeight(40)
        self.update_button.setFixedWidth(40)  # 設置按鈕為正方形
        self.update_button.setIcon(QIcon(resource_path("refresh.ico")))  # 使用自訂圖示
        self.update_button.setStyleSheet("""
            QPushButton {
                background-color: #FF9A00;
                color: #ffffff;
                padding: 8px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #FF8500;
            }
            QPushButton:pressed {
                background-color: #E07800;
            }
            QPushButton:disabled {
                background-color: #555555;
                color: #888888;
            }
        """)
        self.update_button.clicked.connect(self.update_data)
        header_layout.addWidget(self.update_button)

        # 新增「+」按鍵
        self.add_character_button = QPushButton("+")
        self.add_character_button.setFont(QFont("Noto Sans TC", 11))
        self.add_character_button.setCursor(Qt.PointingHandCursor)
        self.add_character_button.setMinimumHeight(40)
        self.add_character_button.setFixedWidth(40)
        self.add_character_button.setStyleSheet("""
            QPushButton {
                background-color: #FF9A00;
                color: #ffffff;
                padding: 8px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #FF8500;
            }
            QPushButton:pressed {
                background-color: #E07800;
            }
        """)
        self.add_character_button.clicked.connect(self.open_character_manager)
        header_layout.addWidget(self.add_character_button)
        
        main_layout.addWidget(header_widget)
        
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet("background-color: #2A2F36; min-height: 2px;")
        main_layout.addWidget(separator)
        
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("""
            QScrollArea { 
                background-color: #0f1318; 
                border: none; 
            }
            QScrollBar:vertical { 
                background: #1D2128; 
                width: 12px; 
                margin: 0px; 
            }
            QScrollBar::handle:vertical { 
                background: #434953; 
                min-height: 20px; 
                border-radius: 6px; 
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { 
                height: 0px; 
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """)
        
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setContentsMargins(0, 0, 0, 0)
        self.scroll_layout.setSpacing(20)
        self.scroll_area.setWidget(self.scroll_content)
        
        main_layout.addWidget(self.scroll_area)
        
        self.status_bar = self.statusBar()
        self.status_bar.setStyleSheet("background-color: #16181D; color: #999999; padding: 5px;")
        
        self.expansion_states = {}
        self.dungeon_expansion_states = {}
        
        self.update_data()

    def center_window(self):
        # 獲取螢幕的可用幾何形狀
        screen = QApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        screen_center = screen_geometry.center()

        # 獲取視窗的幾何形狀
        window_geometry = self.frameGeometry()
        window_geometry.moveCenter(screen_center)
        self.move(window_geometry.topLeft())

    def open_character_manager(self):
        dialog = CharacterManagerWindow(self)
        dialog.exec_()
        # 角色名單更新後，重新載入資料
        self.update_data()

    def load_characters_from_file(self, filename="characters.txt"):
        characters = []
        filepath = get_characters_file_path()
        if not os.path.exists(filepath):
            # 如果檔案不存在，創建一個空的 characters.txt
            try:
                with open(filepath, "w", encoding="utf-8") as file:
                    file.write("# 角色資料格式：地區,伺服器,角色名稱\n")
            except Exception as e:
                self.status_bar.showMessage(f"無法創建角色檔案: {str(e)}")
                return []

        try:
            with open(filepath, "r", encoding="utf-8") as file:
                for line in file:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        parts = line.split(",")
                        if len(parts) == 3:
                            region, realm, name = [p.strip() for p in parts]
                            characters.append((region, realm, name))
        except Exception as e:
            self.status_bar.showMessage(f"無法讀取角色檔案: {str(e)}")
            return []
        return characters

    def load_affixes(self):
        """從 Raider.IO API 載入本週詞綴並顯示"""
        try:
            url = "https://raider.io/api/v1/mythic-plus/affixes?region=tw&locale=tw"
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            data = response.json()

            # 清空現有的詞綴顯示
            while self.affixes_layout.count():
                item = self.affixes_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

            # 添加「本週詞綴」文字
            affix_title_label = QLabel("本週詞綴")
            affix_title_label.setFont(QFont("Noto Sans TC", 14, QFont.Bold))  # 與 Raider.IO 標誌字體一致
            affix_title_label.setStyleSheet("color: #FF9A00;")  # 與 Raider.IO 標誌顏色一致
            # 調整邊距，讓文字往上移動（增加底部邊距）
            affix_title_label.setContentsMargins(0, 0, 0, 3)  # 左、上、右、下，增加 5 像素底部邊距
            self.affixes_layout.addWidget(affix_title_label)    

            # 顯示每個詞綴
            for affix in data.get("affix_details", []):
                icon_name = affix.get("icon", "")
                name = affix.get("name", "未知詞綴")
                description = affix.get("description", "無描述")

                # 獲取詞綴縮圖
                icon_url = f"https://render.worldofwarcraft.com/us/icons/56/{icon_name}.jpg"
                try:
                    with urllib.request.urlopen(icon_url) as response:
                        img_data = response.read()
                    pixmap = QPixmap()
                    pixmap.loadFromData(img_data)
                    pixmap = pixmap.scaled(40, 40, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                except Exception as e:
                    print(f"無法載入詞綴縮圖 {icon_name}: {str(e)}")
                    pixmap = QPixmap()  # 空圖片作為備用

                # 創建詞綴圖示標籤
                affix_label = QLabel()
                affix_label.setPixmap(pixmap)
                affix_label.setFixedSize(40, 40)

                # 設置工具提示，包含詞綴名稱和描述
                tooltip_text = f"{name}\n{description}"
                affix_label.setToolTip(tooltip_text)
                affix_label.setStyleSheet("color: #FFFFFF; font: 12px 'Noto Sans TC';")

                # 添加到佈局
                self.affixes_layout.addWidget(affix_label)
        except Exception as e:
            print(f"無法載入本週詞綴: {str(e)}")
            error_label = QLabel("無法載入詞綴")
            error_label.setStyleSheet("color: #FF5555; font: 12px 'Noto Sans TC';")
            self.affixes_layout.addWidget(error_label)

    def update_data(self):
        self.update_button.setEnabled(False)
        self.update_button.setIcon(QIcon())  # 清除圖示
        self.update_button.setText("更新中...")  # 顯示文字
        self.update_button.setFixedWidth(120)  # 調整寬度以適應文字
        self.status_bar.showMessage("正在更新角色資料...")
        
        self.save_expansion_states()
        
        characters = self.load_characters_from_file()
        if not characters:
            error_label = QLabel("未找到角色資料或檔案格式錯誤")
            error_label.setStyleSheet("color: #FF5555; font: 12px 'Noto Sans TC'; padding: 20px;")
            error_label.setAlignment(Qt.AlignCenter)
            self.clear_scroll_content()
            self.scroll_layout.addWidget(error_label)
            self.update_button.setEnabled(True)
            self.update_button.setText("")
            self.update_button.setIcon(QIcon(resource_path("refresh.ico")))  # 使用自訂圖示
            self.update_button.setFixedWidth(40)
            return

        self.clear_scroll_content()
        
        loading_label = QLabel("載入中...")
        loading_label.setAlignment(Qt.AlignCenter)
        loading_label.setStyleSheet("color: #999999; font: 14px 'Noto Sans TC'; padding: 20px;")
        self.scroll_layout.addWidget(loading_label)
        
        self.fetcher = DataFetcher(characters)
        self.fetcher.data_fetched.connect(self.display_data)
        self.fetcher.finished.connect(self.update_finished)
        self.fetcher.start()

    def update_finished(self):
        self.update_button.setEnabled(True)
        self.update_button.setText("")
        self.update_button.setIcon(QIcon(resource_path("refresh.ico")))  # 使用自訂圖示
        self.update_button.setFixedWidth(40)
        self.status_bar.showMessage("資料更新完成", 3000)

    def clear_scroll_content(self):
        while self.scroll_layout.count():
            child = self.scroll_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def save_expansion_states(self):
        self.expansion_states = {}
        self.dungeon_expansion_states = {}
        
        for i in range(self.scroll_layout.count()):
            widget = self.scroll_layout.itemAt(i).widget()
            if widget and hasattr(widget, 'objectName') and widget.objectName().startswith('charCard_'):
                char_id = widget.objectName().split('_')[1]
                content_frame = widget.findChild(QFrame, f'contentFrame_{char_id}')
                if content_frame:
                    self.expansion_states[char_id] = content_frame.isVisible()
                    
                    for dungeon_widget in content_frame.findChildren(QWidget, "^dungeonContent_.*"):
                        dungeon_id = dungeon_widget.objectName().split('_')[1]
                        detail_frame = dungeon_widget.findChild(QFrame, f'detailFrame_{dungeon_id}')
                        if detail_frame:
                            self.dungeon_expansion_states[dungeon_id] = detail_frame.isVisible()

    def get_score_color(self, score):
        if score >= 2000:
            return "#E16AFF"
        elif score >= 1500:
            return "#4C97FC"
        elif score >= 1000:
            return "#1CE2B2"
        elif score >= 500:
            return "#67FD0A"
        else:
            return "#FFFFFF"

    def toggle_content(self, char_id):
        sender = self.sender()
        content_frame = self.findChild(QFrame, f'contentFrame_{char_id}')
        
        if content_frame:
            is_visible = content_frame.isVisible()
            content_frame.setVisible(not is_visible)
            
            if is_visible:
                sender.setText("▼")
                sender.setToolTip("展開副本資訊")
            else:
                sender.setText("▲")
                sender.setToolTip("收起副本資訊")

    def toggle_dungeon_detail(self, dungeon_id):
        sender = self.sender()
        detail_frame = self.findChild(QFrame, f'detailFrame_{dungeon_id}')
        
        if detail_frame:
            is_visible = detail_frame.isVisible()
            detail_frame.setVisible(not is_visible)
            
            if is_visible:
                sender.setText("▼")
                sender.setToolTip("展開詳細紀錄")
            else:
                sender.setText("▲")
                sender.setToolTip("收起詳細紀錄")

    def display_data(self, results):
        try:
            self.clear_scroll_content()
            
            for idx, (region, realm, name, data) in enumerate(results):
                char_id = f"{region}_{realm}_{name}"
                
                char_widget = QWidget()
                char_widget.setObjectName(f"charCard_{char_id}")
                char_layout = QVBoxLayout(char_widget)
                char_layout.setContentsMargins(0, 0, 0, 0)
                char_layout.setSpacing(0)
                
                header_frame = QFrame()
                header_frame.setStyleSheet("background-color: #252C38; border-radius: 6px;")
                header_layout = QVBoxLayout(header_frame)
                header_layout.setContentsMargins(15, 15, 15, 15)
                
                char_header = QHBoxLayout()
                
                thumbnail_url = data.get("thumbnail_url", "")
                if thumbnail_url:
                    try:
                        with urllib.request.urlopen(thumbnail_url) as response:
                            img_data = response.read()
                        pixmap = QPixmap()
                        pixmap.loadFromData(img_data)
                        pixmap = pixmap.scaled(40, 40, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                        thumbnail_label = QLabel()
                        thumbnail_label.setPixmap(pixmap)
                        char_header.addWidget(thumbnail_label)
                    except Exception as e:
                        thumbnail_label = QLabel("無縮圖")
                        thumbnail_label.setStyleSheet("color: #999999; font: 12px 'Noto Sans TC';")
                        char_header.addWidget(thumbnail_label)
                else:
                    thumbnail_label = QLabel("無縮圖")
                    thumbnail_label.setStyleSheet("color: #999999; font: 12px 'Noto Sans TC';")
                    char_header.addWidget(thumbnail_label)
                
                toggle_button = QToolButton()
                is_expanded = self.expansion_states.get(char_id, idx < 2)
                toggle_button.setText("▲" if is_expanded else "▼")
                toggle_button.setStyleSheet("""
                    QToolButton {
                        background-color: transparent;
                        color: #999999;
                        border: none;
                        font-size: 14px;
                        font-weight: bold;
                    }
                    QToolButton:hover {
                        color: #FFFFFF;
                    }
                """)
                toggle_button.setToolTip(f'<span style="color: #FFFFFF;">{"收起副本資訊" if is_expanded else "展開副本資訊"}</span>')
                toggle_button.setObjectName(f"toggleBtn_{char_id}")
                toggle_button.clicked.connect(lambda checked, cid=char_id: self.toggle_content(cid))
                char_header.addWidget(toggle_button)
                
                # 套用職業顏色
                class_name = data.get("class", "Unknown")
                class_color = CLASS_COLORS.get(class_name, "#FFFFFF")
                title_label = QLabel(name)
                title_label.setFont(QFont("Noto Sans TC", 14, QFont.Bold))
                title_label.setStyleSheet(f"color: {class_color};")
                char_header.addWidget(title_label)
                
                realm_label = QLabel(f"{region}-{realm}")
                realm_label.setStyleSheet("color: #999999;")
                realm_label.setFont(QFont("Noto Sans TC", 12))
                char_header.addWidget(realm_label)
                
                char_header.addStretch()
                
                mythic_plus_scores = data.get("mythic_plus_scores_by_season", [])
                overall_score = mythic_plus_scores[0]["scores"]["all"] if mythic_plus_scores else "N/A"
                
                if isinstance(overall_score, (int, float)):
                    score_color = self.get_score_color(overall_score)
                    score_label = QLabel(f"{overall_score:.1f}")
                    score_label.setFont(QFont("Noto Sans TC", 16, QFont.Bold))
                    score_label.setStyleSheet(f"color: {score_color}; background-color: #1D2128; padding: 5px 10px; border-radius: 4px;")
                    char_header.addWidget(score_label)
                else:
                    score_label = QLabel("N/A")
                    score_label.setStyleSheet("color: #999999;")
                    char_header.addWidget(score_label)
                
                header_layout.addLayout(char_header)
                
                char_layout.addWidget(header_frame)
                
                content_frame = QFrame()
                content_frame.setObjectName(f"contentFrame_{char_id}")
                content_frame.setStyleSheet("background-color: #1D2128; border-radius: 6px; margin-top: 2px;")
                content_frame.setVisible(is_expanded)
                
                content_layout = QVBoxLayout(content_frame)
                content_layout.setContentsMargins(10, 10, 10, 10)
                
                dungeon_header = QWidget()
                dungeon_header_layout = QHBoxLayout(dungeon_header)
                dungeon_header_layout.setContentsMargins(5, 8, 5, 8)
                dungeon_header_layout.setSpacing(0)
                
                header_labels = ["副本", "層數", "分數", "鑰石", "通關時間", "完成日期"]
                header_widths = [200, 40, 40, 40, 60, 120]  # 固定每個欄位的寬度
                header_margins = [0, 2, 2, 2, 2, 2]  # 對應每個欄位的左邊距：副本 | 層數 | 分數 | 鑰石 | 通關時間 | 完成日期
                for i, (label, width, margin) in enumerate(zip(header_labels, header_widths, header_margins)):
                    header_label = QLabel(label)
                    header_label.setStyleSheet("color: #999999; font-weight: bold;")
                    header_label.setFont(QFont("Noto Sans TC", 10))
                    if i == 0:
                        header_label.setAlignment(Qt.AlignLeft)
                    else:
                        header_label.setAlignment(Qt.AlignCenter)
                    header_label.setMinimumWidth(width)
                    header_label.setMaximumWidth(width)
                    header_label.setContentsMargins(margin, 0, 0, 0)
                    dungeon_header_layout.addWidget(header_label)
                
                content_layout.addWidget(dungeon_header)
                
                if "error" in data:
                    error_widget = QWidget()
                    error_layout = QHBoxLayout(error_widget)
                    error_layout.setContentsMargins(5, 10, 5, 10)
                    
                    error_label = QLabel("錯誤: " + data["error"])
                    error_label.setStyleSheet("color: #FF5555;")
                    error_label.setFont(QFont("Noto Sans TC", 10))
                    error_layout.addWidget(error_label)
                    
                    content_layout.addWidget(error_widget)
                else:
                    best_runs = data.get("mythic_plus_best_runs", [])
                    recent_runs = data.get("mythic_plus_recent_runs", [])
                    
                    if best_runs:
                        dungeon_runs = {}
                        for run in best_runs:
                            dungeon_name = run["dungeon"]
                            if dungeon_name not in dungeon_runs:
                                dungeon_runs[dungeon_name] = []
                            dungeon_runs[dungeon_name].append(run)
                        
                        for dungeon_name, runs in dungeon_runs.items():
                            display_dungeon_name = DUNGEON_NAME_MAPPING.get(dungeon_name, dungeon_name)
                            best_run = max(runs, key=lambda x: x["mythic_level"])
                            formatted_time = DataFetcher.format_time(best_run["clear_time_ms"])
                            dungeon_score = best_run.get("score", "N/A")
                            keystone_upgrades = best_run.get("num_keystone_upgrades", 0)
                            if keystone_upgrades > 0:
                                keystone_text = f"✓ +{keystone_upgrades}"
                                keystone_color = "#67FD0A"
                            else:
                                keystone_text = "✗ 超時"
                                keystone_color = "#FF5555"
                            
                            dungeon_id = f"{char_id}_{dungeon_name.replace(' ', '_')}"
                            
                            dungeon_container = QWidget()
                            dungeon_container.setObjectName(f"dungeonContent_{dungeon_id}")
                            dungeon_container_layout = QVBoxLayout(dungeon_container)
                            dungeon_container_layout.setContentsMargins(0, 0, 0, 0)
                            dungeon_container_layout.setSpacing(0)
                            
                            run_widget = QWidget()
                            run_widget.setStyleSheet("background-color: #202830; border-radius: 4px; margin-bottom: 1px;")
                            run_layout = QHBoxLayout(run_widget)
                            run_layout.setContentsMargins(5, 8, 5, 8)
                            run_layout.setSpacing(0)
                            
                            detail_toggle = QToolButton()
                            is_detail_expanded = self.dungeon_expansion_states.get(dungeon_id, False)
                            detail_toggle.setText("▲" if is_detail_expanded else "▼")
                            detail_toggle.setStyleSheet("""
                                QToolButton {
                                    background-color: transparent;
                                    color: #999999;
                                    border: none;
                                    font-size: 12px;
                                    font-weight: bold;
                                }
                                QToolButton:hover {
                                    color: #FFFFFF;
                                }
                            """)
                            detail_toggle.setToolTip(f'<span style="color: #FFFFFF;">{"收起詳細紀錄" if is_detail_expanded else "展開詳細紀錄"}</span>')
                            detail_toggle.setObjectName(f"detailBtn_{dungeon_id}")
                            detail_toggle.clicked.connect(lambda checked, did=dungeon_id: self.toggle_dungeon_detail(did))
                            detail_toggle.setMinimumWidth(20)
                            detail_toggle.setMaximumWidth(20)
                            run_layout.addWidget(detail_toggle)
                            
                            name_label = QLabel(display_dungeon_name)
                            name_label.setStyleSheet("font-weight: bold;")
                            name_label.setFont(QFont("Noto Sans TC", 10))
                            name_label.setMinimumWidth(180)
                            name_label.setMaximumWidth(180)
                            run_layout.addWidget(name_label)
                            
                            level = best_run["mythic_level"]
                            level_label = QLabel(str(level))
                            level_color = self.get_level_color(level)
                            level_label.setStyleSheet(f"color: {level_color}; font-weight: bold; text-align: center;")
                            level_label.setFont(QFont("Noto Sans TC", 10))
                            level_label.setAlignment(Qt.AlignCenter)
                            level_label.setMinimumWidth(40)
                            level_label.setMaximumWidth(40)
                            run_layout.addWidget(level_label)
                            
                            score_label = QLabel(f"{dungeon_score:.1f}" if isinstance(dungeon_score, (int, float)) else str(dungeon_score))
                            score_color = self.get_score_color(dungeon_score) if isinstance(dungeon_score, (int, float)) else "#FFFFFF"
                            score_label.setStyleSheet(f"color: {score_color}; font-weight: bold; text-align: center;")
                            score_label.setFont(QFont("Noto Sans TC", 10))
                            score_label.setAlignment(Qt.AlignCenter)
                            score_label.setMinimumWidth(40)
                            score_label.setMaximumWidth(40)
                            run_layout.addWidget(score_label)
                            
                            keystone_label = QLabel(keystone_text)
                            keystone_label.setStyleSheet(f"color: {keystone_color}; font-weight: bold; text-align: center;")
                            keystone_label.setFont(QFont("Noto Sans TC", 10))
                            keystone_label.setAlignment(Qt.AlignCenter)
                            keystone_label.setMinimumWidth(40)
                            keystone_label.setMaximumWidth(40)
                            run_layout.addWidget(keystone_label)
                            
                            time_label = QLabel(formatted_time)
                            time_label.setStyleSheet("text-align: center;")
                            time_label.setFont(QFont("Noto Sans TC", 10))
                            time_label.setAlignment(Qt.AlignCenter)
                            time_label.setMinimumWidth(60)
                            time_label.setMaximumWidth(60)
                            run_layout.addWidget(time_label)
                            
                            date_label = QLabel(DataFetcher.format_datetime(best_run["completed_at"]))
                            date_label.setStyleSheet("text-align: center;")
                            date_label.setFont(QFont("Noto Sans TC", 10))
                            date_label.setAlignment(Qt.AlignCenter)
                            date_label.setMinimumWidth(120)
                            date_label.setMaximumWidth(120)
                            run_layout.addWidget(date_label)
                            
                            dungeon_container_layout.addWidget(run_widget)
                            
                            detail_frame = QFrame()
                            detail_frame.setObjectName(f"detailFrame_{dungeon_id}")
                            detail_frame.setStyleSheet("background-color: #1A2029; border-radius: 4px; margin-top: 1px;")
                            detail_frame.setVisible(is_detail_expanded)
                            
                            detail_layout = QVBoxLayout(detail_frame)
                            detail_layout.setContentsMargins(5, 5, 5, 5)
                            detail_layout.setSpacing(2)
                            
                            detail_title = QLabel("最近紀錄")
                            detail_title.setStyleSheet("color: #999999; font-size: 11px; margin-top: 2px;")
                            detail_title.setFont(QFont("Noto Sans TC", 10))
                            detail_layout.addWidget(detail_title)
                            
                            dungeon_recent_runs = [run for run in recent_runs if run["dungeon"] == dungeon_name]
                            dungeon_recent_runs = sorted(dungeon_recent_runs, key=lambda x: x["completed_at"], reverse=True)
                            
                            if dungeon_recent_runs:
                                for recent_run in dungeon_recent_runs:
                                    recent_widget = QWidget()
                                    recent_layout = QHBoxLayout(recent_widget)
                                    recent_layout.setContentsMargins(5, 8, 5, 8)
                                    recent_layout.setSpacing(0)
                                    
                                    # 空白佔位符，對應父節點的展開按鈕
                                    spacer_label = QLabel("")
                                    spacer_label.setMinimumWidth(20)
                                    spacer_label.setMaximumWidth(20)
                                    recent_layout.addWidget(spacer_label)
                                    
                                    # 空白佔位符，對應父節點的副本名稱欄
                                    spacer_label2 = QLabel("")
                                    spacer_label2.setMinimumWidth(180)
                                    spacer_label2.setMaximumWidth(180)
                                    recent_layout.addWidget(spacer_label2)
                                    
                                    # 層數欄，對應父節點的層數欄
                                    level_label = QLabel(str(recent_run["mythic_level"]))
                                    level_color = self.get_level_color(recent_run["mythic_level"])
                                    level_label.setStyleSheet(f"color: {level_color}; font-weight: bold; text-align: center;")
                                    level_label.setFont(QFont("Noto Sans TC", 10))
                                    level_label.setAlignment(Qt.AlignCenter)
                                    level_label.setMinimumWidth(40)
                                    level_label.setMaximumWidth(40)
                                    recent_layout.addWidget(level_label)
                                    
                                    # 空白佔位符，對應父節點的分數欄
                                    spacer_label3 = QLabel("")
                                    spacer_label3.setMinimumWidth(40)
                                    spacer_label3.setMaximumWidth(40)
                                    recent_layout.addWidget(spacer_label3)
                                    
                                    # 鑰石欄，對應父節點的鑰石欄
                                    keystone_upgrades = recent_run.get("num_keystone_upgrades", 0)
                                    if keystone_upgrades > 0:
                                        keystone_text = f"✓ +{keystone_upgrades}"
                                        keystone_color = "#67FD0A"
                                    else:
                                        keystone_text = "✗ 超時"
                                        keystone_color = "#FF5555"
                                    keystone_label = QLabel(keystone_text)
                                    keystone_label.setStyleSheet(f"color: {keystone_color}; font-weight: bold; text-align: center;")
                                    keystone_label.setFont(QFont("Noto Sans TC", 10))
                                    keystone_label.setAlignment(Qt.AlignCenter)
                                    keystone_label.setMinimumWidth(40)
                                    keystone_label.setMaximumWidth(40)
                                    recent_layout.addWidget(keystone_label)
                                    
                                    # 通關時間欄
                                    time_str = DataFetcher.format_time(recent_run.get("clear_time_ms", 0)) if "clear_time_ms" in recent_run else "未完成  "
                                    time_label = QLabel(time_str)
                                    time_label.setStyleSheet("text-align: center;")
                                    time_label.setFont(QFont("Noto Sans TC", 10))
                                    time_label.setAlignment(Qt.AlignCenter)
                                    time_label.setMinimumWidth(60)
                                    time_label.setMaximumWidth(60)
                                    recent_layout.addWidget(time_label)
                                    
                                    # 完成日期欄
                                    date_label = QLabel(DataFetcher.format_datetime(recent_run["completed_at"]))
                                    date_label.setStyleSheet("text-align: center;")
                                    date_label.setFont(QFont("Noto Sans TC", 10))
                                    date_label.setAlignment(Qt.AlignCenter)
                                    date_label.setMinimumWidth(120)
                                    date_label.setMaximumWidth(120)
                                    recent_layout.addWidget(date_label)
                                    
                                    detail_layout.addWidget(recent_widget)
                            else:
                                no_record = QLabel("無最近紀錄")
                                no_record.setStyleSheet("color: #999999; padding: 3px; text-align: center;")
                                no_record.setFont(QFont("Noto Sans TC", 10))
                                no_record.setAlignment(Qt.AlignCenter)
                                detail_layout.addWidget(no_record)
                            
                            dungeon_container_layout.addWidget(detail_frame)
                            content_layout.addWidget(dungeon_container)
                            
                            if dungeon_name != list(dungeon_runs.keys())[-1]:
                                separator = QFrame()
                                separator.setFrameShape(QFrame.HLine)
                                separator.setFrameShadow(QFrame.Sunken)
                                separator.setStyleSheet("background-color: #2A2F36; max-height: 1px;")
                                content_layout.addWidget(separator)
                    else:
                        no_record = QLabel("無紀錄")
                        no_record.setStyleSheet("color: #999999; padding: 10px; text-align: center;")
                        no_record.setFont(QFont("Noto Sans TC", 10))
                        no_record.setAlignment(Qt.AlignCenter)
                        content_layout.addWidget(no_record)
                
                char_layout.addWidget(content_frame)            
                self.scroll_layout.addWidget(char_widget)

            self.scroll_layout.addStretch()
        except Exception as e:
            error_message = f"發生錯誤: {str(e)}\n{traceback.format_exc()}"
            error_label = QLabel(error_message)
            error_label.setStyleSheet("color: #FF5555; padding: 20px;")
            error_label.setFont(QFont("Noto Sans TC", 10))
            self.clear_scroll_content()
            self.scroll_layout.addWidget(error_label)
            self.status_bar.showMessage("顯示資料時發生錯誤", 5000)

    def get_level_color(self, level):
        if level >= 20:
            return "#E16AFF"
        elif level >= 15:
            return "#4C97FC"
        elif level >= 10:
            return "#1CE2B2"
        elif level >= 5:
            return "#67FD0A"
        else:
            return "#FFFFFF"

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # 設置應用程式的全局圖標（包括工作列）
    icon_path = resource_path("icon.ico")
    print("應用程式圖標路徑:", icon_path)
    icon = QIcon(icon_path)
    if icon.isNull():
        print("應用程式圖標載入失敗:", icon_path)
    else:
        print("應用程式圖標載入成功:", icon_path)
    app.setWindowIcon(icon)

    font_db = QFontDatabase()
    font_path = resource_path("NotoSansTC-SemiBold.ttf")
    font_id = font_db.addApplicationFont(font_path)
    if font_id == -1:
        print("無法載入 Noto Sans TC SemiBold 字型")
    else:
        font_families = font_db.applicationFontFamilies(font_id)
        if font_families:
            app.setFont(QFont("Noto Sans TC", 10))

    window = RaiderIOMainWindow()
    window.show()
    sys.exit(app.exec_())
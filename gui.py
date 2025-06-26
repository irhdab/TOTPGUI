import sys
import json
import os
import time
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                            QListWidget, QProgressBar, QFrame, QMessageBox,
                            QFileDialog, QMenuBar, QMenu)
from PyQt6.QtCore import QTimer, Qt, QSettings
from PyQt6.QtGui import QFont, QAction
import pyotp
import qrcode
from PIL import Image

class TOTPApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.accounts = {}
        self.current_account = None
        self.current_totp_code = ""
        self.settings = QSettings("TOTP", "Settings")
        self.dark_mode = self.settings.value("dark_mode", False, type=bool)
        
        self.setWindowTitle("TOTP Authenticator")
        self.setFixedSize(400, 600)
        
        self.setup_menu()
        self.load_accounts()
        self.setup_ui()
        self.apply_styles()
        self.setup_timer()
    
    def setup_menu(self):
        menubar = self.menuBar()
        
        file_menu = menubar.addMenu("File")
        export_action = QAction("Export", self)
        export_action.triggered.connect(self.export_accounts)
        file_menu.addAction(export_action)
        
        import_action = QAction("Import", self)
        import_action.triggered.connect(self.import_accounts)
        file_menu.addAction(import_action)
        
        view_menu = menubar.addMenu("View")
        dark_action = QAction("Dark Mode", self)
        dark_action.setCheckable(True)
        dark_action.setChecked(self.dark_mode)
        dark_action.triggered.connect(self.toggle_dark_mode)
        view_menu.addAction(dark_action)
    
    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)
        
        
        # TOTP DISPLAY
        totp_frame = QFrame()
        totp_layout = QVBoxLayout(totp_frame)
        totp_layout.setContentsMargins(0, 0, 0, 0)
        
        # Account name
        self.account_label = QLabel("NO ACCOUNT SELECTED")
        self.account_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.account_label.setObjectName("accountLabel")
        self.account_label.setMinimumHeight(25)
        totp_layout.addWidget(self.account_label)
        
        # TOTP code
        self.totp_label = QLabel("000 000")
        self.totp_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.totp_label.setObjectName("totpCode")
        self.totp_label.setMinimumHeight(60)
        totp_layout.addWidget(self.totp_label)
        
        # Progress bar
        # Minimal progress indicator
        self.progress = QProgressBar()
        self.progress.setMaximum(30)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(3)
        totp_layout.addWidget(self.progress)
        
        # COPY BUTTON - GUARANTEED TO APPEAR
        self.copy_btn = QPushButton("COPY CODE")
        self.copy_btn.setObjectName("copyBtn")
        self.copy_btn.clicked.connect(self.copy_code)
        self.copy_btn.setMinimumHeight(45)
        self.copy_btn.setMaximumWidth(200)
        totp_layout.addWidget(self.copy_btn, 0, Qt.AlignmentFlag.AlignCenter)
        
        layout.addWidget(totp_frame)
        
        # ACCOUNTS
        accounts_header = QHBoxLayout()
        acc_label = QLabel("ACCOUNTS")
        acc_label.setObjectName("sectionLabel")
        accounts_header.addWidget(acc_label)
        accounts_header.addStretch()
        
        self.theme_btn = QPushButton("🌙" if not self.dark_mode else "☀")
        self.theme_btn.setObjectName("themeBtn")
        self.theme_btn.clicked.connect(self.toggle_dark_mode)
        self.theme_btn.setFixedSize(35, 35)
        accounts_header.addWidget(self.theme_btn)
        
        layout.addLayout(accounts_header)
        
        # Accounts list
        self.accounts_list = QListWidget()
        self.accounts_list.setObjectName("accountsList")
        self.accounts_list.itemClicked.connect(self.select_account)
        layout.addWidget(self.accounts_list)
        
        # INPUT SECTION
        input_frame = QFrame()
        input_frame.setObjectName("inputFrame")
        input_layout = QVBoxLayout(input_frame)
        input_layout.setSpacing(15)
        input_layout.setContentsMargins(20, 20, 20, 20)
        
        # Name input
        name_lbl = QLabel("ACCOUNT NAME")
        name_lbl.setObjectName("inputLabel")
        input_layout.addWidget(name_lbl)
        
        self.name_input = QLineEdit()
        self.name_input.setObjectName("textInput")
        self.name_input.setPlaceholderText("Enter account name")
        self.name_input.setFixedHeight(45)
        input_layout.addWidget(self.name_input)
        
        # Secret input
        secret_lbl = QLabel("SECRET KEY")
        secret_lbl.setObjectName("inputLabel")
        input_layout.addWidget(secret_lbl)
        
        self.secret_input = QLineEdit()
        self.secret_input.setObjectName("textInput")
        self.secret_input.setPlaceholderText("Enter secret key")
        self.secret_input.setFixedHeight(45)
        input_layout.addWidget(self.secret_input)
        
        # BUTTONS
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15)
        
        add_btn = QPushButton("ADD")
        add_btn.setObjectName("actionBtn")
        add_btn.clicked.connect(self.add_account)
        add_btn.setFixedHeight(45)
        
        del_btn = QPushButton("DELETE")
        del_btn.setObjectName("actionBtn")
        del_btn.clicked.connect(self.delete_account)
        del_btn.setFixedHeight(45)
        
        qr_btn = QPushButton("QR CODE")
        qr_btn.setObjectName("actionBtn")
        qr_btn.clicked.connect(self.generate_qr)
        qr_btn.setFixedHeight(45)
        
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(del_btn)
        btn_layout.addWidget(qr_btn)
        
        input_layout.addLayout(btn_layout)
        layout.addWidget(input_frame)
        
        self.update_accounts_list()
    
    def apply_styles(self):
        if self.dark_mode:
            bg_color = "#1a1a1a"
            text_color = "#ffffff"
            frame_bg = "#2a2a2a"
            border_color = "#404040"
            button_bg = "#ffffff"
            button_text = "#000000"
        else:
            bg_color = "#ffffff"
            text_color = "#000000"
            frame_bg = "#f8f8f8"
            border_color = "#e0e0e0"
            button_bg = "#000000"
            button_text = "#ffffff"
        
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {bg_color};
                color: {text_color};
            }}
            
            
            QLabel#sectionLabel {{
                font-family: '.AppleSystemUIFont', Helvetica, Arial, sans-serif;
                font-size: 15px;
                font-weight: bold;
                color: {text_color};
                letter-spacing: 1px;
            }}
            
            QLabel#accountLabel {{
                font-family: '.AppleSystemUIFont', Helvetica, Arial, sans-serif;
                font-size: 16px;
                font-weight: 500;
                color: {text_color};
                letter-spacing: 1px;
                padding: 5px;
                text-align: center;
            }}
            
            QLabel#totpCode {{
                font-family: Menlo, 'Courier New', monospace;
                font-size: 28px;
                color: {text_color};
                padding: 10px;
                text-align: center;
                border: none;
            }}
            
            QLabel#timeLabel {{
                font-family: '.AppleSystemUIFont', Helvetica, Arial, sans-serif;
                font-size: 13px;
                color: #888888;
                padding: 5px;
                text-align: center;
            }}
            
            QLabel#inputLabel {{
                font-family: '.AppleSystemUIFont', Helvetica, Arial, sans-serif;
                font-size: 12px;
                font-weight: bold;
                color: {text_color};
                letter-spacing: 1px;
                padding: 5px 0px;
            }}
            
            QFrame#totpFrame {{
                background-color: {frame_bg};
                border: 2px solid {border_color};
                border-radius: 15px;
                margin: 5px;
            }}
            
            QFrame#inputFrame {{
                background-color: {frame_bg};
                border: 1px solid {border_color};
                border-radius: 10px;
            }}
            
            QListWidget#accountsList {{
                background-color: {bg_color};
                border: none;
                border-top: 1px solid {border_color};
                font-family: '.AppleSystemUIFont', Helvetica, Arial, sans-serif;
                font-size: 13px;
                color: {text_color};
                padding: 5px;
            }}
            
            QListWidget#accountsList::item {{
                padding: 15px;
                border-bottom: 1px solid {border_color};
                border-radius: 5px;
                margin: 2px;
            }}
            
            QListWidget#accountsList::item:selected {{
                background-color: {button_bg};
                color: {button_text};
            }}
            
            QLineEdit#textInput {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                padding: 8px;
                font-family: Menlo, monospace;
                font-size: 13px;
                color: {text_color};
            }}
            
            QLineEdit#textInput:focus {{
                border: 2px solid {text_color};
            }}
            
            QPushButton#copyBtn {{
                background: transparent;
                color: {text_color};
                border: none;
                border-bottom: 2px solid {text_color};
                border-radius: 0;
                padding: 4px 8px;
                font-family: -apple-system, BlinkMacSystemFont, sans-serif;
                font-size: 12px;
            }}
            
            QPushButton#copyBtn:hover {{
                background-color: #555555;
                color: #ffffff;
            }}
            
            QPushButton#actionBtn {{
                background-color: {bg_color};
                color: {text_color};
                border: 1px solid {border_color};
                border-radius: 4px;
                padding: 6px 12px;
                font-family: '.AppleSystemUIFont', Helvetica, Arial, sans-serif;
                font-size: 13px;
                font-weight: bold;
                letter-spacing: 1px;
            }}
            
            QPushButton#actionBtn:hover {{
                background-color: {frame_bg};
            }}
            
            QPushButton#actionBtn:pressed {{
                background-color: {button_bg};
                color: {button_text};
            }}
            
            QPushButton#themeBtn {{
                background-color: {frame_bg};
                border: 1px solid {border_color};
                border-radius: 17px;
                font-size: 16px;
            }}
            
            QProgressBar#progress {{
                border: none;
                background-color: {text_color}40;
                height: 3px;
            }}
            
            QProgressBar#progress::chunk {{
                background-color: {text_color};
                border-radius: 4px;
            }}
        """)
    
    def toggle_dark_mode(self):
        self.dark_mode = not self.dark_mode
        self.settings.setValue("dark_mode", self.dark_mode)
        self.apply_styles()
        self.theme_btn.setText("🌙" if not self.dark_mode else "☀")
    
    def select_account(self, item):
        self.current_account = item.text()
        self.account_label.setText(self.current_account)
        self.update_totp_display()
    
    def add_account(self):
        name = self.name_input.text().strip().upper()
        secret = self.secret_input.text().strip()
        
        if not name or not secret:
            QMessageBox.warning(self, "Error", "Enter both name and secret")
            return
        
        if name in self.accounts:
            QMessageBox.warning(self, "Error", f"'{name}' already exists")
            return
        
        try:
            pyotp.TOTP(secret).now()
            self.accounts[name] = secret
            self.save_accounts()
            self.update_accounts_list()
            self.name_input.clear()
            self.secret_input.clear()
            QMessageBox.information(self, "Success", f"'{name}' added!")
        except:
            QMessageBox.critical(self, "Error", "Invalid secret key")
    
    def delete_account(self):
        current = self.accounts_list.currentItem()
        if not current:
            QMessageBox.warning(self, "Warning", "Select an account first")
            return
        
        name = current.text()
        reply = QMessageBox.question(self, "Confirm", f"Delete '{name}'?")
        
        if reply == QMessageBox.StandardButton.Yes:
            del self.accounts[name]
            self.save_accounts()
            self.update_accounts_list()
            
            if self.current_account == name:
                self.current_account = None
                self.account_label.setText("NO ACCOUNT SELECTED")
                self.totp_label.setText("000 000")
    
    def update_totp_display(self):
        if self.current_account and self.current_account in self.accounts:
            try:
                secret = self.accounts[self.current_account]
                totp = pyotp.TOTP(secret)
                code = totp.now()
                formatted = f"{code[:3]} {code[3:]}"
                self.totp_label.setText(formatted)
                self.current_totp_code = code
            except:
                self.totp_label.setText("ERROR")
                self.current_totp_code = ""
        
        current_time = time.time()
        remaining = 30 - (current_time % 30)
        self.progress.setValue(int(remaining))
        # Progress bar automatically shows remaining time visually
    
    def copy_code(self):
        if self.current_totp_code:
            QApplication.clipboard().setText(self.current_totp_code)
            original = self.copy_btn.text()
            self.copy_btn.setText("COPIED!")
            QTimer.singleShot(1500, lambda: self.copy_btn.setText(original))
        else:
            QMessageBox.warning(self, "No Code", "Select an account first")
    
    def generate_qr(self):
        name = self.name_input.text().strip()
        secret = self.secret_input.text().strip()
        
        if not name or not secret:
            QMessageBox.warning(self, "Error", "Enter name and secret")
            return
        
        try:
            totp = pyotp.TOTP(secret)
            uri = totp.provisioning_uri(name=name, issuer_name="TOTP")
            
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(uri)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            
            path, _ = QFileDialog.getSaveFileName(self, "Save QR", f"{name}_qr.png", "PNG (*.png)")
            if path:
                img.save(path)
                QMessageBox.information(self, "Success", "QR code saved!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed: {str(e)}")
    
    def export_accounts(self):
        if not self.accounts:
            QMessageBox.warning(self, "Warning", "No accounts to export")
            return
        
        path, _ = QFileDialog.getSaveFileName(self, "Export", "backup.json", "JSON (*.json)")
        if path:
            try:
                with open(path, 'w') as f:
                    json.dump(self.accounts, f, indent=2)
                QMessageBox.information(self, "Success", "Exported!")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed: {str(e)}")
    
    def import_accounts(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import", "", "JSON (*.json)")
        if path:
            try:
                with open(path, 'r') as f:
                    imported = json.load(f)
                
                added = 0
                for name, secret in imported.items():
                    if name not in self.accounts:
                        self.accounts[name] = secret
                        added += 1
                
                self.save_accounts()
                self.update_accounts_list()
                QMessageBox.information(self, "Success", f"Imported {added} accounts!")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed: {str(e)}")
    
    def update_accounts_list(self):
        self.accounts_list.clear()
        for name in sorted(self.accounts.keys()):
            self.accounts_list.addItem(name)
    
    def setup_timer(self):
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_totp_display)
        self.timer.start(1000)
    
    def save_accounts(self):
        try:
            with open("totp_accounts.json", "w") as f:
                json.dump(self.accounts, f, indent=2)
        except:
            pass
    
    def load_accounts(self):
        try:
            if os.path.exists("totp_accounts.json"):
                with open("totp_accounts.json", "r") as f:
                    self.accounts = json.load(f)
        except:
            self.accounts = {}
    
    def closeEvent(self, event):
        self.save_accounts()
        event.accept()

def main():
    app = QApplication(sys.argv)
    app.setFont(QFont(".AppleSystemUIFont", 11))
    
    window = TOTPApp()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()

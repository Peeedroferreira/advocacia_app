from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton,
    QMessageBox, QSpacerItem, QSizePolicy, QApplication, QDialog
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

# Importa AuthService diretamente se não for passado pelo app_controller,
# ou acessa via app_controller como no exemplo de login.
# Para consistência e melhor prática, vamos assumir que é acessado via app_controller.
# from services.auth_service import AuthService

class RegisterWindow_pyside(QDialog): # <--- NOME DA CLASSE CORRIGIDO
    def __init__(self, app_controller, parent=None):
        super().__init__(parent)
        self.app_controller = app_controller
        # self.auth_service = AuthService() # Usar self.app_controller.auth_service

        self.setWindowTitle("Criar Nova Conta - Sistema Advocacia")
        self.setMinimumSize(400, 380) # Ajustar altura se necessário
        self.resize(400, 380)
        # self.setModal(True)

        self.setStyleSheet("""
            QDialog {
                font-size: 14px;
                background-color: #f8f9fa;
            }
            QLabel#titleLabel {
                font-size: 20px;
                font-weight: bold;
                color: #333;
                margin-bottom: 10px;
            }
            QLineEdit {
                padding: 8px;
                border: 1px solid #ccc;
                border-radius: 4px;
                min-height: 25px;
            }
            QPushButton {
                padding: 10px;
                background-color: #28a745;
                color: white;
                border: none;
                border-radius: 4px;
                min-height: 25px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
            QPushButton:pressed {
                background-color: #1e7e34;
            }
        """)

        self.init_ui()
        self.center_window()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(15)

        title_label = QLabel("Criar Nova Conta")
        title_label.setObjectName("titleLabel")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title_label)

        self.username_entry = QLineEdit()
        self.username_entry.setPlaceholderText("Escolha um nome de usuário")
        main_layout.addWidget(self.username_entry)

        self.email_entry = QLineEdit() # Adicionado campo de e-mail
        self.email_entry.setPlaceholderText("Seu e-mail")
        main_layout.addWidget(self.email_entry)

        self.password_entry = QLineEdit()
        self.password_entry.setPlaceholderText("Digite sua senha")
        self.password_entry.setEchoMode(QLineEdit.EchoMode.Password)
        main_layout.addWidget(self.password_entry)

        self.confirm_password_entry = QLineEdit()
        self.confirm_password_entry.setPlaceholderText("Confirme sua senha")
        self.confirm_password_entry.setEchoMode(QLineEdit.EchoMode.Password)
        main_layout.addWidget(self.confirm_password_entry)

        main_layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        register_button = QPushButton("Registrar")
        register_button.clicked.connect(self.attempt_register)
        main_layout.addWidget(register_button)

        self.setLayout(main_layout)

    def attempt_register(self):
        username = self.username_entry.text().strip()
        email = self.email_entry.text().strip()
        password = self.password_entry.text()
        confirm_password = self.confirm_password_entry.text()


        if not username or not password or not confirm_password or not email:
            QMessageBox.warning(self, "Campos Obrigatórios", "Nome de usuário, e-mail, senha e confirmação de senha são obrigatórios.")
            return

        if password != confirm_password:
            QMessageBox.warning(self, "Senhas Diferentes", "As senhas digitadas não coincidem.")
            self.confirm_password_entry.clear()
            self.confirm_password_entry.setFocus()
            return

        if len(password) < 6:
            QMessageBox.warning(self, "Senha Fraca", "A senha deve ter pelo menos 6 caracteres.")
            return
        
        if "@" not in email or "." not in email: # Validação de e-mail um pouco melhor
            QMessageBox.warning(self, "E-mail Inválido", "Por favor, insira um endereço de e-mail válido.")
            return

        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        
        # Acessa o auth_service através do app_controller
        register_result = self.app_controller.auth_service.register(username, password, email)

        QApplication.restoreOverrideCursor()

        if register_result.get("success"):
            QMessageBox.information(self, "Registro Bem-sucedido", register_result.get("message", "Conta criada com sucesso! Agora você pode fazer login."))
            self.accept() 
        else:
            QMessageBox.critical(self, "Falha no Registro", register_result.get("message", "Não foi possível criar a conta."))

    def center_window(self):
        if self.parent():
            parent_geo = self.parent().geometry()
            self.move(parent_geo.center().x() - self.width() / 2,
                      parent_geo.center().y() - self.height() / 2)
        else:
            # Fallback se não houver pai, centraliza na tela
            screen_geo = self.screen().availableGeometry()
            center_point = screen_geo.center()
            self.move(center_point.x() - self.width() / 2, center_point.y() - self.height() / 2)

if __name__ == '__main__':
    import sys
    from services.auth_service import AuthService # Para o mock do AppController

    class MockAuthService:
        def register(self, username, password, email=None):
            print(f"MockAuthService: Tentando registrar usuário {username} com e-mail {email}")
            if username == "existente":
                return {"success": False, "message": "Este nome de usuário já existe."}
            return {"success": True, "message": "Conta criada com sucesso (simulação)!"}

    class MockAppController:
        def __init__(self):
            self.auth_service = MockAuthService()

    app = QApplication(sys.argv)
    mock_controller = MockAppController()
    # Passa None como pai, pois estamos testando standalone
    register_win = RegisterWindow_pyside(mock_controller, None) 
    register_win.show()
    sys.exit(app.exec())

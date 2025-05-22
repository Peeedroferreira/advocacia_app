from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QMessageBox, QSpacerItem, QSizePolicy, QApplication, QFrame
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QPalette, QColor

from services.auth_service import AuthService # Mantém o mesmo serviço de autenticação
# Importaremos a RegisterWindow_pyside quando ela for criada
# from .register_window_pyside import RegisterWindow_pyside


class LoginWindow(QWidget):
    def __init__(self, app_controller):
        super().__init__()
        self.app_controller = app_controller
        # Acessa o auth_service através do app_controller
        # self.auth_service = AuthService() # Removido, usar self.app_controller.auth_service
        self.register_window_instance = None # Para manter uma referência à janela de registro

        self.setWindowTitle("Login - Sistema Advocacia")
        self.setMinimumSize(400, 400) # Aumentar um pouco a altura para o novo botão
        self.resize(400, 400)

        self.setStyleSheet("""
            QWidget {
                font-size: 14px;
            }
            QLabel#titleLabel {
                font-size: 24px;
                font-weight: bold;
                color: #333; /* Cor escura para o título */
            }
            QLabel#subtitleLabel {
                font-size: 18px;
                color: #555; /* Cor um pouco mais clara para o subtítulo */
            }
            QLineEdit {
                padding: 8px;
                border: 1px solid #ccc;
                border-radius: 4px;
                min-height: 25px; /* Altura mínima */
            }
            QPushButton#loginButton { /* ID específico para o botão de login */
                padding: 10px;
                background-color: #0078D7; /* Azul similar ao do CustomTkinter */
                color: white;
                border: none;
                border-radius: 4px;
                min-height: 25px; /* Altura mínima */
            }
            QPushButton#loginButton:hover {
                background-color: #005A9E;
            }
            QPushButton#loginButton:pressed {
                background-color: #004C8A;
            }
            QPushButton#registerButton { /* ID específico para o botão de registro */
                padding: 8px; /* Padding um pouco menor para diferenciar */
                background-color: #6c757d; /* Cinza para o botão de registro */
                color: white;
                border: none;
                border-radius: 4px;
                min-height: 25px;
            }
            QPushButton#registerButton:hover {
                background-color: #5a6268;
            }
            QPushButton#registerButton:pressed {
                background-color: #545b62;
            }
        """)

        self.init_ui()
        self.center_window()

    def init_ui(self):
        main_layout = QVBoxLayout(self) # Layout principal para a janela
        main_layout.setContentsMargins(40, 40, 40, 40) # Margens maiores
        main_layout.setSpacing(15) # Espaçamento entre widgets

        # Título
        title_label = QLabel("Sistema de Advocacia")
        title_label.setObjectName("titleLabel") # Para QSS
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title_label)

        # Subtítulo
        subtitle_label = QLabel("Acessar Conta")
        subtitle_label.setObjectName("subtitleLabel") # Para QSS
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(subtitle_label)

        main_layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        # Campo de Usuário
        self.username_entry = QLineEdit()
        self.username_entry.setPlaceholderText("Usuário")
        main_layout.addWidget(self.username_entry)

        # Campo de Senha
        self.password_entry = QLineEdit()
        self.password_entry.setPlaceholderText("Senha")
        self.password_entry.setEchoMode(QLineEdit.EchoMode.Password)
        main_layout.addWidget(self.password_entry)

        # Bind Enter para login
        self.username_entry.returnPressed.connect(self.attempt_login)
        self.password_entry.returnPressed.connect(self.attempt_login)

        main_layout.addSpacerItem(QSpacerItem(20, 10, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)) # Espaço menor

        # Botão de Login
        login_button = QPushButton("Login")
        login_button.setObjectName("loginButton") # Aplicar ID para QSS
        login_button.clicked.connect(self.attempt_login)
        main_layout.addWidget(login_button)

        # Linha divisória (opcional, para separar visualmente os botões)
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        main_layout.addWidget(line)

        # Botão Criar Conta
        register_button = QPushButton("Criar Conta")
        register_button.setObjectName("registerButton") # Aplicar ID para QSS
        register_button.clicked.connect(self.open_register_window)
        main_layout.addWidget(register_button)

        main_layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        self.setLayout(main_layout)

    def attempt_login(self):
        username = self.username_entry.text()
        password = self.password_entry.text()

        if not username or not password:
            QMessageBox.warning(self, "Erro de Login", "Por favor, insira usuário e senha.")
            return

        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        # Usa o auth_service do app_controller
        login_result = self.app_controller.auth_service.login(username, password)
        QApplication.restoreOverrideCursor()

        if login_result.get("success"):
            user_data = login_result.get("user_data", {})
            self.app_controller.on_login_success(user_data)
        else:
            QMessageBox.critical(self, "Falha no Login", login_result.get("message", "Usuário ou senha inválidos."))
            self.password_entry.clear()
            self.password_entry.setFocus()

    def open_register_window(self):
        # Importa aqui para evitar dependência circular
        from .register_window_pyside import RegisterWindow_pyside

        # Verifica se já existe uma instância e a traz para frente, ou cria uma nova
        if self.register_window_instance is None or not self.register_window_instance.isVisible():
            # Passa o app_controller para a RegisterWindow_pyside
            self.register_window_instance = RegisterWindow_pyside(self.app_controller, self)
            self.register_window_instance.show()
        else:
            self.register_window_instance.activateWindow()
            self.register_window_instance.raise_()


    def center_window(self):
        screen_geo = self.screen().availableGeometry()
        center_point = screen_geo.center()
        self.move(center_point.x() - self.width() / 2, center_point.y() - self.height() / 2)

    def closeEvent(self, event):
        if self.register_window_instance and self.register_window_instance.isVisible():
            self.register_window_instance.close()

        if not self.app_controller.user_data:
            QApplication.quit()
        super().closeEvent(event)


if __name__ == '__main__':
    import sys
    # Mock AppController para teste standalone
    class MockAppController:
        def __init__(self):
            self.user_data = None
            self.app_instance = QApplication.instance() or QApplication(sys.argv)
            self.auth_service = AuthService() # AppController agora tem uma instância de AuthService

        def on_login_success(self, user_data):
            print(f"Login bem-sucedido com mock controller! Usuário: {user_data}")
            QMessageBox.information(None, "Login", "Login bem-sucedido (teste)!")
            if QApplication.instance():
                 QApplication.instance().quit()

        def screen(self):
            return QApplication.primaryScreen()


    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)

    mock_controller = MockAppController()
    login_win = LoginWindow(mock_controller)
    login_win.show()
    sys.exit(app.exec())

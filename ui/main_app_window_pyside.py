import os
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTabWidget, QMessageBox, QFrame, QApplication,
    QProgressDialog
)
from PySide6.QtGui import QAction, QIcon, QFont
from PySide6.QtCore import Qt, Slot, QTimer

from services.update_service import UpdateService # Mantido
from config.constants import CURRENT_APPLICATION_VERSION # Mantido

# Importação das abas reais
from .clients_tab_pyside import ClientsTab_pyside 
from .processes_tab_pyside import ProcessesTab_pyside # Nova importação

# Placeholders para outras abas (se você ainda as tiver como placeholders)
class PlaceholderTab(QWidget):
    def __init__(self, tab_name="Placeholder", api_service_param=None, parent=None): # Nome do param alterado
        super().__init__(parent)
        # self.api_service = api_service_param # Se o placeholder precisar do serviço
        layout = QVBoxLayout(self)
        label = QLabel(f"Conteúdo da Aba {tab_name} (PySide6 - A Implementar)")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setFont(QFont("Arial", 16))
        layout.addWidget(label)
        self.setLayout(layout)

class MainAppWindow(QMainWindow):
    def __init__(self, user_data, app_controller): # app_controller é passado
        super().__init__()
        self.user_data = user_data
        self.app_controller = app_controller # Armazena a instância do AppController
        
        # Aceder aos serviços de API através do app_controller
        self.client_api_service = self.app_controller.client_api_service 
        self.process_api_service = self.app_controller.process_api_service # Adicionado

        # Lógica do UpdateService
        if hasattr(self.app_controller, 'update_service') and self.app_controller.update_service is not None:
            self.update_service = self.app_controller.update_service
            self.update_service.parent_window = self 
        else:
            print("MainAppWindow: UpdateService não encontrado no AppController, criando novo.")
            self.update_service = UpdateService(parent_window=self)
            if self.app_controller: 
                 self.app_controller.update_service = self.update_service

        self.setWindowTitle("Sistema de Gerenciamento de Advocacia")
        self.setMinimumSize(1200, 800)
        self.resize(1200, 800)

        self.init_ui() 
        self.create_menus() 
        self.center_window()
        print("MainAppWindow: __init__ concluído.")
    
    def create_menus(self):
        menu_bar = self.menuBar()

        file_menu = menu_bar.addMenu("&Arquivo")
        exit_action = QAction("Sair", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.setStatusTip("Sair da aplicação")
        exit_action.triggered.connect(self.close_application_triggered) 
        file_menu.addAction(exit_action)

        help_menu = menu_bar.addMenu("&Ajuda")
        update_action = QAction("Verificar Atualizações...", self)
        update_action.triggered.connect(self.manual_update_check)
        help_menu.addAction(update_action)

        about_action = QAction("Sobre", self)
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)

    def init_ui(self):
        print("MainAppWindow: init_ui iniciado.")
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0,0,0,0) 
        main_layout.setSpacing(0)

        header_frame = QFrame(self) 
        header_frame.setFixedHeight(50)
        header_frame.setStyleSheet("background-color: #E0E0E0; border-bottom: 1px solid #C0C0C0;")
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(10,0,10,0)

        username_display = self.user_data.get('username')
        if not username_display and isinstance(self.user_data.get('user_data'), dict): 
            username_display = self.user_data['user_data'].get('username', "Usuário")
        elif not username_display:
            username_display = "Usuário"

        welcome_label = QLabel(f"Bem-vindo(a), {username_display}!")
        welcome_label.setFont(QFont("Arial", 12)) 
        header_layout.addWidget(welcome_label)
        header_layout.addStretch()

        logout_button = QPushButton("Logout")
        logout_button.setFixedWidth(100)
        logout_button.clicked.connect(self.handle_logout)
        header_layout.addWidget(logout_button)
        main_layout.addWidget(header_frame)

        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #C0C0C0; top: -1px; background-color: white;}
            QTabBar::tab { background: #E0E0E0; border: 1px solid #C0C0C0; 
                           border-bottom-color: #C0C0C0; 
                           border-top-left-radius: 4px;
                           border-top-right-radius: 4px;
                           min-width: 120px; 
                           padding: 8px;
                           font-size: 14px; 
                         }
            QTabBar::tab:selected { background: white; margin-bottom: -1px; }
            QTabBar::tab:!selected:hover { background: #D0D0D0; }
        """)

        user_id_for_tabs = username_display 
        if user_id_for_tabs == "Usuário" or not user_id_for_tabs : 
            QMessageBox.critical(self, "Erro Crítico de Usuário", "ID do usuário não pôde ser determinado para carregar as abas.")
            return

        # Verificar se os serviços de API estão definidos
        if not self.client_api_service:
            QMessageBox.critical(self, "Erro Crítico de API", "Serviço de API de Cliente não inicializado.")
            print("MainAppWindow: ERRO - client_api_service é None em init_ui.")
            return
        if not self.process_api_service: # Adicionada verificação para process_api_service
            QMessageBox.critical(self, "Erro Crítico de API", "Serviço de API de Processos não inicializado.")
            print("MainAppWindow: ERRO - process_api_service é None em init_ui.")
            return
            
        # Aba de Clientes
        print(f"MainAppWindow: Instanciando ClientsTab_pyside com user_id: {user_id_for_tabs}")
        self.clients_tab = ClientsTab_pyside(user_id_for_tabs, self.client_api_service, self.tab_widget)
        self.tab_widget.addTab(self.clients_tab, "Clientes")

        # Aba de Processos (Nova)
        print(f"MainAppWindow: Instanciando ProcessesTab_pyside com user_id: {user_id_for_tabs}")
        self.processes_tab = ProcessesTab_pyside(user_id_for_tabs, self.process_api_service, self.client_api_service, self.tab_widget)
        self.tab_widget.addTab(self.processes_tab, "Processos")
        
        # Adicionar outras abas (Demandas, Audiências) como placeholders ou implementações reais
        # self.demands_tab = PlaceholderTab("Demandas", api_service_param=None, parent=self.tab_widget) # Ajustar se precisar de API
        # self.tab_widget.addTab(self.demands_tab, "Demandas")
        # self.hearings_tab = PlaceholderTab("Audiências", api_service_param=None, parent=self.tab_widget) # Ajustar se precisar de API
        # self.tab_widget.addTab(self.hearings_tab, "Audiências")
        
        main_layout.addWidget(self.tab_widget)
        print("MainAppWindow: init_ui concluído com sucesso.")

    @Slot()
    def manual_update_check(self):
        if self.update_service:
            self.update_service.parent_window = self 
            self.update_service.check_for_updates(is_manual_check=True)
        else:
            QMessageBox.warning(self, "Erro de Atualização", "Serviço de atualização não está disponível.")

    def show_about_dialog(self):
        QMessageBox.about(self, "Sobre o Sistema de Advocacia",
                          f"Sistema de Gerenciamento para Escritórios de Advocacia\n"
                          f"Versão: {CURRENT_APPLICATION_VERSION}\n\n"
                          "Desenvolvido por [Seu Nome/Empresa]")

    def handle_logout(self): 
        reply = QMessageBox.question(self, "Logout",
                                     "Tem certeza que deseja sair?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            if self.app_controller:
                self.app_controller.logout() 
            else: 
                print("MainAppWindow: Erro - app_controller não definido para logout.")
                self.close()

    def center_window(self):
        primary_screen = QApplication.primaryScreen()
        if primary_screen:
            screen_geo = primary_screen.availableGeometry()
            center_point = screen_geo.center()
            self.move(center_point.x() - self.width() / 2, center_point.y() - self.height() / 2)

    def close_application_triggered(self):
        self.close() 

    def closeEvent(self, event):
        print("MainAppWindow: closeEvent chamado.")
        app_instance = QApplication.instance()
        if app_instance:
            print("MainAppWindow: Encerrando a aplicação via QApplication.quit().")
            app_instance.quit() 
        super().closeEvent(event) 

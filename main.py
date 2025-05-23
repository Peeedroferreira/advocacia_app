import sys
import os
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtGui import QIcon

from ui.login_window_pyside import LoginWindow
from ui.main_app_window_pyside import MainAppWindow 
from services.auth_service import AuthService 
from services.update_service import UpdateService 
from config.constants import CURRENT_APPLICATION_VERSION 
from services.client_api_service import ClientApiService
from services.process_api_service import ProcessApiService 
from services.hearings_api_service import HearingsApiService # Nova importação
# A linha abaixo foi mantida conforme o seu código, mas atenção ao seu uso.
# from services.dynamodb_client_handler import DynamoDBClientHandler 

class AppController(QApplication):
    def __init__(self, argv):
        super().__init__(argv)
        self.user_data = None
        self.auth_token = None 
        self.login_window = None
        self.main_app_window = None

        # --- Serviços ---
        self.auth_service = AuthService()
        
        # self.dynamodb_client_handler = DynamoDBClientHandler() # Comentado, pois o ideal é via API
        
        self.client_api_service = None 
        self.process_api_service = None 
        self.hearings_api_service = None # Novo serviço de audiências
        self.update_service = None 

        self.setApplicationName("Sistema Advocacia")
        self.setApplicationVersion(CURRENT_APPLICATION_VERSION)

        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "icon.ico")
        if not os.path.exists(icon_path) and hasattr(sys, '_MEIPASS'):
            icon_path = os.path.join(sys._MEIPASS, "assets", "icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        else:
            print(f"Arquivo de ícone não encontrado em: {icon_path}")
            alt_icon_path = os.path.join("assets", "icon.ico") 
            if os.path.exists(alt_icon_path):
                 self.setWindowIcon(QIcon(alt_icon_path))
            else:
                 print(f"Tentativa alternativa de ícone também falhou: {alt_icon_path}")

        self.show_login_window()

    def show_login_window(self):
        if self.main_app_window and self.main_app_window.isVisible():
            self.main_app_window.close() 
            self.main_app_window = None 
        
        self.login_window = LoginWindow(self)
        self.login_window.show()

    def on_login_success(self, user_data_from_auth): 
        self.user_data = user_data_from_auth 
        
        token_found = False
        if isinstance(self.user_data, dict):
            if 'token' in self.user_data:
                self.auth_token = self.user_data.get('token')
                token_found = True
            elif 'user_data' in self.user_data and isinstance(self.user_data.get('user_data'), dict):
                user_details_dict = self.user_data.get('user_data', {})
                if 'token' in user_details_dict:
                    self.auth_token = user_details_dict.get('token')
                    token_found = True
        
        if not token_found or not self.auth_token:
            self.auth_token = None 
            print("AppController: ERRO CRÍTICO - Token de autenticação não encontrado na resposta do login.")
            QMessageBox.critical(None, "Erro de Login", 
                                 "Token de autenticação não foi retornado pelo servidor após o login.\n"
                                 "A aplicação não pode prosseguir sem autenticação para a API.")
            return 

        username_display = "N/A"
        if isinstance(self.user_data, dict):
            username_display = self.user_data.get('username')
            if not username_display and isinstance(self.user_data.get('user_data'), dict):
                username_display = self.user_data.get('user_data', {}).get('username', "N/A")
        
        print(f"AppController: Usuário '{username_display}' logado com sucesso.")
        print(f"AppController: Token de autenticação recebido e armazenado.")
        
        # Instanciar os serviços de API com o token
        self.client_api_service = ClientApiService(auth_token=self.auth_token)
        print("AppController: ClientApiService instanciado.")
        self.process_api_service = ProcessApiService(auth_token=self.auth_token)
        print("AppController: ProcessApiService instanciado.")
        self.hearings_api_service = HearingsApiService(auth_token=self.auth_token) # Instancia o novo serviço
        print("AppController: HearingsApiService instanciado.")
        
        if self.login_window:
            self.login_window.close()
            self.login_window = None 
        
        self.show_main_app_window() 
        
        if self.main_app_window:
            if not self.update_service: 
                self.update_service = UpdateService(parent_window=self.main_app_window)
            
            if self.update_service.is_update_check_due():
                print("AppController: Verificação de atualização automática devida, iniciando...")
                self.update_service.check_for_updates(is_manual_check=False) 
            else:
                print("AppController: Verificação de atualização automática não é devida no momento.")

    def show_main_app_window(self):
        # Verifica se os serviços de API foram instanciados
        if not self.user_data or not self.client_api_service or not self.process_api_service or not self.hearings_api_service: 
            print("AppController: Não é possível mostrar a janela principal. Dados do usuário ou serviços de API não estão prontos.")
            # Poderia mostrar uma mensagem de erro para o usuário aqui também ou tentar relogar.
            # Por agora, apenas não abre a janela principal se algo essencial faltar.
            if not self.login_window or not self.login_window.isVisible(): # Evita abrir login sobre login
                QMessageBox.critical(None, "Erro Crítico de Inicialização", 
                                     "Falha ao inicializar componentes essenciais da aplicação após o login.\n"
                                     "Por favor, tente reiniciar a aplicação ou contate o suporte.")
                self.logout() # Faz logout para tentar um novo ciclo de login
            return
        
        self.main_app_window = MainAppWindow(self.user_data, self) 
        self.main_app_window.show()
        print("AppController: MainAppWindow exibida.")

    def logout(self):
        self.user_data = None
        self.auth_token = None
        self.client_api_service = None 
        self.process_api_service = None 
        self.hearings_api_service = None # Limpar HearingsApiService
        print("AppController: Usuário deslogado.")
        if self.main_app_window:
            self.main_app_window.close() 
            self.main_app_window = None 
        self.show_login_window()

if __name__ == "__main__":
    # Garante que o diretório do projeto esteja no sys.path
    # Isso é útil se você executar main.py diretamente de dentro de advocacia_app/
    project_dir = os.path.dirname(os.path.abspath(__file__))
    if project_dir not in sys.path:
        sys.path.insert(0, project_dir)
    
    # Garante que a pasta 'assets' exista
    assets_dir = os.path.join(project_dir, "assets") 
    os.makedirs(assets_dir, exist_ok=True)
    
    app = AppController(sys.argv)
    sys.exit(app.exec())

import requests
import json
import os
import sys
import subprocess
import shutil
import configparser
from datetime import datetime, timedelta
from packaging.version import parse as parse_version

from PySide6.QtCore import QThread, Signal as PySideSignal, Slot, QTimer, Qt
from PySide6.QtWidgets import (
    QMessageBox, QProgressDialog, QApplication,
    QWidget, QVBoxLayout, QPushButton
)

# Importar constantes do novo ficheiro
# Este import assume que a pasta 'advocacia_app' está no PYTHONPATH
# ou que o script é executado de uma forma que permite este tipo de importação.
# Se main.py está em 'advocacia_app/', e 'config' e 'services' são subpastas,
# o import deve ser 'from config.constants import ...'
try:
    from config.constants import (
        CURRENT_APPLICATION_VERSION,
        VERSION_INFO_URL,
        CONFIG_FILE_NAME,
        CONFIG_SECTION_UPDATE,
        CONFIG_KEY_LAST_CHECK
    )
except ImportError: # Fallback se executado de forma isolada ou com problemas de path
    print("ALERTA CRÍTICO em update_service.py: Não foi possível importar 'constants.py' de 'config'.")
    print("Usando valores de fallback. A funcionalidade de atualização pode não funcionar corretamente.")
    CURRENT_APPLICATION_VERSION = "0.0.0"
    VERSION_INFO_URL = "NOT_CONFIGURED_PLEASE_CHECK_CONSTANTS_PY"
    CONFIG_FILE_NAME = "app_config_fallback.ini"
    CONFIG_SECTION_UPDATE = "UpdateSettings"
    CONFIG_KEY_LAST_CHECK = "last_update_check_timestamp"

class ConfigManager:
    def __init__(self, config_file_name=CONFIG_FILE_NAME):
        if getattr(sys, 'frozen', False): # Aplicação compilada
            base_path = os.path.dirname(sys.executable)
        else: # Script Python
            # Tenta obter o diretório do script principal da aplicação (onde main.py reside)
            # Assumindo que main.py está na raiz do projeto (ex: 'advocacia_app/')
            # e este ficheiro (update_service.py) está em 'advocacia_app/services/'
            current_file_dir = os.path.dirname(os.path.abspath(__file__))
            base_path = os.path.dirname(current_file_dir) # Sobe um nível para 'advocacia_app/'
            # Se a estrutura for diferente, este base_path pode precisar de ajuste.
            # Uma forma mais robusta se QApplication já existe:
            # app_instance = QApplication.instance()
            # if app_instance and hasattr(app_instance, 'applicationDirPath'):
            #    base_path = app_instance.applicationDirPath()

        self.config_file_path = os.path.join(base_path, config_file_name)
        print(f"ConfigManager: Caminho do ficheiro de configuração: {self.config_file_path}")

        self.config = configparser.ConfigParser()
        self._load_or_create_config()

    def _load_or_create_config(self):
        """Lê a configuração ou cria o ficheiro com padrões se não existir/for inválido."""
        try:
            if not os.path.exists(self.config_file_path):
                print(f"ConfigManager: Ficheiro de configuração não encontrado, criando em {self.config_file_path}")
                self._create_default_config()
            else:
                self.config.read(self.config_file_path)
                if not self.config.has_section(CONFIG_SECTION_UPDATE):
                    print(f"ConfigManager: Seção [{CONFIG_SECTION_UPDATE}] não encontrada, adicionando.")
                    self.config.add_section(CONFIG_SECTION_UPDATE)
                    # Garante que a chave existe se a seção foi recém-adicionada a um ficheiro existente
                    if not self.config.has_option(CONFIG_SECTION_UPDATE, CONFIG_KEY_LAST_CHECK):
                        self.config.set(CONFIG_SECTION_UPDATE, CONFIG_KEY_LAST_CHECK, "0.0")
                    self._save_config()
        except configparser.Error as e:
            print(f"ConfigManager: Erro ao ler o ficheiro de configuração {self.config_file_path}: {e}. Recriando.")
            self._create_default_config()

    def _create_default_config(self):
        self.config = configparser.ConfigParser() # Garante que está limpo
        self.config.add_section(CONFIG_SECTION_UPDATE)
        self.config.set(CONFIG_SECTION_UPDATE, CONFIG_KEY_LAST_CHECK, "0.0")
        self._save_config()

    def _save_config(self):
        try:
            os.makedirs(os.path.dirname(self.config_file_path), exist_ok=True)
            with open(self.config_file_path, 'w') as f:
                self.config.write(f)
            print(f"ConfigManager: Configuração salva em {self.config_file_path}")
        except Exception as e:
            print(f"Erro ao salvar o ficheiro de configuração {self.config_file_path}: {e}")

    def get_last_check_timestamp(self) -> float:
        try:
            self._load_or_create_config() # Garante que a config está carregada/existe
            return self.config.getfloat(CONFIG_SECTION_UPDATE, CONFIG_KEY_LAST_CHECK)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            print(f"Chave '{CONFIG_KEY_LAST_CHECK}' não encontrada ou inválida na seção '{CONFIG_SECTION_UPDATE}'. Resetando.")
            self._create_default_config() # Recria se a chave estiver em falta após carregar
            return 0.0
        except Exception as e:
            print(f"ConfigManager: Erro inesperado ao obter last_check_timestamp: {e}. Resetando para padrão.")
            self._create_default_config()
            return 0.0

    def set_last_check_timestamp(self, timestamp: float = None):
        if timestamp is None:
            timestamp = datetime.now().timestamp()
        self._load_or_create_config() # Garante que a seção existe
        self.config.set(CONFIG_SECTION_UPDATE, CONFIG_KEY_LAST_CHECK, str(timestamp))
        self._save_config()

class UpdateWorker(QThread):
    # ... (código do UpdateWorker permanece o mesmo da versão anterior no Canvas) ...
    check_finished = PySideSignal(object)
    download_progress = PySideSignal(int)
    download_finished = PySideSignal(str, str) # (path, version) or (None, None)
    error_occurred = PySideSignal(str)

    def __init__(self, task, url=None, version_str=None, parent=None):
        super().__init__(parent)
        self.task = task
        self.url = url
        self.version_str = version_str
        self.was_error_emitted_flag = False

    def run(self):
        self.was_error_emitted_flag = False
        if self.task == "check":
            self._check_for_updates_task()
        elif self.task == "download":
            self._download_update_task()

    def _emit_error(self, message):
        if not self.was_error_emitted_flag:
            self.error_occurred.emit(message)
            self.was_error_emitted_flag = True

    def _check_for_updates_task(self):
        try:
            if "SEU_USUARIO_GITHUB" in VERSION_INFO_URL or "SEU_REPOSITORIO" in VERSION_INFO_URL or VERSION_INFO_URL == "NOT_CONFIGURED":
                 print("ALERTA: VERSION_INFO_URL não foi configurada corretamente em config/constants.py.")
                 self._emit_error("Configuração de URL de atualização pendente.")
                 self.check_finished.emit(None)
                 return

            print(f"Worker: Verificando atualizações em: {VERSION_INFO_URL}")
            response = requests.get(VERSION_INFO_URL, timeout=15)
            response.raise_for_status()
            latest_version_info = response.json()
            print(f"Worker: Informação da versão recebida: {latest_version_info}")
            self.check_finished.emit(latest_version_info)
        except requests.exceptions.Timeout:
            print(f"Worker: Timeout ao verificar atualizações.")
            self._emit_error("Tempo esgotado ao buscar informações de versão.")
            self.check_finished.emit(None)
        except requests.exceptions.RequestException as e:
            print(f"Worker: Erro na requisição ao verificar atualizações: {e}")
            self._emit_error(f"Erro de rede ao buscar informações de versão: {str(e)}")
            self.check_finished.emit(None)
        except json.JSONDecodeError as e:
            print(f"Worker: Erro ao decodificar JSON da versão: {e}")
            self._emit_error("Formato inválido das informações de versão do servidor.")
            self.check_finished.emit(None)
        except Exception as e:
            print(f"Worker: Erro inesperado ao verificar atualizações: {e}")
            self._emit_error(f"Ocorreu um erro inesperado ao verificar atualizações: {str(e)}")
            self.check_finished.emit(None)

    def _download_update_task(self):
        if not self.url or not self.version_str:
            self._emit_error("Informações de download não configuradas para o worker.")
            self.download_finished.emit(None, None)
            return

        temp_filename = f"AdvocaciaApp_v{self.version_str}_update_temp"
        if sys.platform == "win32": temp_filename += ".exe"
        elif sys.platform == "darwin": temp_filename += ".dmg"
        
        try:
            app_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.getcwd()
            download_path = os.path.join(app_dir, temp_filename)
        except Exception:
            download_path = os.path.join(os.getcwd(), temp_filename)

        try:
            print(f"Worker: Baixando atualização de: {self.url} para {download_path}")
            self.download_progress.emit(0)
            with requests.get(self.url, stream=True, timeout=300) as r:
                r.raise_for_status()
                total_size = int(r.headers.get('content-length', 0))
                bytes_downloaded = 0
                with open(download_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            bytes_downloaded += len(chunk)
                            if total_size > 0:
                                self.download_progress.emit(int((bytes_downloaded / total_size) * 100))
            self.download_progress.emit(100)
            print("Worker: Download concluído.")
            self.download_finished.emit(download_path, self.version_str)
        except Exception as e:
            print(f"Worker: Erro durante o download: {e}")
            self._emit_error(f"Erro durante o download: {str(e)}")
            self.download_finished.emit(None, None)


class UpdateService:
    def __init__(self, parent_window=None):
        self.parent_window = parent_window
        self.config_manager = ConfigManager()
        self.update_check_worker = None
        self.update_download_worker = None
        self.progress_dialog = None
        self.latest_version_info_cache = None

    def is_update_check_due(self, hours_interval=24) -> bool:
        last_check_ts = self.config_manager.get_last_check_timestamp()
        print(f"UpdateService: Última verificação em timestamp: {last_check_ts}")
        if last_check_ts == 0.0: # Nunca verificado ou erro ao ler config
            print("UpdateService: Verificação devida (nunca verificada ou config resetada).")
            return True
        
        last_check_dt = datetime.fromtimestamp(last_check_ts)
        current_dt = datetime.now()
        is_due = current_dt - last_check_dt > timedelta(hours=hours_interval)
        print(f"UpdateService: Última verificação em: {last_check_dt}, Agora: {current_dt}, Intervalo: {hours_interval}h. Devida? {is_due}")
        return is_due

    def check_for_updates(self, is_manual_check=False):
        if self.update_check_worker and self.update_check_worker.isRunning():
            if is_manual_check and self.parent_window:
                QMessageBox.warning(self.parent_window, "Aviso", "Verificação de atualização já está em progresso.")
            return

        # Para verificações automáticas no login, não mostramos o diálogo "A verificar..."
        # O feedback só será dado se uma atualização for encontrada.
        if is_manual_check and self.parent_window:
            QMessageBox.information(self.parent_window, "Verificar Atualizações", 
                                    "A verificar atualizações online, por favor aguarde...")
        
        parent_for_worker = self.parent_window if self.parent_window else QApplication.instance()
        self.update_check_worker = UpdateWorker(task="check", parent=parent_for_worker)
        self.update_check_worker.check_finished.connect(
            lambda info: self._handle_update_check_result(info, is_manual_check)
        )
        self.update_check_worker.error_occurred.connect(self._handle_update_error)
        self.update_check_worker.start()
        
        # Importante: Para verificações automáticas (is_manual_check=False),
        # o timestamp é atualizado AGORA, antes da chamada de rede.
        # Isto previne verificações repetidas em logins rápidos se a primeira falhar por rede.
        # Para verificações manuais, o timestamp é atualizado DEPOIS, em _handle_update_check_result.
        if not is_manual_check:
             print("UpdateService: Verificação automática iniciada, atualizando timestamp da última verificação.")
             self.config_manager.set_last_check_timestamp()


    @Slot(object, bool)
    def _handle_update_check_result(self, version_info, is_manual_check):
        if is_manual_check: # Atualiza timestamp para verificações manuais também, após a conclusão
            print("UpdateService: Verificação manual concluída, atualizando timestamp.")
            self.config_manager.set_last_check_timestamp()

        if version_info is None: # Erro já foi tratado e emitido pelo worker
            return

        self.latest_version_info_cache = version_info
        latest_version_str = version_info.get("version")
        download_url = version_info.get("download_url")

        print(f"Service: Versão atual: {CURRENT_APPLICATION_VERSION}, Versão mais recente: {latest_version_str}")

        if not latest_version_str or not download_url:
            if is_manual_check and self.parent_window:
                QMessageBox.critical(self.parent_window, "Erro de Atualização", 
                                     "Informações de versão inválidas recebidas do servidor.")
            return
        
        try:
            if parse_version(latest_version_str) > parse_version(CURRENT_APPLICATION_VERSION):
                # Para verificações automáticas, só pergunta se houver atualização
                self._prompt_for_download(latest_version_str, download_url)
            elif is_manual_check and self.parent_window: # Só informa "atualizado" se for manual
                QMessageBox.information(self.parent_window, "Atualizado", 
                                        "Você já está com a versão mais recente.")
        except Exception as e:
            print(f"Service: Erro ao comparar versões: {e}")
            if is_manual_check and self.parent_window:
                QMessageBox.critical(self.parent_window, "Erro de Versão", 
                                     f"Formato de versão inválido ou erro na comparação: {e}")
    
    def _prompt_for_download(self, latest_version_str, download_url):
        if not self.parent_window: # Não pode mostrar diálogo sem janela pai
            print(f"Atualização {latest_version_str} disponível, mas sem janela pai para perguntar.")
            return

        reply = QMessageBox.question(self.parent_window, "Atualização Disponível",
                                     f"Uma nova versão ({latest_version_str}) está disponível!\n"
                                     f"Sua versão atual é {CURRENT_APPLICATION_VERSION}.\n\n"
                                     "Deseja baixar a atualização agora?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.Yes)
        if reply == QMessageBox.StandardButton.Yes:
            self._start_download(download_url, latest_version_str)
        else:
            print("Usuário recusou a atualização.")

    def _start_download(self, download_url, new_version_str):
        if self.update_download_worker and self.update_download_worker.isRunning():
            if self.parent_window:
                QMessageBox.warning(self.parent_window, "Download", "Um download já está em progresso.")
            return

        if self.parent_window:
            self.progress_dialog = QProgressDialog("A baixar atualização...", "Cancelar", 0, 100, self.parent_window)
            self.progress_dialog.setWindowTitle("Progresso do Download")
            self.progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
            self.progress_dialog.setAutoClose(False)
            self.progress_dialog.setAutoReset(False)
            self.progress_dialog.canceled.connect(self.cancel_download)
            self.progress_dialog.setValue(0)
            self.progress_dialog.show()
        
        parent_for_worker = self.parent_window if self.parent_window else QApplication.instance()
        self.update_download_worker = UpdateWorker(task="download", url=download_url, version_str=new_version_str, parent=parent_for_worker)
        self.update_download_worker.download_progress.connect(self._update_download_progress_ui)
        self.update_download_worker.download_finished.connect(self._handle_download_finished_ui)
        self.update_download_worker.error_occurred.connect(self._handle_update_error)
        
        self.update_download_worker.start()

    @Slot()
    def cancel_download(self):
        if self.update_download_worker and self.update_download_worker.isRunning():
            print("Download cancelado pelo usuário.")
            self.update_download_worker.quit() 
            self.update_download_worker.wait() 
        if self.progress_dialog:
            self.progress_dialog.close()
            self.progress_dialog = None

    @Slot(int)
    def _update_download_progress_ui(self, progress_percentage):
        if self.progress_dialog:
            self.progress_dialog.setValue(progress_percentage)

    @Slot(str, str) 
    def _handle_download_finished_ui(self, downloaded_file_path, new_version):
        if self.progress_dialog:
            self.progress_dialog.setValue(100)
            self.progress_dialog.close()
            self.progress_dialog = None
        
        if downloaded_file_path and new_version:
            if self.parent_window:
                QMessageBox.information(self.parent_window, "Download Concluído",
                                        f"Atualização para a versão {new_version} baixada com sucesso!\n"
                                        f"Ficheiro: {downloaded_file_path}\n\n"
                                        "A aplicação tentará aplicar a atualização e reiniciar.")
            self._attempt_self_replace(downloaded_file_path)
        else:
            if not (self.update_download_worker and self.update_download_worker.was_error_emitted_flag):
                 if self.parent_window:
                    QMessageBox.critical(self.parent_window, "Falha no Download", "O download da atualização falhou.")

    def _attempt_self_replace(self, downloaded_file_path):
        # ... (lógica de _attempt_self_replace permanece a mesma) ...
        try:
            current_exe_path = sys.executable
            if not getattr(sys, 'frozen', False): 
                if self.parent_window:
                    QMessageBox.information(self.parent_window, "Modo de Script",
                                            "A aplicação está a ser executada como script Python.\n"
                                            "A substituição automática não é suportada neste modo.\n"
                                            f"Novo ficheiro baixado em: {downloaded_file_path}")
                return

            old_exe_path = current_exe_path + ".old"
            
            print(f"Caminho do executável atual: {current_exe_path}")
            print(f"Caminho do ficheiro baixado: {downloaded_file_path}")

            if os.path.exists(old_exe_path):
                print(f"Removendo backup antigo: {old_exe_path}")
                os.remove(old_exe_path)
            print(f"Renomeando {current_exe_path} para {old_exe_path}")
            os.rename(current_exe_path, old_exe_path)
            
            print(f"Movendo {downloaded_file_path} para {current_exe_path}")
            shutil.move(downloaded_file_path, current_exe_path)
            
            if sys.platform != "win32":
                print(f"Definindo permissões de execução para {current_exe_path}")
                os.chmod(current_exe_path, 0o755)

            if self.parent_window:
                QMessageBox.information(self.parent_window, "Atualização Aplicada", 
                                        "A atualização foi aplicada. A aplicação será reiniciada agora.")
            
            app_instance = QApplication.instance()
            if app_instance:
                QTimer.singleShot(200, lambda p=current_exe_path: self._restart_app(p))
        except Exception as e:
            print(f"Erro ao tentar aplicar a atualização automaticamente: {e}")
            import traceback
            traceback.print_exc()
            if self.parent_window:
                QMessageBox.warning(self.parent_window, "Erro na Atualização",
                                    f"Erro ao tentar aplicar a atualização: {e}\n"
                                    f"Por favor, substitua manualmente o ficheiro em '{sys.executable}' "
                                    f"pelo ficheiro baixado em '{downloaded_file_path}'.")
            if 'old_exe_path' in locals() and os.path.exists(old_exe_path) and not os.path.exists(current_exe_path):
                print(f"Tentando reverter renomeação: movendo {old_exe_path} de volta para {current_exe_path}")
                try:
                    os.rename(old_exe_path, current_exe_path)
                except Exception as e_revert:
                    print(f"Falha ao reverter renomeação: {e_revert}")

    def _restart_app(self, path):
        print(f"Tentando reiniciar com: {path}")
        try:
            subprocess.Popen([path])
        except Exception as e_restart:
            print(f"Falha ao reiniciar a aplicação: {e_restart}")
            if self.parent_window:
                QMessageBox.critical(self.parent_window, "Erro ao Reiniciar", 
                                     f"Não foi possível reiniciar a aplicação automaticamente: {e_restart}")
        finally:
            current_app = QApplication.instance()
            if current_app:
                current_app.quit()

    @Slot(str)
    def _handle_update_error(self, error_message): 
        if self.progress_dialog and self.progress_dialog.isVisible():
            self.progress_dialog.close()
            self.progress_dialog = None
        if self.parent_window:
            QMessageBox.critical(self.parent_window, "Erro de Atualização", error_message)

if __name__ == '__main__':
    # Este bloco é para teste isolado do UpdateService.
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)

    class DummyMainWindowForTest(QWidget): 
        def __init__(self):
            super().__init__()
            self.setWindowTitle("Teste Update Service")
            self.layout = QVBoxLayout() 
            self.btn = QPushButton("Verificar Atualizações (Teste)", self)
            self.layout.addWidget(self.btn)
            self.update_service = UpdateService(parent_window=self) 
            self.btn.clicked.connect(lambda: self.update_service.check_for_updates(is_manual_check=True))
            self.setLayout(self.layout) 

    # VERSION_INFO_URL é importado de config.constants
    if "SEU_USUARIO_GITHUB" in VERSION_INFO_URL or VERSION_INFO_URL == "NOT_CONFIGURED":
        print("ALERTA: VERSION_INFO_URL não está configurada corretamente em config/constants.py para o teste no __main__.")
        if QApplication.instance(): 
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Warning)
            msg_box.setText("URL de Atualização Não Configurada para Teste")
            msg_box.setInformativeText("A constante VERSION_INFO_URL (importada de config.constants)\n"
                                       "precisa ser definida com um URL real para testar esta funcionalidade.")
            msg_box.setStandardButtons(QMessageBox.Ok)
            msg_box.exec()
        sys.exit(0) 
    
    main_test_win = DummyMainWindowForTest()
    main_test_win.show()
    sys.exit(app.exec())

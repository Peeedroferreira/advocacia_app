# processes_tab_pyside.py

import datetime
from typing import Dict, List, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QScrollArea, QFrame, QSplitter, QApplication, QDialog
)
from PySide6.QtCore import Qt, Slot, QTimer
from PySide6.QtGui import QFont
import json # Adicionado para debug com json.dumps

# Supondo que ProcessFormDialog_pyside está no mesmo diretório ou importável
from .process_form_dialog_pyside import ProcessFormDialog_pyside 

class ProcessesTab_pyside(QWidget):
    def __init__(self, user_id: str, process_api_service, client_api_service, parent=None):
        super().__init__(parent)
        self.user_id = user_id
        self.process_api_service = process_api_service 
        self.client_api_service = client_api_service 
        self.selected_process_id: Optional[str] = None
        self.clients_cache: List[Dict[str, str]] = [] 
        self.details_labels_widgets: List[QWidget] = [] # Para limpar os widgets de detalhes dinâmicos

        print(f"ProcessesTab_pyside: Instanciada com user_id: {self.user_id}, process_api_service: {type(self.process_api_service)}, client_api_service: {type(self.client_api_service)}")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)

        action_bar_layout = QHBoxLayout()
        self.search_entry = QLineEdit()
        self.search_entry.setPlaceholderText("Buscar por Nº do Processo, Cliente, Assunto...")
        self.search_entry.textChanged.connect(self.filter_processes_display)
        action_bar_layout.addWidget(self.search_entry)

        add_process_btn = QPushButton("Adicionar Processo")
        add_process_btn.clicked.connect(self.open_add_process_dialog)
        action_bar_layout.addWidget(add_process_btn)
        main_layout.addLayout(action_bar_layout)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)

        self.processes_table = QTableWidget()
        self.processes_table.setColumnCount(5) 
        self.processes_table.setHorizontalHeaderLabels(["ID Processo", "Nº Processo", "Cliente", "Vara", "Fase Atual"])
        self.processes_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.processes_table.setColumnHidden(0, True) 
        self.processes_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive) 
        self.processes_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        self.processes_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.processes_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.processes_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.processes_table.itemSelectionChanged.connect(self.on_process_selected_from_table)
        self.splitter.addWidget(self.processes_table)

        self.process_details_area = QScrollArea()
        self.process_details_area.setWidgetResizable(True)
        self.process_details_content_widget = QWidget()
        self.process_details_layout = QVBoxLayout(self.process_details_content_widget)
        self.process_details_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        self.edit_process_btn = QPushButton("Editar Processo Selecionado")
        self.edit_process_btn.clicked.connect(self.open_edit_process_dialog)
        self.edit_process_btn.setEnabled(False)
        self.process_details_layout.addWidget(self.edit_process_btn)

        self.delete_process_btn = QPushButton("Remover Processo Selecionado")
        self.delete_process_btn.clicked.connect(self.delete_selected_process)
        self.delete_process_btn.setEnabled(False)
        self.process_details_layout.addWidget(self.delete_process_btn)
        
        # Este QLabel será usado para os detalhes, incluindo documentos
        self.details_display_label = QLabel("Selecione um processo para ver os detalhes.")
        self.details_display_label.setWordWrap(True)
        self.details_display_label.setAlignment(Qt.AlignmentFlag.AlignTop) # Para o texto começar do topo
        self.process_details_layout.addWidget(self.details_display_label)
        
        self.process_details_layout.addStretch() # Adiciona um espaçador flexível no final

        self.process_details_area.setWidget(self.process_details_content_widget)
        self.splitter.addWidget(self.process_details_area)
        
        self.splitter.setStretchFactor(0, 2) 
        self.splitter.setStretchFactor(1, 1)

        main_layout.addWidget(self.splitter)
        self.setLayout(main_layout)

        self.fetch_clients_for_form() 
        self.load_processes_from_api() 

    def fetch_clients_for_form(self):
        print("ProcessesTab: Buscando lista de clientes para o formulário...")
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            response = self.client_api_service.get_clients_by_user(self.user_id)
            if response and response.get("success") and "clients" in response:
                self.clients_cache = response["clients"]
                print(f"ProcessesTab: {len(self.clients_cache)} clientes carregados para o formulário.")
            else:
                self.clients_cache = []
                QMessageBox.warning(self, "Erro ao Carregar Clientes",
                                    response.get("message", "Não foi possível buscar a lista de clientes para o formulário."))
        finally:
            QApplication.restoreOverrideCursor()

    def load_processes_from_api(self, search_term=""):
        print(f"ProcessesTab: load_processes_from_api. User ID: {self.user_id}, Busca: '{search_term}'")
        self.processes_table.setRowCount(0)
        if not self.user_id:
            QMessageBox.critical(self, "Erro Interno", "ID do utilizador não está disponível para carregar processos.")
            return
        
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            api_response = self.process_api_service.get_processes_by_user(self.user_id, search_term) 
        finally:
            QApplication.restoreOverrideCursor()
        
        all_processes_data = []
        if api_response and api_response.get("success") and "processes" in api_response:
            all_processes_data = api_response["processes"]
            print(f"ProcessesTab: {len(all_processes_data)} processos recebidos da API.")
        elif api_response and not api_response.get("success"):
             QMessageBox.warning(self, "Erro ao Carregar Processos", api_response.get("message", "Não foi possível buscar os processos do servidor."))
        else:
             QMessageBox.warning(self, "Erro ao Carregar Processos", "Resposta inesperada ou falha de comunicação ao buscar processos.")
        
        self.processes_table.setSortingEnabled(False)
        for row, process_item in enumerate(all_processes_data):
            self.processes_table.insertRow(row)
            self.processes_table.setItem(row, 0, QTableWidgetItem(str(process_item.get("process_id", "N/A"))))
            self.processes_table.setItem(row, 1, QTableWidgetItem(process_item.get("numero_processo", "N/A")))
            client_display = process_item.get("client_nome_completo", process_item.get("client_cpf", "N/A"))
            self.processes_table.setItem(row, 2, QTableWidgetItem(client_display))
            self.processes_table.setItem(row, 3, QTableWidgetItem(process_item.get("vara", "N/A")))
            self.processes_table.setItem(row, 4, QTableWidgetItem(process_item.get("fase_atual", "N/A")))
        self.processes_table.setSortingEnabled(True)
        
        self.clear_process_details_display() # Limpa os detalhes
        self.edit_process_btn.setEnabled(False)
        self.delete_process_btn.setEnabled(False)

    @Slot()
    def filter_processes_display(self):
        search_term = self.search_entry.text()
        self.load_processes_from_api(search_term)

    @Slot() 
    def on_process_selected_from_table(self):
        selected_items = self.processes_table.selectedItems()
        if selected_items:
            selected_row = self.processes_table.currentRow() 
            process_id_item = self.processes_table.item(selected_row, 0) 
            if process_id_item:
                self.selected_process_id = process_id_item.text()
                print(f"ProcessesTab: Processo selecionado da tabela - ID {self.selected_process_id}")
                self.display_process_details(self.selected_process_id)
                self.edit_process_btn.setEnabled(True)
                self.delete_process_btn.setEnabled(True)
                return
        
        self.selected_process_id = None
        self.clear_process_details_display()
        self.edit_process_btn.setEnabled(False)
        self.delete_process_btn.setEnabled(False)

    def display_process_details(self, process_id_to_display: str):
        # Limpa o conteúdo anterior do QLabel de detalhes
        self.clear_process_details_display() 
        print(f"DEBUG UI: Chamando display_process_details para ID: {process_id_to_display}")

        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        api_response = None # Inicializa para o caso de erro na chamada
        try:
            api_response = self.process_api_service.get_process_details(self.user_id, process_id_to_display)
            print(f"DEBUG UI - display_process_details - api_response: {json.dumps(api_response, indent=2, ensure_ascii=False)}") 
        except Exception as e:
            print(f"DEBUG UI - Erro ao chamar get_process_details: {e}")
            QMessageBox.critical(self, "Erro de API", f"Erro ao buscar detalhes do processo: {e}")
        finally:
            QApplication.restoreOverrideCursor()

        if api_response and api_response.get("success") and "process" in api_response:
            process_info = api_response.get("process", {}) # Pega 'process' com segurança
            print(f"DEBUG UI - display_process_details - process_info: {json.dumps(process_info, indent=2, ensure_ascii=False)}")

            details_text_parts = ["<b>Detalhes do Processo:</b>"] # Usar lista para construir o texto
            
            # Mapeamento dos campos do formulário para exibição (ajuste conforme necessário)
            # Se ProcessFormDialog_pyside.STATIC_PROCESS_FIELDS_CONFIG não estiver acessível ou for muito complexo,
            # defina um mapeamento mais simples aqui ou passe os labels de alguma forma.
            # Por ora, vamos usar um mapeamento simplificado se o original não estiver disponível.
            try:
                dialog_fields_map = {item[1]: item[0].replace(":", "") for item in ProcessFormDialog_pyside.STATIC_PROCESS_FIELDS_CONFIG}
            except AttributeError: # Fallback se STATIC_PROCESS_FIELDS_CONFIG não for acessível
                print("DEBUG UI: STATIC_PROCESS_FIELDS_CONFIG não encontrado em ProcessFormDialog_pyside. Usando mapeamento manual.")
                dialog_fields_map = {
                    "numero_processo": "Número do Processo", "client_cpf": "Cliente Associado",
                    "vara": "Vara", "juizo": "Juízo", "comarca": "Comarca", 
                    "classe_judicial": "Classe Judicial", "assuntos": "Assuntos",
                    "valor_causa": "Valor da Causa (R$)", "fase_atual": "Fase Atual",
                    "observacoes": "Observações", "data_distribuicao": "Data de Distribuição",
                    "link_processo_externo": "Link do Processo (Tribunal)",
                    "created_at": "Criado em", "updated_at": "Atualizado em" 
                    # Adicione outros campos se necessário
                }


            for attr_name, friendly_label_text in dialog_fields_map.items():
                value = process_info.get(attr_name)
                if value is not None: # Exibir mesmo se for string vazia, se o atributo existir
                    display_value_str = str(value)
                    if attr_name == "client_cpf" and self.clients_cache:
                        client_found = next((c for c in self.clients_cache if c.get('client_cpf') == display_value_str), None)
                        if client_found:
                            display_value_str = f"{client_found.get('nome_completo', display_value_str)} (CPF: {display_value_str})"
                    
                    # Formatar datas se forem timestamps ISO
                    if attr_name in ["created_at", "updated_at", "data_distribuicao"] and 'T' in display_value_str:
                        try:
                            dt_obj = datetime.datetime.fromisoformat(display_value_str.replace("Z", "+00:00"))
                            display_value_str = dt_obj.strftime("%d/%m/%Y %H:%M:%S")
                        except ValueError:
                            pass # Mantém a string original se não puder formatar

                    details_text_parts.append(f"<b>{friendly_label_text}:</b> {display_value_str}")
            
            # Lógica para exibir documentos:
            documents = process_info.get("documents", []) 
            print(f"DEBUG UI - display_process_details - documents list extraída: {documents}")
            print(f"DEBUG UI - display_process_details - Tipo da lista 'documents': {type(documents)}")

            if isinstance(documents, list) and documents:
                details_text_parts.append("<br><b>Documentos Anexados:</b>")
                print(f"DEBUG UI: Entrou no IF de 'documents' (existem {len(documents)} documentos)")
                for i, doc in enumerate(documents):
                    filename = doc.get('filename', 'Documento sem nome')
                    download_url = doc.get('download_url') # A Lambda já gera isso
                    print(f"DEBUG UI - display_process_details - Documento {i}: Filename='{filename}', URL='{download_url is not None}'")
                    
                    if download_url:
                        # QLabel não suporta links clicáveis diretamente de forma simples.
                        # Para links clicáveis, você precisaria de um QTextBrowser com setOpenExternalLinks(True)
                        # ou um evento de clique no QLabel para abrir a URL.
                        # Por ora, apenas listamos o nome.
                        details_text_parts.append(f"- {filename}")
                    else:
                        details_text_parts.append(f"- {filename} (URL de download indisponível)")
            else:
                details_text_parts.append("<br>Nenhum documento anexado.")
                print("DEBUG UI - display_process_details - Bloco ELSE - Nenhum documento anexado ou 'documents' não é uma lista.")
            
            final_details_html = "<br>".join(details_text_parts)
            print(f"DEBUG UI - display_process_details - final_details_html: {final_details_html}")
            self.details_display_label.setText(final_details_html)
            print("DEBUG UI: self.details_display_label.setText() chamado.")
        else:
            error_msg = "Falha ao buscar detalhes do processo ou resposta da API sem sucesso/processo."
            if api_response and isinstance(api_response, dict): 
                 error_msg = api_response.get("message", error_msg)
            print(f"DEBUG UI - Erro ou sem sucesso na API: {error_msg}")
            self.details_display_label.setText(f"<font color='red'>{error_msg}</font>")

    def clear_process_details_display(self):
        """Limpa o QLabel que mostra os detalhes do processo."""
        self.details_display_label.setText("Selecione um processo para ver os detalhes.")
        print("DEBUG UI: clear_process_details_display chamado.")


    def open_add_process_dialog(self):
        print("ProcessesTab: open_add_process_dialog chamado.")
        if not self.clients_cache: 
            QMessageBox.information(self, "A Carregar Clientes", "A buscar lista de clientes para o formulário...")
            self.fetch_clients_for_form() # Garante que a lista de clientes está carregada
            if not self.clients_cache: # Verifica novamente após a tentativa de carregar
                QMessageBox.warning(self, "Sem Clientes", "Não há clientes cadastrados para associar ao processo. Por favor, adicione um cliente primeiro.")
                return

        dialog = ProcessFormDialog_pyside(self.process_api_service, self.client_api_service, self.user_id, self.clients_cache, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_processes_from_api() 

    def open_edit_process_dialog(self):
        if not self.selected_process_id:
            QMessageBox.warning(self, "Seleção Necessária", "Por favor, selecione um processo na lista para editar.")
            return
        print(f"ProcessesTab: open_edit_process_dialog para ID {self.selected_process_id}")
        if not self.clients_cache: self.fetch_clients_for_form() 

        dialog = ProcessFormDialog_pyside(self.process_api_service, self.client_api_service, self.user_id, self.clients_cache, process_id_to_edit=self.selected_process_id, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_processes_from_api() 
            self.display_process_details(self.selected_process_id) # Atualiza os detalhes após a edição

    def delete_selected_process(self):
        if not self.selected_process_id:
            QMessageBox.warning(self, "Seleção Necessária", "Por favor, selecione um processo para remover.")
            return
        print(f"ProcessesTab: delete_selected_process para ID {self.selected_process_id}")

        current_row = self.processes_table.currentRow()
        numero_processo_confirm = self.selected_process_id 
        if current_row >= 0:
            item_num_proc = self.processes_table.item(current_row, 1) 
            if item_num_proc:
                numero_processo_confirm = item_num_proc.text()
        
        confirm_msg = (f"Tem certeza que deseja remover o processo:\n"
                       f"Nº: {numero_processo_confirm} (ID: {self.selected_process_id})\n\n"
                       "Esta ação não pode ser desfeita e removerá também documentos associados.")
        
        reply = QMessageBox.question(self, "Confirmar Remoção", confirm_msg,
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            api_response = None
            try:
                api_response = self.process_api_service.delete_process(self.user_id, self.selected_process_id)
            except Exception as e:
                print(f"Erro ao chamar delete_process: {e}")
                QMessageBox.critical(self, "Erro na Remoção", f"Erro ao tentar remover processo: {e}")
            finally:
                QApplication.restoreOverrideCursor()

            if api_response and api_response.get("success"):
                QMessageBox.information(self, "Sucesso", api_response.get("message", "Processo removido com sucesso."))
                self.load_processes_from_api() 
                self.clear_process_details_display() # Limpa os detalhes do processo removido
                self.edit_process_btn.setEnabled(False) # Desabilita botões
                self.delete_process_btn.setEnabled(False)
            elif api_response: # Se houve resposta da API, mas não foi sucesso
                error_msg = api_response.get("message", "Não foi possível remover o processo via API.")
                QMessageBox.critical(self, "Erro na Remoção", error_msg)
            # Se api_response for None (devido a exceção na chamada), a mensagem de erro já foi mostrada.


# processes_tab_pyside.py

import datetime
from typing import Dict, List, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QScrollArea, QTextBrowser, QApplication, QDialog, QSplitter
)
from PySide6.QtCore import Qt, Slot, QDateTime 
from PySide6.QtGui import QFont
import json

from .process_form_dialog_pyside import ProcessFormDialog_pyside
from .hearing_form_dialog_pyside import HearingFormDialog_pyside # Para agendar audiência

class ProcessesTab_pyside(QWidget):
    def __init__(self, user_id: str, process_api_service, client_api_service, hearings_api_service, parent=None): 
        super().__init__(parent)
        self.user_id = user_id
        self.process_api_service = process_api_service 
        self.client_api_service = client_api_service 
        self.hearings_api_service = hearings_api_service 
        self.selected_process_id: Optional[str] = None
        self.clients_cache: List[Dict[str, str]] = [] 
        
        print(f"ProcessesTab_pyside: Instanciada com user_id: {self.user_id}")

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
        details_content_layout = QVBoxLayout(self.process_details_content_widget) 
        details_content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.edit_process_btn = QPushButton("Editar Processo Selecionado")
        self.edit_process_btn.clicked.connect(self.open_edit_process_dialog)
        self.edit_process_btn.setEnabled(False)
        details_content_layout.addWidget(self.edit_process_btn)

        self.delete_process_btn = QPushButton("Remover Processo Selecionado")
        self.delete_process_btn.clicked.connect(self.delete_selected_process)
        self.delete_process_btn.setEnabled(False)
        details_content_layout.addWidget(self.delete_process_btn)

        self.schedule_hearing_btn = QPushButton("Agendar Audiência para este Processo")
        self.schedule_hearing_btn.clicked.connect(self.open_schedule_hearing_for_process_dialog)
        self.schedule_hearing_btn.setEnabled(False) 
        details_content_layout.addWidget(self.schedule_hearing_btn)
        
        self.details_display_browser = QTextBrowser() 
        self.details_display_browser.setOpenExternalLinks(True) 
        self.details_display_browser.setFont(QFont("Arial", 10)) 
        details_content_layout.addWidget(self.details_display_browser)
        
        self.process_details_content_widget.setLayout(details_content_layout) 
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
                msg = "Não foi possível buscar a lista de clientes para o formulário."
                if response and isinstance(response, dict) and response.get("message"): 
                    msg = response.get("message")
                QMessageBox.warning(self, "Erro ao Carregar Clientes", msg)
        except Exception as e:
            print(f"Erro em fetch_clients_for_form: {e}")
            QMessageBox.critical(self, "Erro Crítico", f"Erro ao buscar clientes: {e}")
        finally:
            QApplication.restoreOverrideCursor()

    def load_processes_from_api(self, search_term=""):
        print(f"ProcessesTab: load_processes_from_api. User ID: {self.user_id}, Busca: '{search_term}'")
        self.processes_table.setRowCount(0)
        if not self.user_id:
            QMessageBox.critical(self, "Erro Interno", "ID do utilizador não está disponível para carregar processos.")
            return
        
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        api_response = None
        try:
            api_response = self.process_api_service.get_processes_by_user(self.user_id, search_term) 
        except Exception as e:
            print(f"Erro em load_processes_from_api ao chamar serviço: {e}")
            QMessageBox.critical(self, "Erro de API", f"Erro ao buscar lista de processos: {e}")
        finally:
            QApplication.restoreOverrideCursor()
        
        all_processes_data = []
        if api_response and api_response.get("success") and "processes" in api_response:
            all_processes_data = api_response["processes"]
            print(f"ProcessesTab: {len(all_processes_data)} processos recebidos da API.")
        elif api_response and not api_response.get("success"):
             QMessageBox.warning(self, "Erro ao Carregar Processos", api_response.get("message", "Não foi possível buscar os processos do servidor."))
        elif not api_response and not isinstance(api_response, bool): 
             pass 
        else: 
             QMessageBox.warning(self, "Erro ao Carregar Processos", "Resposta inesperada ou falha de comunicação ao buscar processos.")
        
        self.processes_table.setSortingEnabled(False)
        for row, process_item in enumerate(all_processes_data):
            self.processes_table.insertRow(row)
            self.processes_table.setItem(row, 0, QTableWidgetItem(str(process_item.get("process_id", "N/A"))))
            self.processes_table.setItem(row, 1, QTableWidgetItem(process_item.get("numero_processo", "N/A")))
            
            client_cpf_from_process = process_item.get("client_cpf")
            client_display_name = client_cpf_from_process 
            if client_cpf_from_process and self.clients_cache:
                found_client = next((c for c in self.clients_cache if c.get('client_cpf') == client_cpf_from_process), None)
                if found_client:
                    client_display_name = found_client.get('nome_completo', client_cpf_from_process)
            
            self.processes_table.setItem(row, 2, QTableWidgetItem(client_display_name))
            self.processes_table.setItem(row, 3, QTableWidgetItem(process_item.get("vara", "N/A")))
            self.processes_table.setItem(row, 4, QTableWidgetItem(process_item.get("fase_atual", "N/A")))
        self.processes_table.setSortingEnabled(True)
        
        self.clear_process_details_display()
        self.edit_process_btn.setEnabled(False)
        self.delete_process_btn.setEnabled(False)
        self.schedule_hearing_btn.setEnabled(False)

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
            if process_id_item and process_id_item.text() != "N/A":
                self.selected_process_id = process_id_item.text()
                print(f"ProcessesTab: Processo selecionado da tabela - ID {self.selected_process_id}")
                self.display_process_details(self.selected_process_id)
                self.edit_process_btn.setEnabled(True)
                self.delete_process_btn.setEnabled(True)
                self.schedule_hearing_btn.setEnabled(True) 
                return
        
        self.selected_process_id = None
        self.clear_process_details_display()
        self.edit_process_btn.setEnabled(False)
        self.delete_process_btn.setEnabled(False)
        self.schedule_hearing_btn.setEnabled(False) 

    def display_process_details(self, process_id_to_display: str):
        self.clear_process_details_display() 
        print(f"DEBUG UI: Chamando display_process_details para ID: {process_id_to_display}")

        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        process_api_response = None
        hearings_api_response = None # Para armazenar a resposta das audiências
        try:
            process_api_response = self.process_api_service.get_process_details(self.user_id, process_id_to_display)
            # Se os detalhes do processo foram carregados com sucesso, busca as audiências
            if process_api_response and process_api_response.get("success"):
                print(f"DEBUG UI: Buscando audiências para o processo ID: {process_id_to_display}")
                hearings_api_response = self.hearings_api_service.get_hearings_by_user(self.user_id, process_id=process_id_to_display)
                print(f"DEBUG UI - display_process_details - hearings_api_response: {json.dumps(hearings_api_response, indent=2, ensure_ascii=False)}")
        except Exception as e:
            print(f"DEBUG UI - Erro ao chamar APIs em display_process_details: {e}")
            QMessageBox.critical(self, "Erro de API", f"Erro ao buscar dados: {e}")
            self.details_display_browser.setHtml("<font color='red'>Erro ao buscar dados.</font>")
            QApplication.restoreOverrideCursor()
            return
        finally:
            QApplication.restoreOverrideCursor()

        html_parts = []
        if process_api_response and process_api_response.get("success") and "process" in process_api_response:
            process_info = process_api_response.get("process", {})
            html_parts.append("<h3>Detalhes do Processo:</h3><table width='100%' cellspacing='0' cellpadding='3' style='border-collapse: collapse;'>")
            
            try:
                dialog_fields_map = {item[1]: item[0].replace(":", "") for item in ProcessFormDialog_pyside.STATIC_PROCESS_FIELDS_CONFIG}
            except AttributeError: 
                dialog_fields_map = {
                    "numero_processo": "Número do Processo", "client_cpf": "Cliente Associado",
                    "vara": "Vara", "juizo": "Juízo", "comarca": "Comarca", 
                    "classe_judicial": "Classe Judicial", "assuntos": "Assuntos",
                    "valor_causa": "Valor da Causa (R$)", "fase_atual": "Fase Atual",
                    "observacoes": "Observações", "data_distribuicao": "Data de Distribuição",
                    "link_processo_externo": "Link do Processo (Tribunal)",
                    "created_at": "Criado em", "updated_at": "Atualizado em"
                }

            for attr_name, friendly_label_text in dialog_fields_map.items():
                value = process_info.get(attr_name)
                if value is not None: 
                    display_value_str = str(value).replace('\t', ' ')
                    if attr_name == "client_cpf" and self.clients_cache:
                        client_found = next((c for c in self.clients_cache if c.get('client_cpf') == display_value_str), None)
                        if client_found:
                            display_value_str = f"{client_found.get('nome_completo', display_value_str)} (CPF: {display_value_str})"
                    
                    if attr_name in ["created_at", "updated_at"] and 'T' in display_value_str:
                        try:
                            dt_obj = datetime.datetime.fromisoformat(display_value_str.replace("Z", "+00:00"))
                            display_value_str = dt_obj.strftime("%d/%m/%Y %H:%M:%S")
                        except ValueError: pass 
                    elif attr_name == "data_distribuicao" and value: 
                         try: 
                            dt_obj = datetime.datetime.strptime(display_value_str, "%Y-%m-%d")
                            display_value_str = dt_obj.strftime("%d/%m/%Y")
                         except ValueError:
                            try:
                                datetime.datetime.strptime(display_value_str, "%d/%m/%Y")
                            except ValueError: pass 
                    html_parts.append(f"<tr><td valign='top' style='padding: 4px; border: 1px solid #ddd;' width='180px'><b>{friendly_label_text}:</b></td><td style='padding: 4px; border: 1px solid #ddd;'>{display_value_str}</td></tr>")
            html_parts.append("</table>")

            documents = process_info.get("documents", []) 
            if isinstance(documents, list) and documents:
                html_parts.append("<br><h3>Documentos Anexados (Processo):</h3><ul style='list-style-type: none; padding-left: 0;'>")
                for doc in documents:
                    filename = doc.get('filename', 'Documento sem nome')
                    download_url = doc.get('download_url') 
                    if download_url:
                        html_parts.append(f"<li style='margin-bottom: 5px;'><a href='{download_url}' style='text-decoration: none; color: #007bff;'>📄 {filename}</a></li>")
                    else:
                        html_parts.append(f"<li style='margin-bottom: 5px;'>📄 {filename} (URL indisponível)</li>")
                html_parts.append("</ul>")
            else:
                html_parts.append("<p>Nenhum documento anexado a este processo.</p>")
        else:
            error_msg = "Falha ao buscar detalhes do processo."
            if process_api_response and isinstance(process_api_response, dict): 
                 error_msg = process_api_response.get("message", error_msg)
            html_parts.append(f"<p><font color='red'>{error_msg}</font></p>")

        # Exibir audiências associadas
        html_parts.append("<br><h3>Audiências Agendadas para este Processo:</h3>")
        if hearings_api_response and hearings_api_response.get("success"):
            process_hearings = hearings_api_response.get("hearings", [])
            if process_hearings:
                html_parts.append("<ul style='list-style-type: none; padding-left: 0;'>")
                process_hearings.sort(key=lambda h: h.get("data_hora", ""), reverse=False) 
                for hearing in process_hearings:
                    data_hora_str = hearing.get("data_hora", "N/A")
                    display_dt = data_hora_str
                    try:
                        # Tenta parsear como ISODate (que a Lambda deve retornar)
                        dt = QDateTime.fromString(data_hora_str, Qt.DateFormat.ISODate)
                        if not dt.isValid(): # Tenta com milissegundos se o primeiro falhar
                             dt = QDateTime.fromString(data_hora_str, Qt.DateFormat.ISODateWithMs)
                        
                        if dt.isValid(): display_dt = dt.toString("dd/MM/yyyy 'às' HH:mm")
                    except Exception as e_dt_parse:
                        print(f"DEBUG UI: Erro ao parsear data_hora da audiência '{data_hora_str}': {e_dt_parse}")
                        pass # Mantém a string original se o parse falhar
                    
                    tipo = hearing.get('tipo', 'N/A')
                    local = hearing.get('local', 'N/A')
                    html_parts.append(f"<li style='margin-bottom: 5px;'>📅 <strong>{tipo}</strong> em {display_dt} - Local: {local}</li>")
                html_parts.append("</ul>")
            else:
                html_parts.append("<p>Nenhuma audiência agendada para este processo.</p>")
        elif hearings_api_response: 
            error_msg_hearings = hearings_api_response.get("message", "Não foi possível carregar audiências.")
            html_parts.append(f"<p><font color='red'>Erro ao carregar audiências: {error_msg_hearings}</font></p>")
        else: 
             html_parts.append("<p><font color='red'>Não foi possível carregar informações de audiências.</font></p>")
            
        final_details_html = "".join(html_parts)
        self.details_display_browser.setHtml(final_details_html)

    def clear_process_details_display(self):
        self.details_display_browser.setHtml("Selecione um processo para ver os detalhes.")

    def open_add_process_dialog(self):
        print("ProcessesTab: open_add_process_dialog chamado.")
        if not self.clients_cache: 
            QMessageBox.information(self, "A Carregar Clientes", "A buscar lista de clientes para o formulário...")
            self.fetch_clients_for_form()
            if not self.clients_cache:
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
            self.display_process_details(self.selected_process_id) # Reexibe os detalhes atualizados

    @Slot()
    def open_schedule_hearing_for_process_dialog(self):
        if not self.selected_process_id:
            QMessageBox.warning(self, "Seleção Necessária", "Nenhum processo selecionado para agendar audiência.")
            return
        
        print(f"ProcessesTab: Abrindo diálogo de audiência para o processo ID: {self.selected_process_id}")
        dialog = HearingFormDialog_pyside(
            self.hearings_api_service, 
            self.process_api_service, # Passado para que HearingFormDialog possa buscar lista de processos se necessário
            self.user_id,
            initial_process_id=self.selected_process_id, 
            parent=self
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Após agendar uma audiência, atualiza os detalhes do processo para mostrar a nova audiência
            self.display_process_details(self.selected_process_id)
            # Opcional: Notificar a aba de audiências para recarregar também
            # if hasattr(self.parent(), 'hearings_tab') and self.parent().hearings_tab:
            #     self.parent().hearings_tab.load_all_hearings_from_api()


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
                       "Esta ação não pode ser desfeita e removerá também documentos e audiências associadas.") 
        
        reply = QMessageBox.question(self, "Confirmar Remoção", confirm_msg,
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            api_response = None
            try:
                # A API de delete_process na Lambda deve ser ajustada para também deletar audiências associadas
                api_response = self.process_api_service.delete_process(self.user_id, self.selected_process_id)
            except Exception as e:
                print(f"Erro ao chamar delete_process: {e}")
                QMessageBox.critical(self, "Erro na Remoção", f"Erro ao tentar remover processo: {e}")
            finally:
                QApplication.restoreOverrideCursor()

            if api_response and api_response.get("success"):
                QMessageBox.information(self, "Sucesso", api_response.get("message", "Processo removido com sucesso."))
                self.load_processes_from_api() 
                self.clear_process_details_display() 
                self.edit_process_btn.setEnabled(False) 
                self.delete_process_btn.setEnabled(False)
                self.schedule_hearing_btn.setEnabled(False)
            elif api_response: 
                error_msg = api_response.get("message", "Não foi possível remover o processo via API.")
                QMessageBox.critical(self, "Erro na Remoção", error_msg)


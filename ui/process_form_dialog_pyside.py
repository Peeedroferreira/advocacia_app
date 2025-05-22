from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit, QTextEdit,
    QDialogButtonBox, QMessageBox, QPushButton, QFileDialog,
    QListWidget, QAbstractItemView, QComboBox, QLabel, QApplication,
    QListWidgetItem,
)
from PySide6.QtCore import Qt, Slot, QFileInfo
from typing import List, Dict, Optional, Any

class ProcessFormDialog_pyside(QDialog):
    """
    Diálogo para adicionar ou editar um processo jurídico.
    """
    STATIC_PROCESS_FIELDS_CONFIG = [
        ("Número do Processo:", "numero_processo", QLineEdit, True, "Ex: 0000000-00.0000.0.00.0000"),
        ("Cliente Associado:", "client_cpf", QComboBox, True, []), 
        ("Vara:", "vara", QLineEdit, False, "Ex: 1ª Vara Cível"),
        ("Juízo:", "juizo", QLineEdit, False, "Ex: Tribunal de Justiça Estadual"),
        ("Comarca:", "comarca", QLineEdit, False, "Ex: Comarca da Capital"),
        ("Classe Judicial:", "classe_judicial", QLineEdit, False, "Ex: Procedimento Comum Cível"),
        ("Assuntos (separados por vírgula):", "assuntos", QTextEdit, False, "Ex: Direito Civil, Contratos, Indenização"),
        ("Valor da Causa (R$):", "valor_causa", QLineEdit, False, "Ex: 15000.00"),
        ("Fase Atual:", "fase_atual", QLineEdit, False, "Ex: Inicial, Instrução, Recursal"),
        ("Observações:", "observacoes", QTextEdit, False, "Detalhes adicionais sobre o processo"),
        ("Data de Distribuição:", "data_distribuicao", QLineEdit, False, "DD/MM/AAAA"), 
        ("Link do Processo (Tribunal):", "link_processo_externo", QLineEdit, False, "URL para consulta pública")
    ]

    def __init__(self, process_api_service, client_api_service, user_id: str, clients_list: List[Dict[str, str]], process_id_to_edit: Optional[str] = None, parent=None):
        super().__init__(parent)
        self.process_api_service = process_api_service
        self.client_api_service = client_api_service 
        self.user_id = user_id
        self.clients_list = clients_list 
        self.process_id_to_edit = process_id_to_edit
        self.process_data_to_edit: Optional[Dict[str, Any]] = None
        self.files_to_upload: List[QFileInfo] = [] 

        self.setWindowTitle("Adicionar Novo Processo" if not self.process_id_to_edit else "Editar Processo")
        self.setMinimumWidth(650)
        self.setMinimumHeight(700) 

        main_layout = QVBoxLayout(self)
        
        form_layout_container = QFormLayout()
        
        self.entries: Dict[str, QLineEdit | QTextEdit | QComboBox] = {}
        for label_text, attr_name, WidgetClass, _, placeholder_or_items in ProcessFormDialog_pyside.STATIC_PROCESS_FIELDS_CONFIG:
            if WidgetClass == QComboBox and attr_name == "client_cpf":
                widget = QComboBox()
                widget.addItem("Selecione um Cliente...", None) 
                for client in self.clients_list:
                    widget.addItem(f"{client.get('nome_completo', 'Nome Desconhecido')} (CPF: {client.get('client_cpf', 'N/A')})", client.get('client_cpf'))
                if not self.clients_list:
                    widget.setEnabled(False)
                    widget.addItem("Nenhum cliente cadastrado", None)
            elif WidgetClass == QTextEdit:
                widget = WidgetClass()
                widget.setPlaceholderText(str(placeholder_or_items))
                widget.setMinimumHeight(80)
            elif WidgetClass == QLineEdit:
                widget = WidgetClass()
                widget.setPlaceholderText(str(placeholder_or_items))
            else: 
                widget = WidgetClass()

            self.entries[attr_name] = widget
            form_layout_container.addRow(label_text, widget)
        
        main_layout.addLayout(form_layout_container)

        main_layout.addWidget(QLabel("<b>Documentos do Processo:</b>"))
        
        self.documents_list_widget = QListWidget()
        self.documents_list_widget.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        main_layout.addWidget(self.documents_list_widget)

        document_buttons_layout = QHBoxLayout()
        add_doc_button = QPushButton("Anexar Novo Documento (PDF)")
        add_doc_button.clicked.connect(self.select_document_to_attach)
        document_buttons_layout.addWidget(add_doc_button)
        
        main_layout.addLayout(document_buttons_layout)
        
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept_data)
        self.button_box.rejected.connect(self.reject)
        main_layout.addWidget(self.button_box)

        self.setLayout(main_layout)

        if self.process_id_to_edit:
            self.load_process_data_for_edit()

    def load_process_data_for_edit(self):
        if not self.process_id_to_edit:
            return
        print(f"ProcessFormDialog: Carregando dados para editar processo ID {self.process_id_to_edit} para utilizador {self.user_id}")
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            api_response = self.process_api_service.get_process_details(self.user_id, self.process_id_to_edit)
        finally:
            QApplication.restoreOverrideCursor()
        
        if api_response and api_response.get("success") and "process" in api_response:
            self.process_data_to_edit = api_response["process"]
            
            for _, attr_name, WidgetClass, _, _ in ProcessFormDialog_pyside.STATIC_PROCESS_FIELDS_CONFIG:
                widget = self.entries.get(attr_name)
                value = self.process_data_to_edit.get(attr_name)
                if widget and value is not None:
                    if isinstance(widget, QLineEdit):
                        widget.setText(str(value))
                    elif isinstance(widget, QTextEdit):
                        widget.setPlainText(str(value))
                    elif isinstance(widget, QComboBox) and attr_name == "client_cpf":
                        client_cpf_to_select = str(value)
                        for i in range(widget.count()):
                            if widget.itemData(i) == client_cpf_to_select:
                                widget.setCurrentIndex(i)
                                break
            
            self.documents_list_widget.clear()
            self.files_to_upload.clear() 
            existing_documents = api_response.get("documents", [])
            for doc in existing_documents:
                item_text = doc.get("filename", "Documento Desconhecido")
                if doc.get("s3_key"): 
                    list_item = QListWidgetItem(f"[Salvo] {item_text}")
                    list_item.setData(Qt.ItemDataRole.UserRole, {"s3_key": doc.get("s3_key"), "filename": item_text, "type": "existing"})
                else: 
                    list_item = QListWidgetItem(item_text)
                self.documents_list_widget.addItem(list_item)
        else:
            error_msg = "Não foi possível carregar os dados do processo."
            if isinstance(api_response, dict):
                error_msg = api_response.get("message", "Não foi possível carregar os dados do processo para edição.")
            QMessageBox.critical(self, "Erro ao Carregar Dados", error_msg)
            ok_button = self.button_box.button(QDialogButtonBox.StandardButton.Ok)
            if ok_button:
                ok_button.setEnabled(False)

    @Slot()
    def select_document_to_attach(self):
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Selecionar Documentos PDF para Anexar",
            "", 
            "Documentos PDF (*.pdf);;Todos os Ficheiros (*)"
        )
        if file_paths:
            for path in file_paths:
                file_info = QFileInfo(path)
                if not any(f_info.absoluteFilePath() == file_info.absoluteFilePath() for f_info in self.files_to_upload):
                    self.files_to_upload.append(file_info)
                    list_item = QListWidgetItem(f"[Novo] {file_info.fileName()}")
                    list_item.setData(Qt.ItemDataRole.UserRole, {"file_info": file_info, "type": "new"})
                    self.documents_list_widget.addItem(list_item)
            print(f"ProcessFormDialog: {len(self.files_to_upload)} ficheiros selecionados para upload.")

    def accept_data(self):
        print("ProcessFormDialog: accept_data chamado.")
        process_data_payload = {}
        has_errors = False

        for label_text, attr_name, WidgetClass, is_required, _ in ProcessFormDialog_pyside.STATIC_PROCESS_FIELDS_CONFIG:
            widget = self.entries[attr_name]
            value_str = ""
            
            if isinstance(widget, QLineEdit):
                value_str = widget.text().strip()
            elif isinstance(widget, QTextEdit):
                value_str = widget.toPlainText().strip()
            elif isinstance(widget, QComboBox) and attr_name == "client_cpf":
                selected_data = widget.currentData() 
                if selected_data:
                    value_str = str(selected_data)
                else: 
                    value_str = "" 

            if is_required and not value_str:
                QMessageBox.warning(self, "Campo Obrigatório", f"O campo '{label_text.replace(':', '')}' é obrigatório.")
                widget.setFocus() 
                has_errors = True
                break 
            
            if value_str: 
                process_data_payload[attr_name] = value_str
        
        if has_errors:
            return

        print(f"ProcessFormDialog: Dados do processo para API (payload): {process_data_payload}")
        
        files_data_for_api = []
        if self.files_to_upload:
            for file_info in self.files_to_upload:
                try:
                    with open(file_info.absoluteFilePath(), 'rb') as f:
                        files_data_for_api.append(
                            ('process_documents', (file_info.fileName(), f.read(), 'application/pdf'))
                        )
                except Exception as e:
                    QMessageBox.critical(self, "Erro ao Ler Ficheiro", f"Não foi possível ler o ficheiro {file_info.fileName()}: {e}")
                    return
            print(f"ProcessFormDialog: {len(files_data_for_api)} ficheiros preparados para envio.")

        api_response = None
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            if self.process_id_to_edit:
                print(f"ProcessFormDialog: Chamando process_api_service.update_process para user: {self.user_id}, process_id: {self.process_id_to_edit}")
                api_response = self.process_api_service.update_process(self.user_id, self.process_id_to_edit, process_data_payload, files_data_for_api if files_data_for_api else None)
            else:
                print(f"ProcessFormDialog: Chamando process_api_service.add_process para user: {self.user_id}")
                api_response = self.process_api_service.add_process(self.user_id, process_data_payload, files_data_for_api if files_data_for_api else None)
        finally:
            QApplication.restoreOverrideCursor()

        print(f"ProcessFormDialog: Resposta da API: {api_response}")
        if api_response and api_response.get("success"):
            msg = api_response.get("message", f"Processo {'atualizado' if self.process_id_to_edit else 'adicionado'} com sucesso!")
            QMessageBox.information(self, "Sucesso", msg)
            self.accept() 
        else:
            error_msg = "Falha na operação com a API de Processos."
            if isinstance(api_response, dict):
                error_msg = api_response.get("message", f"Não foi possível {'atualizar' if self.process_id_to_edit else 'adicionar'} o processo via API.")
            QMessageBox.critical(self, "Erro na Operação", error_msg)

# process_form_dialog_pyside.py

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLineEdit, QTextEdit, # QFormLayout removido, QGridLayout adicionado
    QDialogButtonBox, QMessageBox, QPushButton, QFileDialog,
    QListWidget, QAbstractItemView, QComboBox, QLabel, QApplication,
    QListWidgetItem, QCompleter, QSizePolicy # QSizePolicy adicionado
)
from PySide6.QtCore import Qt, Slot, QFileInfo, QRegularExpression, QStringListModel 
from PySide6.QtGui import QRegularExpressionValidator 
from typing import List, Dict, Optional, Any

class ProcessFormDialog_pyside(QDialog):
    """
    Diálogo para adicionar ou editar um processo jurídico,
    com máscaras de entrada, remoção de arquivos e autocompletar para clientes.
    Layout refeito com QGridLayout para melhor controle e evitar sobreposição.
    """
    # Configuração dos campos: (Label, attr_name, WidgetClass, is_required, placeholder/items, input_mask/regex_validator_config, widget_min_height)
    # O sétimo elemento (widget_min_height) é opcional, para QTextEdit
    STATIC_PROCESS_FIELDS_CONFIG = [
        ("Número do Processo:", "numero_processo", QLineEdit, True, "Ex: 0710804-61.2024.8.02.0001", "0000000-00.0000.0.00.0000;_"), 
        ("Cliente Associado:", "client_cpf", QComboBox, True, [], None), 
        ("Vara:", "vara", QLineEdit, False, "Ex: 1ª Vara Cível da Comarca de...", None),
        ("Juízo:", "juizo", QLineEdit, False, "Ex: Tribunal de Justiça Estadual de...", None),
        ("Comarca:", "comarca", QLineEdit, False, "Ex: Comarca da Capital", None),
        ("Classe Judicial:", "classe_judicial", QLineEdit, False, "Ex: Procedimento Comum Cível", None),
        ("Assuntos (separados por vírgula):", "assuntos", QTextEdit, False, "Ex: Direito Civil, Contratos, Indenização por Dano Moral", None, 80), 
        ("Valor da Causa (R$):", "valor_causa", QLineEdit, False, "Ex: 15000.00", 
         (QRegularExpression(r"^\d{1,9}(\.\d{2})?$"), "Valor inválido. Use números e até duas casas decimais (ex: 1234.56).")),
        ("Fase Atual:", "fase_atual", QLineEdit, False, "Ex: Inicial, Instrução, Recursal, Execução", None),
        ("Observações:", "observacoes", QTextEdit, False, "Detalhes adicionais, próximos passos, informações relevantes...", None, 100), 
        ("Data de Distribuição:", "data_distribuicao", QLineEdit, False, "DD/MM/AAAA", "00/00/0000;_"), 
        ("Link do Processo (Tribunal):", "link_processo_externo", QLineEdit, False, "URL para consulta pública do processo", None)
    ]

    def __init__(self, process_api_service, client_api_service, user_id: str, clients_list: List[Dict[str, str]], process_id_to_edit: Optional[str] = None, parent=None):
        super().__init__(parent)
        self.process_api_service = process_api_service
        self.client_api_service = client_api_service 
        self.user_id = user_id
        self.clients_list_data = clients_list 
        self.process_id_to_edit = process_id_to_edit
        self.process_data_to_edit: Optional[Dict[str, Any]] = None
        self.document_items_state: List[Dict[str, Any]] = [] 

        self.setWindowTitle("Adicionar Novo Processo" if not self.process_id_to_edit else "Editar Processo")
        # Ajustar tamanhos mínimos conforme necessário, QGridLayout é mais flexível
        self.setMinimumWidth(700) 
        self.resize(750, 800) # Permitir um tamanho inicial maior

        main_layout = QVBoxLayout(self)
        
        # Usar QGridLayout para o formulário principal
        form_grid_layout = QGridLayout()
        form_grid_layout.setColumnStretch(1, 1) # Faz a coluna dos campos de entrada expandir
        form_grid_layout.setVerticalSpacing(10) # Adiciona espaçamento vertical entre as linhas
        form_grid_layout.setHorizontalSpacing(5) # Espaçamento horizontal

        self.entries: Dict[str, QLineEdit | QTextEdit | QComboBox] = {}
        current_row = 0
        for config_item in ProcessFormDialog_pyside.STATIC_PROCESS_FIELDS_CONFIG:
            label_text, attr_name, WidgetClass, _, placeholder_or_items = config_item[:5]
            mask_or_validator_config = config_item[5] if len(config_item) > 5 else None
            widget_min_height = config_item[6] if len(config_item) > 6 else None

            label_widget = QLabel(label_text)
            # Alinhar o label ao topo se o widget do campo for potencialmente alto (QTextEdit)
            if WidgetClass == QTextEdit:
                label_widget.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
            else:
                label_widget.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)


            if WidgetClass == QComboBox and attr_name == "client_cpf":
                widget = QComboBox()
                widget.setEditable(True) 
                widget.setInsertPolicy(QComboBox.NoInsert) 
                widget.addItem("Selecione ou digite para buscar...", None) 
                
                client_display_list = []
                for client in self.clients_list_data:
                    display_text = f"{client.get('nome_completo', 'Nome Desconhecido')} (CPF: {client.get('client_cpf', 'N/A')})"
                    widget.addItem(display_text, client.get('client_cpf'))
                    client_display_list.append(display_text)
                
                if not self.clients_list_data:
                    widget.setEnabled(False)
                    widget.addItem("Nenhum cliente cadastrado", None)
                
                self.client_completer_model = QStringListModel(client_display_list, self)
                self.client_completer = QCompleter(self.client_completer_model, self)
                self.client_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
                self.client_completer.setFilterMode(Qt.MatchFlag.MatchContains) 
                widget.setCompleter(self.client_completer)
                label_widget.setToolTip("Selecione o cliente ou comece a digitar o nome/CPF para filtrar.")

            elif WidgetClass == QTextEdit:
                widget = WidgetClass()
                widget.setPlaceholderText(str(placeholder_or_items))
                if widget_min_height:
                    widget.setMinimumHeight(widget_min_height)
                # Permitir que QTextEdit expanda verticalmente
                widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding) 
                label_widget.setToolTip(str(placeholder_or_items))
            elif WidgetClass == QLineEdit:
                widget = QLineEdit()
                widget.setPlaceholderText(str(placeholder_or_items))
                label_widget.setToolTip(str(placeholder_or_items))
                if mask_or_validator_config:
                    if isinstance(mask_or_validator_config, str): 
                        widget.setInputMask(mask_or_validator_config)
                    elif isinstance(mask_or_validator_config, tuple) and isinstance(mask_or_validator_config[0], QRegularExpression):
                        regex, _ = mask_or_validator_config
                        validator = QRegularExpressionValidator(regex, widget)
                        widget.setValidator(validator)
            else: 
                widget = WidgetClass()

            self.entries[attr_name] = widget
            form_grid_layout.addWidget(label_widget, current_row, 0)
            form_grid_layout.addWidget(widget, current_row, 1)
            current_row += 1
        
        main_layout.addLayout(form_grid_layout)

        docs_group_label = QLabel("<b>Documentos do Processo:</b>")
        docs_group_label.setToolTip("Anexe arquivos PDF relevantes para este processo.")
        main_layout.addWidget(docs_group_label)
        
        self.documents_list_widget = QListWidget()
        self.documents_list_widget.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.documents_list_widget.setToolTip("Lista de documentos. Selecione um item e clique em 'Remover' para desanexar.")
        self.documents_list_widget.setFixedHeight(100) 
        main_layout.addWidget(self.documents_list_widget)

        document_buttons_layout = QHBoxLayout()
        add_doc_button = QPushButton("Anexar Novo Documento (PDF)")
        add_doc_button.setToolTip("Clique para selecionar um ou mais arquivos PDF para adicionar ao processo.")
        add_doc_button.clicked.connect(self.select_document_to_attach)
        document_buttons_layout.addWidget(add_doc_button)
        
        remove_doc_button = QPushButton("Remover Documento Selecionado")
        remove_doc_button.setToolTip("Remove o documento selecionado da lista.")
        remove_doc_button.clicked.connect(self.remove_selected_document_from_list)
        document_buttons_layout.addWidget(remove_doc_button)
        
        main_layout.addLayout(document_buttons_layout)
        
        main_layout.addStretch(1) # Empurra os botões OK/Cancelar para baixo

        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.button(QDialogButtonBox.StandardButton.Ok).setText("Salvar Processo")
        self.button_box.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        self.button_box.accepted.connect(self.accept_data)
        self.button_box.rejected.connect(self.reject)
        main_layout.addWidget(self.button_box)

        self.setLayout(main_layout)

        if self.process_id_to_edit:
            self.load_process_data_for_edit()

    def load_process_data_for_edit(self):
        # ... (código existente, sem alterações necessárias aqui para o layout) ...
        if not self.process_id_to_edit: return
        print(f"ProcessFormDialog: Carregando dados para editar processo ID {self.process_id_to_edit}")
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            api_response = self.process_api_service.get_process_details(self.user_id, self.process_id_to_edit)
        finally:
            QApplication.restoreOverrideCursor()
        
        if api_response and api_response.get("success") and "process" in api_response:
            self.process_data_to_edit = api_response["process"]
            
            for config_item in ProcessFormDialog_pyside.STATIC_PROCESS_FIELDS_CONFIG:
                attr_name = config_item[1]
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
            self.document_items_state.clear() 
            existing_documents = self.process_data_to_edit.get("documents", [])
            for doc in existing_documents:
                item_text = doc.get("filename", "Documento Desconhecido")
                s3_key = doc.get("s3_key")
                if s3_key: 
                    list_item = QListWidgetItem(f"[Salvo] {item_text}")
                    doc_state = {"s3_key": s3_key, "filename": item_text, "type": "existing", "original_data": doc}
                    list_item.setData(Qt.ItemDataRole.UserRole, doc_state)
                    self.document_items_state.append(doc_state)
                else: 
                    list_item = QListWidgetItem(f"[Info] {item_text}") 
                self.documents_list_widget.addItem(list_item)
        else:
            error_msg = "Não foi possível carregar os dados do processo."
            if isinstance(api_response, dict):
                error_msg = api_response.get("message", "Não foi possível carregar os dados do processo para edição.")
            QMessageBox.critical(self, "Erro ao Carregar Dados", error_msg)
            ok_button = self.button_box.button(QDialogButtonBox.StandardButton.Ok)
            if ok_button: ok_button.setEnabled(False)


    @Slot()
    def select_document_to_attach(self):
        # ... (código existente, sem alterações necessárias aqui para o layout) ...
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, "Selecionar Documentos PDF para Anexar", "", 
            "Documentos PDF (*.pdf);;Todos os Ficheiros (*)"
        )
        if file_paths:
            for path in file_paths:
                file_info = QFileInfo(path)
                is_already_listed = any(
                    (item_state.get("type") == "new" and item_state.get("file_info").absoluteFilePath() == file_info.absoluteFilePath()) or
                    (item_state.get("type") == "existing" and item_state.get("filename") == file_info.fileName())
                    for item_state in self.document_items_state
                )
                
                if not is_already_listed:
                    doc_state = {"file_info": file_info, "filename": file_info.fileName(), "type": "new"}
                    self.document_items_state.append(doc_state)
                    list_item = QListWidgetItem(f"[Novo] {file_info.fileName()}")
                    list_item.setData(Qt.ItemDataRole.UserRole, doc_state) 
                    self.documents_list_widget.addItem(list_item)
                else:
                     QMessageBox.information(self, "Documento Já Listado", f"O documento '{file_info.fileName()}' já está na lista ou salvo neste processo.")
            print(f"ProcessFormDialog: {len([s for s in self.document_items_state if s['type'] == 'new'])} novos ficheiros para upload.")
    
    @Slot()
    def remove_selected_document_from_list(self):
        # ... (código existente, sem alterações necessárias aqui para o layout) ...
        selected_items = self.documents_list_widget.selectedItems()
        if not selected_items:
            QMessageBox.information(self, "Nenhum Documento Selecionado", "Por favor, selecione um documento da lista para remover.")
            return
        
        list_item_to_remove = selected_items[0]
        item_data = list_item_to_remove.data(Qt.ItemDataRole.UserRole) 

        if item_data:
            self.document_items_state = [s for s in self.document_items_state if s != item_data]
            self.documents_list_widget.takeItem(self.documents_list_widget.row(list_item_to_remove))
            print(f"ProcessFormDialog: Documento '{item_data.get('filename')}' removido da lista de upload/manutenção.")
            
            if item_data.get("type") == "existing":
                 QMessageBox.information(self, "Documento Removido da Lista", 
                                        f"O documento '{item_data.get('filename')}' foi removido da lista.\n"
                                        "Ele não será excluído do servidor até que você salve as alterações no processo.\n"
                                        "A API de atualização precisará ser ajustada para lidar com a remoção de documentos existentes se essa funcionalidade for desejada.")
        else:
            self.documents_list_widget.takeItem(self.documents_list_widget.row(list_item_to_remove))


    def accept_data(self):
        # ... (código existente, sem alterações necessárias aqui para o layout) ...
        print("ProcessFormDialog: accept_data chamado.")
        process_data_payload = {}
        has_errors = False

        for config_item in ProcessFormDialog_pyside.STATIC_PROCESS_FIELDS_CONFIG:
            label_text, attr_name, WidgetClass, is_required, _, mask_or_validator_config = config_item[:6] \
                if len(config_item) > 5 else config_item + (None,)
            widget = self.entries[attr_name]
            value_str = ""
            
            if isinstance(widget, QLineEdit):
                value_str = widget.text()
                if isinstance(mask_or_validator_config, tuple) and isinstance(mask_or_validator_config[0], QRegularExpression):
                    validator = widget.validator()
                    if validator:
                        state, _, _ = validator.validate(value_str, 0)
                        if state != QRegularExpressionValidator.State.Acceptable and (value_str.strip() != "" or is_required):
                            _, error_message = mask_or_validator_config
                            QMessageBox.warning(self, "Campo Inválido", f"O campo '{label_text.replace(':', '')}' contém um valor inválido. {error_message}")
                            widget.setFocus(); has_errors = True; break
                value_str = value_str.strip()
            elif isinstance(widget, QTextEdit):
                value_str = widget.toPlainText().strip()
            elif isinstance(widget, QComboBox) and attr_name == "client_cpf":
                current_index = widget.currentIndex()
                if current_index > 0: 
                    selected_data = widget.itemData(current_index)
                    if selected_data: value_str = str(selected_data)
                    else: value_str = "" 
                else: 
                    edited_text = widget.lineEdit().text().strip() if widget.lineEdit() else ""
                    if edited_text:
                        found_in_model = False
                        for i in range(self.client_completer_model.rowCount()):
                            model_text = self.client_completer_model.data(self.client_completer_model.index(i, 0), Qt.ItemDataRole.DisplayRole)
                            if edited_text.lower() in model_text.lower(): 
                                original_combo_index = -1
                                for cb_idx in range(widget.count()):
                                    if widget.itemText(cb_idx) == model_text:
                                        original_combo_index = cb_idx
                                        break
                                if original_combo_index > 0:
                                    cpf_data = widget.itemData(original_combo_index)
                                    if cpf_data:
                                        value_str = str(cpf_data)
                                        widget.setCurrentIndex(original_combo_index) 
                                        found_in_model = True
                                        break
                        if not found_in_model:
                             QMessageBox.warning(self, "Cliente Inválido", f"Cliente '{edited_text}' não encontrado. Por favor, selecione um cliente da lista ou digite um nome/CPF válido que corresponda a um cliente existente.")
                             widget.setFocus(); has_errors = True; break
                    else: 
                        value_str = ""

            if is_required and not value_str:
                QMessageBox.warning(self, "Campo Obrigatório", f"O campo '{label_text.replace(':', '')}' é obrigatório.")
                widget.setFocus(); has_errors = True; break 
            
            process_data_payload[attr_name] = value_str
        
        if has_errors: return
        
        if self.process_id_to_edit:
            final_document_metadata_for_api = []
            for item_state in self.document_items_state:
                if item_state["type"] == "existing":
                    final_document_metadata_for_api.append(item_state["original_data"]) 
            process_data_payload['documents'] = final_document_metadata_for_api

        print(f"ProcessFormDialog: Dados do processo para API (payload): {process_data_payload}")
        
        files_data_for_api = [] 
        for item_state in self.document_items_state:
            if item_state["type"] == "new":
                file_info = item_state["file_info"]
                try:
                    if not file_info.exists():
                        QMessageBox.warning(self, "Arquivo Não Encontrado", f"O arquivo '{file_info.fileName()}' não foi encontrado e não será enviado.")
                        continue
                    with open(file_info.absoluteFilePath(), 'rb') as f:
                        files_data_for_api.append(
                            ('process_documents', (file_info.fileName(), f.read(), 'application/pdf'))
                        )
                except Exception as e:
                    QMessageBox.critical(self, "Erro ao Ler Ficheiro", f"Não foi possível ler o ficheiro {file_info.fileName()}: {e}")
                    return 
        print(f"ProcessFormDialog: {len(files_data_for_api)} novos ficheiros preparados para envio.")

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


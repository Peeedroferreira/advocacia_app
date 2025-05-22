from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QDialog, QDialogButtonBox, QFormLayout, QScrollArea, QFrame, QSplitter,
    QTextEdit, QSpacerItem, QSizePolicy, QApplication
)
from PySide6.QtCore import Qt, Slot, QTimer
from PySide6.QtGui import QFont

# Este ficheiro NÃO DEVE importar DynamoDBClientHandler diretamente
# Ele recebe e usa uma instância de ClientApiService

class ClientFormDialog_pyside(QDialog):
    # Definição estática da configuração dos campos do formulário
    STATIC_FIELDS_CONFIG = [
        ("Nome Completo:", "nome_completo", QLineEdit, True, "Nome completo do cliente"),
        ("CPF:", "client_cpf", QLineEdit, True, "000.000.000-00"),
        ("Nacionalidade:", "nacionalidade", QLineEdit, False, "Ex: Brasileira"),
        ("Estado Civil:", "estado_civil", QLineEdit, False, "Ex: Solteiro(a), Casado(a)"),
        ("Profissão:", "profissao", QLineEdit, False, "Ex: Engenheiro(a)"),
        ("Data de Nascimento:", "data_nascimento", QLineEdit, False, "DD/MM/AAAA"),
        ("RG:", "rg", QLineEdit, False, "Número do RG"),
        ("Órgão Emissor RG:", "rg_orgao_emissor", QLineEdit, False, "Ex: SSP"),
        ("UF RG:", "rg_uf", QLineEdit, False, "Ex: SP"),
        ("CNH:", "cnh", QLineEdit, False, "Número da CNH"),
        ("NIS/PIS/PASEP:", "nis_pis_pasep", QLineEdit, False, "Número"),
        ("Telefone Celular:", "telefone_celular", QLineEdit, True, "(XX) XXXXX-XXXX"),
        ("Telefone Fixo:", "telefone_fixo", QLineEdit, False, "(XX) XXXX-XXXX"),
        ("E-mail:", "email", QLineEdit, False, "email@exemplo.com"),
        ("Endereço - Rua:", "endereco_rua", QLineEdit, False, "Nome da rua/avenida"),
        ("Número:", "endereco_numero", QLineEdit, False, "Número"),
        ("Complemento:", "endereco_complemento", QLineEdit, False, "Apto, Bloco, etc."),
        ("Bairro:", "endereco_bairro", QLineEdit, False, "Nome do bairro"),
        ("Cidade:", "endereco_cidade", QLineEdit, False, "Nome da cidade"),
        ("Estado (UF):", "endereco_estado", QLineEdit, False, "Ex: SP"),
        ("CEP:", "endereco_cep", QLineEdit, False, "00000-000"),
        ("Empresa (onde trabalha):", "empresa", QLineEdit, False, "Nome da empresa"),
        ("Cargo:", "cargo", QLineEdit, False, "Cargo na empresa"),
        ("End. Profissional:", "endereco_profissional", QTextEdit, False, "Endereço completo do trabalho"), 
        ("Tel. Profissional:", "telefone_profissional", QLineEdit, False, "(XX) XXXX-XXXX"),
        ("Nome do Cônjuge:", "conjuge_nome", QLineEdit, False, "Nome completo do cônjuge"),
        ("Nomes dos Filhos (separados por vírgula):", "filhos_nomes", QTextEdit, False, "Filho 1, Filho 2..."),
        ("Dependentes Legais (separados por vírgula):", "dependentes_legais", QTextEdit, False, "Dependente 1, Dependente 2..."),
        ("Documentos/Informações Complementares:", "documentos_complementares", QTextEdit, False, "Outras informações relevantes, referências de documentos...")
    ]

    # O construtor agora recebe client_api_service
    def __init__(self, client_api_service, user_id, client_cpf_to_edit=None, parent=None):
        super().__init__(parent)
        self.client_api_service = client_api_service # Armazena a instância do serviço de API
        self.user_id = user_id
        self.client_cpf_to_edit = client_cpf_to_edit 
        self.client_data_to_edit = None

        self.setWindowTitle("Adicionar Novo Cliente" if not client_cpf_to_edit else "Editar Cliente")
        self.setMinimumWidth(550) 
        self.setMinimumHeight(650) # Ajuste a altura conforme necessário para todos os campos

        self.layout = QVBoxLayout(self)
        
        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        self.layout.addWidget(scroll_area)
        
        form_widget = QWidget()
        self.form_layout = QFormLayout(form_widget)
        self.form_layout.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows) 
        form_widget.setLayout(self.form_layout)
        scroll_area.setWidget(form_widget)
        
        self.entries = {}
        for label, attr_name, WidgetClass, _, placeholder in ClientFormDialog_pyside.STATIC_FIELDS_CONFIG:
            entry = WidgetClass()
            if isinstance(entry, QLineEdit):
                entry.setPlaceholderText(placeholder)
            elif isinstance(entry, QTextEdit):
                entry.setPlaceholderText(placeholder) 
                entry.setMinimumHeight(60) # Altura mínima para QTextEdit
            self.form_layout.addRow(label, entry)
            self.entries[attr_name] = entry
        
        if self.client_cpf_to_edit:
            self.load_client_data_for_edit() # Este método usará self.client_api_service
            if "client_cpf" in self.entries: 
                self.entries["client_cpf"].setReadOnly(True) # CPF não editável na edição

        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept_data) # Conecta ao método que usa a API
        self.button_box.rejected.connect(self.reject)
        self.layout.addWidget(self.button_box)

    def load_client_data_for_edit(self):
        print(f"ClientFormDialog: Carregando dados para editar cliente CPF {self.client_cpf_to_edit} para utilizador {self.user_id}")
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            # USA O CLIENT_API_SERVICE
            api_response = self.client_api_service.get_client(self.user_id, self.client_cpf_to_edit)
        finally:
            QApplication.restoreOverrideCursor()
        
        if api_response and api_response.get("success") and "client" in api_response:
            self.client_data_to_edit = api_response["client"]
            for label, attr_name, WidgetClass, _, _ in ClientFormDialog_pyside.STATIC_FIELDS_CONFIG:
                widget = self.entries.get(attr_name)
                value = self.client_data_to_edit.get(attr_name)
                if widget and value is not None:
                    if isinstance(widget, QLineEdit):
                        widget.setText(str(value))
                    elif isinstance(widget, QTextEdit):
                        if attr_name in ["filhos_nomes", "dependentes_legais"] and isinstance(value, list):
                             widget.setPlainText(", ".join(map(str,value))) 
                        else:
                             widget.setPlainText(str(value))
        else:
            error_msg = "Não foi possível carregar os dados do cliente."
            if isinstance(api_response, dict): # Verifica se api_response é um dict
                error_msg = api_response.get("message", "Não foi possível carregar os dados do cliente para edição.")
            QMessageBox.critical(self, "Erro ao Carregar Dados", error_msg)
            ok_button = self.button_box.button(QDialogButtonBox.StandardButton.Ok)
            if ok_button:
                ok_button.setEnabled(False)

    def accept_data(self):
        print("ClientFormDialog: accept_data chamado. Usando ClientApiService.") # DEBUG
        client_data_payload = {}
        for label, attr_name, WidgetClass, is_required, _ in ClientFormDialog_pyside.STATIC_FIELDS_CONFIG:
            widget = self.entries[attr_name]
            value_str = ""
            if isinstance(widget, QLineEdit):
                value_str = widget.text().strip()
            elif isinstance(widget, QTextEdit):
                value_str = widget.toPlainText().strip()

            if is_required and not value_str:
                QMessageBox.warning(self, "Campo Obrigatório", f"O campo '{label}' é obrigatório.")
                return
            
            if value_str: # Só adiciona ao payload se tiver valor
                if attr_name in ["filhos_nomes", "dependentes_legais"]:
                    client_data_payload[attr_name] = [name.strip() for name in value_str.split(',') if name.strip()]
                else:
                    client_data_payload[attr_name] = value_str
        
        if not self.client_cpf_to_edit: 
            cpf_value_from_entry = self.entries['client_cpf'].text().strip()
            if not cpf_value_from_entry:
                 QMessageBox.warning(self, "Campo Obrigatório", "O campo 'CPF' é obrigatório.")
                 return
            client_data_payload['client_cpf'] = cpf_value_from_entry
        else: # Em edição, CPF não vai no payload de atributos, vai na URL
            client_data_payload.pop('client_cpf', None)

        print(f"ClientFormDialog: Dados do cliente para API (payload): {client_data_payload}")

        api_response = None
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            if self.client_cpf_to_edit:
                # USA O CLIENT_API_SERVICE
                print(f"ClientFormDialog: Chamando client_api_service.update_client para user: {self.user_id}, cpf: {self.client_cpf_to_edit}")
                api_response = self.client_api_service.update_client(self.user_id, self.client_cpf_to_edit, client_data_payload)
            else:
                # USA O CLIENT_API_SERVICE
                print(f"ClientFormDialog: Chamando client_api_service.add_client para user: {self.user_id}")
                api_response = self.client_api_service.add_client(self.user_id, client_data_payload)
        finally:
            QApplication.restoreOverrideCursor()

        print(f"ClientFormDialog: Resposta da API: {api_response}")
        if api_response and api_response.get("success"):
            msg = api_response.get("message", f"Cliente {'atualizado' if self.client_cpf_to_edit else 'adicionado'} com sucesso!")
            QMessageBox.information(self, "Sucesso", msg)
            self.accept() # Fecha o diálogo com sucesso
        else:
            error_msg = "Falha na operação com a API."
            if isinstance(api_response, dict):
                error_msg = api_response.get("message", f"Não foi possível {'atualizar' if self.client_cpf_to_edit else 'adicionar'} o cliente via API.")
            QMessageBox.critical(self, "Erro na Operação", error_msg)


class ClientsTab_pyside(QWidget):
    # O construtor agora recebe client_api_service
    def __init__(self, user_id, client_api_service, parent=None):
        super().__init__(parent)
        self.user_id = user_id
        self.client_api_service = client_api_service # Armazena a instância do serviço de API
        self.selected_client_cpf = None
        
        print(f"ClientsTab_pyside: Instanciada com user_id: {self.user_id} e client_api_service: {type(self.client_api_service)}")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)

        action_bar_layout = QHBoxLayout()
        self.search_entry = QLineEdit()
        self.search_entry.setPlaceholderText("Buscar por Nome ou CPF...")
        self.search_entry.textChanged.connect(self.filter_clients_display)
        action_bar_layout.addWidget(self.search_entry)

        add_client_btn = QPushButton("Adicionar Cliente")
        add_client_btn.clicked.connect(self.open_add_client_dialog) # Chama o método que usa a API
        action_bar_layout.addWidget(add_client_btn)
        main_layout.addLayout(action_bar_layout)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)

        self.clients_table = QTableWidget()
        self.clients_table.setColumnCount(3) 
        self.clients_table.setHorizontalHeaderLabels(["Nome Completo", "CPF", "Celular"])
        self.clients_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.clients_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self.clients_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.clients_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.clients_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.clients_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.clients_table.itemSelectionChanged.connect(self.on_client_selected_from_table)
        self.splitter.addWidget(self.clients_table)

        self.client_details_area = QScrollArea()
        self.client_details_area.setWidgetResizable(True)
        self.client_details_content_widget = QWidget()
        self.client_details_layout = QVBoxLayout(self.client_details_content_widget)
        self.client_details_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.client_details_area.setWidget(self.client_details_content_widget)
        
        self.edit_client_btn = QPushButton("Editar Cliente Selecionado")
        self.edit_client_btn.clicked.connect(self.open_edit_client_dialog) # Chama o método que usa a API
        self.edit_client_btn.setEnabled(False)
        self.client_details_layout.addWidget(self.edit_client_btn)

        self.delete_client_btn = QPushButton("Remover Cliente Selecionado")
        self.delete_client_btn.clicked.connect(self.delete_selected_client) # Chama o método que usa a API
        self.delete_client_btn.setEnabled(False)
        self.client_details_layout.addWidget(self.delete_client_btn)
        
        self.details_spacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        self.details_labels_widgets = [] 

        self.splitter.addWidget(self.client_details_area)
        self.splitter.setStretchFactor(0, 2) 
        self.splitter.setStretchFactor(1, 1)

        main_layout.addWidget(self.splitter)
        self.setLayout(main_layout)

        self.load_clients_from_api() # Carrega clientes ao iniciar, usando a API

    def load_clients_from_api(self, search_term=""):
        print(f"ClientsTab: load_clients_from_api. User ID: {self.user_id}, Busca: '{search_term}'")
        self.clients_table.setRowCount(0)
        if not self.user_id:
            print("ClientsTab: ERRO - user_id não definido em load_clients_from_api.")
            QMessageBox.critical(self, "Erro Interno", "ID do utilizador não está disponível para carregar clientes.")
            return
        
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            # USA O CLIENT_API_SERVICE
            api_response = self.client_api_service.get_clients_by_user(self.user_id)
        finally:
            QApplication.restoreOverrideCursor()
        
        all_clients_data = []
        if api_response and api_response.get("success") and "clients" in api_response:
            all_clients_data = api_response["clients"]
            print(f"ClientsTab: {len(all_clients_data)} clientes recebidos da API.")
        elif api_response and not api_response.get("success"): # Erro da API, mas resposta recebida
             QMessageBox.warning(self, "Erro ao Carregar Clientes", api_response.get("message", "Não foi possível buscar os clientes do servidor."))
        else: # Resposta inesperada ou None
             QMessageBox.warning(self, "Erro ao Carregar Clientes", "Resposta inesperada ou falha de comunicação ao buscar clientes.")

        filtered_clients = []
        if search_term:
            search_lower = search_term.lower()
            for client in all_clients_data:
                if (search_lower in client.get("nome_completo", "").lower() or
                    search_lower in client.get("client_cpf", "")):
                    filtered_clients.append(client)
        else:
            filtered_clients = all_clients_data

        self.clients_table.setSortingEnabled(False)
        for row, client_item in enumerate(filtered_clients):
            self.clients_table.insertRow(row)
            self.clients_table.setItem(row, 0, QTableWidgetItem(client_item.get("nome_completo", "N/A")))
            self.clients_table.setItem(row, 1, QTableWidgetItem(client_item.get("client_cpf", "N/A")))
            self.clients_table.setItem(row, 2, QTableWidgetItem(client_item.get("telefone_celular", "N/A")))
        self.clients_table.setSortingEnabled(True)
        
        self.clear_client_details()
        self.edit_client_btn.setEnabled(False)
        self.delete_client_btn.setEnabled(False)

    @Slot()
    def filter_clients_display(self):
        search_term = self.search_entry.text()
        self.load_clients_from_api(search_term)

    @Slot() 
    def on_client_selected_from_table(self):
        selected_items = self.clients_table.selectedItems()
        if selected_items:
            selected_row = self.clients_table.row(selected_items[0]) 
            cpf_item = self.clients_table.item(selected_row, 1) 
            if cpf_item:
                self.selected_client_cpf = cpf_item.text()
                print(f"ClientsTab: Cliente selecionado da tabela - CPF {self.selected_client_cpf}")
                self.display_client_details(self.selected_client_cpf) # Usa a API
                self.edit_client_btn.setEnabled(True)
                self.delete_client_btn.setEnabled(True)
                return
        
        self.selected_client_cpf = None
        self.clear_client_details()
        self.edit_client_btn.setEnabled(False)
        self.delete_client_btn.setEnabled(False)

    def display_client_details(self, client_cpf_to_display):
        self.clear_client_details_content() 
        print(f"ClientsTab: display_client_details para CPF {client_cpf_to_display}")

        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            # USA O CLIENT_API_SERVICE
            api_response = self.client_api_service.get_client(self.user_id, client_cpf_to_display)
        finally:
            QApplication.restoreOverrideCursor()

        if api_response and api_response.get("success") and "client" in api_response:
            client_info = api_response["client"]
            dialog_fields_map = {item[1]: item[0].replace(":", "") for item in ClientFormDialog_pyside.STATIC_FIELDS_CONFIG}

            for i in reversed(range(self.client_details_layout.count())):
                item = self.client_details_layout.itemAt(i)
                if item and isinstance(item, QSpacerItem):
                    self.client_details_layout.takeAt(i) 
                    break 

            for attr_name, friendly_label_text in dialog_fields_map.items():
                value = client_info.get(attr_name)
                if value is not None and str(value).strip() != "": 
                    if isinstance(value, list): value_str = ", ".join(map(str,value))
                    else: value_str = str(value)
                    
                    detail_label_title = QLabel(f"<b>{friendly_label_text}:</b>")
                    detail_label_value = QLabel(value_str)
                    detail_label_value.setWordWrap(True)
                    
                    self.client_details_layout.addWidget(detail_label_title)
                    self.client_details_layout.addWidget(detail_label_value)
                    self.details_labels_widgets.append(detail_label_title)
                    self.details_labels_widgets.append(detail_label_value)
            
            self.client_details_layout.addSpacerItem(self.details_spacer)
        else:
            error_msg = "Detalhes do cliente não encontrados."
            if isinstance(api_response, dict):
                error_msg = api_response.get("message", "Detalhes do cliente não encontrados ou erro ao buscar via API.")
            no_details_label = QLabel(error_msg)
            self.client_details_layout.addWidget(no_details_label)
            self.details_labels_widgets.append(no_details_label)
            self.client_details_layout.addSpacerItem(self.details_spacer)

    def clear_client_details_content(self):
        for widget in self.details_labels_widgets:
            widget.deleteLater()
        self.details_labels_widgets.clear()
        
        if self.client_details_layout.count() > 2: 
            last_item_index = self.client_details_layout.count() - 1
            last_item = self.client_details_layout.itemAt(last_item_index)
            if last_item and isinstance(last_item, QSpacerItem):
                self.client_details_layout.takeAt(last_item_index)

    def clear_client_details(self):
        self.clear_client_details_content()

    def open_add_client_dialog(self):
        print("ClientsTab: open_add_client_dialog chamado.")
        # Passa self.client_api_service e self.user_id para o diálogo
        dialog = ClientFormDialog_pyside(self.client_api_service, self.user_id, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_clients_from_api() # Recarrega da API

    def open_edit_client_dialog(self):
        if not self.selected_client_cpf:
            QMessageBox.warning(self, "Seleção Necessária", "Por favor, selecione um cliente na lista para editar.")
            return
        print(f"ClientsTab: open_edit_client_dialog para CPF {self.selected_client_cpf}")
        dialog = ClientFormDialog_pyside(self.client_api_service, self.user_id, client_cpf_to_edit=self.selected_client_cpf, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_clients_from_api() 
            self.display_client_details(self.selected_client_cpf) 

    def delete_selected_client(self):
        if not self.selected_client_cpf:
            QMessageBox.warning(self, "Seleção Necessária", "Por favor, selecione um cliente para remover.")
            return
        print(f"ClientsTab: delete_selected_client para CPF {self.selected_client_cpf}")

        current_row = self.clients_table.currentRow()
        nome_cliente_para_confirmacao = self.selected_client_cpf
        if current_row >= 0:
            nome_item = self.clients_table.item(current_row, 0)
            if nome_item:
                nome_cliente_para_confirmacao = nome_item.text()
        
        confirm_msg = (f"Tem certeza que deseja remover o cliente:\n"
                       f"Nome: {nome_cliente_para_confirmacao}\n"
                       f"CPF: {self.selected_client_cpf}\n\n"
                       "Esta ação não pode ser desfeita.")
        
        reply = QMessageBox.question(self, "Confirmar Remoção", confirm_msg,
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            try:
                # USA O CLIENT_API_SERVICE
                api_response = self.client_api_service.delete_client(self.user_id, self.selected_client_cpf)
            finally:
                QApplication.restoreOverrideCursor()

            if api_response and api_response.get("success"):
                QMessageBox.information(self, "Sucesso", api_response.get("message", "Cliente removido com sucesso."))
                self.load_clients_from_api() 
            else:
                error_msg = "Falha na remoção via API."
                if isinstance(api_response, dict): 
                    error_msg = api_response.get("message", "Não foi possível remover o cliente via API.")
                QMessageBox.critical(self, "Erro na Remoção", error_msg)

# advocacia_app/ui/hearing_form_dialog_pyside.py

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QTextEdit,
    QDialogButtonBox, QMessageBox, QPushButton, QComboBox, QLabel,
    QApplication, QDateTimeEdit, QCompleter # QCalendarWidget removido, QCompleter adicionado
)
from PySide6.QtCore import Qt, Slot, QDateTime, QDate, QTime, QStringListModel 
from typing import List, Dict, Optional, Any

class HearingFormDialog_pyside(QDialog):
    """
    Diálogo para adicionar ou editar uma audiência.
    """
    # (Label, attr_name, WidgetClass, is_required, placeholder/items, widget_config_ou_altura)
    STATIC_HEARING_FIELDS_CONFIG = [
        ("Processo Associado:", "process_id", QComboBox, True, "Selecione ou busque o processo", None),
        ("Data e Hora:", "data_hora", QDateTimeEdit, True, None, None), 
        ("Local:", "local", QLineEdit, True, "Ex: Fórum Central, Sala 101", None),
        ("Vara:", "vara", QLineEdit, False, "Ex: 2ª Vara de Família", None),
        ("Tipo de Audiência:", "tipo", QLineEdit, True, "Ex: Instrução, Conciliação, Una", None),
        ("Notas Adicionais:", "notas", QTextEdit, False, "Observações, lembretes, partes a serem intimadas...", 80) # 80 é min_height
    ]

    def __init__(self, hearings_api_service, process_api_service, user_id: str, 
                 hearing_id_to_edit: Optional[str] = None, 
                 initial_process_id: Optional[str] = None, 
                 parent=None):
        super().__init__(parent)
        self.hearings_api_service = hearings_api_service
        self.process_api_service = process_api_service 
        self.user_id = user_id
        self.hearing_id_to_edit = hearing_id_to_edit
        self.hearing_data_to_edit: Optional[Dict[str, Any]] = None
        self.initial_process_id = initial_process_id
        
        self.all_processes_cache: List[Dict[str, Any]] = [] 

        self.setWindowTitle("Adicionar Nova Audiência" if not self.hearing_id_to_edit else "Editar Audiência")
        self.setMinimumWidth(600)
        self.resize(650, 550)

        main_layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        form_layout.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)

        self.entries: Dict[str, QLineEdit | QTextEdit | QComboBox | QDateTimeEdit] = {}

        self._fetch_processes_for_combobox()

        for config_item in HearingFormDialog_pyside.STATIC_HEARING_FIELDS_CONFIG:
            # Desempacotar corretamente os 6 elementos
            label_text, attr_name, WidgetClass, is_required, placeholder, widget_config = config_item

            label_widget = QLabel(label_text)
            
            if WidgetClass == QComboBox and attr_name == "process_id":
                widget = QComboBox()
                widget.setEditable(True)
                widget.setInsertPolicy(QComboBox.NoInsert)
                widget.addItem("Buscando processos...", None) 
                widget.setToolTip(str(placeholder)) # Usa o placeholder como tooltip
            elif WidgetClass == QTextEdit:
                widget = WidgetClass()
                widget.setPlaceholderText(str(placeholder))
                if isinstance(widget_config, int): # Se o sexto elemento for um int, é min_height
                    widget.setMinimumHeight(widget_config)
                label_widget.setToolTip(str(placeholder))
            elif WidgetClass == QDateTimeEdit and attr_name == "data_hora":
                widget = QDateTimeEdit(self)
                widget.setCalendarPopup(True)
                widget.setDateTime(QDateTime.currentDateTime().addSecs(3600)) 
                widget.setDisplayFormat("dd/MM/yyyy HH:mm")
                widget.setMinimumDateTime(QDateTime.currentDateTime().addDays(-365*5)) 
                widget.setMaximumDateTime(QDateTime.currentDateTime().addDays(365*5)) 
                label_widget.setToolTip("Selecione a data e hora da audiência.")
            elif WidgetClass == QLineEdit:
                widget = QLineEdit()
                widget.setPlaceholderText(str(placeholder))
                label_widget.setToolTip(str(placeholder))
            else:
                widget = WidgetClass() 

            self.entries[attr_name] = widget
            form_layout.addRow(label_widget, widget)
        
        self._populate_processes_combobox()

        main_layout.addLayout(form_layout)
        
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.button(QDialogButtonBox.StandardButton.Ok).setText("Salvar Audiência")
        self.button_box.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        self.button_box.accepted.connect(self.accept_data)
        self.button_box.rejected.connect(self.reject)
        main_layout.addWidget(self.button_box)

        self.setLayout(main_layout)

        if self.hearing_id_to_edit:
            self.load_hearing_data_for_edit()
        elif self.initial_process_id: 
            self._preselect_process(self.initial_process_id)

    def _fetch_processes_for_combobox(self):
        print("HearingFormDialog: Buscando processos para ComboBox...")
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            response = self.process_api_service.get_processes_by_user(self.user_id) 
            if response and response.get("success") and "processes" in response:
                self.all_processes_cache = sorted(
                    response["processes"], 
                    key=lambda p: p.get("numero_processo", "").lower()
                ) 
                print(f"HearingFormDialog: {len(self.all_processes_cache)} processos carregados para ComboBox.")
            else:
                self.all_processes_cache = []
                msg = "Não foi possível buscar a lista de processos."
                if response and isinstance(response, dict) and response.get("message"):
                    msg = response.get("message")
                QMessageBox.warning(self, "Erro ao Carregar Processos", msg)
        except Exception as e:
            self.all_processes_cache = []
            QMessageBox.critical(self, "Erro Crítico", f"Erro ao buscar processos para o formulário: {e}")
        finally:
            QApplication.restoreOverrideCursor()

    def _populate_processes_combobox(self):
        process_combo_box = self.entries.get("process_id")
        if not isinstance(process_combo_box, QComboBox): return

        process_combo_box.clear() 
        process_combo_box.addItem("Selecione ou digite para buscar...", None)
        
        display_texts = []
        for proc in self.all_processes_cache:
            client_display = proc.get("client_nome_completo") or proc.get("client_cpf", "Cliente não associado")
            text = f"{proc.get('numero_processo', 'N/P Desconhecido')} (Cliente: {client_display})"
            process_combo_box.addItem(text, proc.get('process_id'))
            display_texts.append(text)

        if not self.all_processes_cache:
            process_combo_box.addItem("Nenhum processo encontrado", None)
            process_combo_box.setEnabled(False)

        completer_model = QStringListModel(display_texts, self)
        completer = QCompleter(completer_model, self)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        process_combo_box.setCompleter(completer)

    def _preselect_process(self, process_id_to_select: str):
        process_combo_box = self.entries.get("process_id")
        if isinstance(process_combo_box, QComboBox):
            for i in range(process_combo_box.count()):
                if process_combo_box.itemData(i) == process_id_to_select:
                    process_combo_box.setCurrentIndex(i)
                    break

    def load_hearing_data_for_edit(self):
        if not self.hearing_id_to_edit: return
        print(f"HearingFormDialog: Carregando dados para editar audiência ID {self.hearing_id_to_edit}")
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            api_response = self.hearings_api_service.get_hearing_details(self.user_id, self.hearing_id_to_edit)
        finally:
            QApplication.restoreOverrideCursor()
        
        if api_response and api_response.get("success") and "hearing" in api_response: 
            self.hearing_data_to_edit = api_response["hearing"]
            
            for config_item in HearingFormDialog_pyside.STATIC_HEARING_FIELDS_CONFIG:
                # Desempacotar corretamente os 6 elementos
                label_text, attr_name, WidgetClass, is_required, placeholder, widget_config = config_item
                widget = self.entries.get(attr_name)
                value = self.hearing_data_to_edit.get(attr_name)

                if widget and value is not None:
                    if isinstance(widget, QLineEdit):
                        widget.setText(str(value))
                    elif isinstance(widget, QTextEdit):
                        widget.setPlainText(str(value))
                    elif isinstance(widget, QComboBox) and attr_name == "process_id":
                        self._preselect_process(str(value)) 
                    elif isinstance(widget, QDateTimeEdit) and attr_name == "data_hora":
                        try:
                            dt_obj = QDateTime.fromString(str(value), Qt.DateFormat.ISODateWithMs)
                            if not dt_obj.isValid(): 
                                dt_obj = QDateTime.fromString(str(value), Qt.DateFormat.ISODate)
                            if dt_obj.isValid():
                                widget.setDateTime(dt_obj)
                            else:
                                print(f"Erro ao parsear data_hora '{value}' para QDateTimeEdit.")
                        except Exception as e_dt:
                            print(f"Exceção ao parsear data_hora '{value}': {e_dt}")
        else:
            error_msg = "Não foi possível carregar os dados da audiência."
            if isinstance(api_response, dict):
                error_msg = api_response.get("message", error_msg)
            QMessageBox.critical(self, "Erro ao Carregar Dados", error_msg)
            ok_button = self.button_box.button(QDialogButtonBox.StandardButton.Ok)
            if ok_button: ok_button.setEnabled(False)

    def accept_data(self):
        print("HearingFormDialog: accept_data chamado.")
        hearing_data_payload = {}
        has_errors = False

        # Iterar sobre todos os campos e desempacotar 6 elementos
        for config_item in HearingFormDialog_pyside.STATIC_HEARING_FIELDS_CONFIG:
            label_text, attr_name, WidgetClass, is_required, placeholder, widget_config = config_item
            
            widget = self.entries[attr_name]
            value_str = ""
            
            if isinstance(widget, QLineEdit):
                value_str = widget.text().strip()
            elif isinstance(widget, QTextEdit):
                value_str = widget.toPlainText().strip()
            elif isinstance(widget, QComboBox) and attr_name == "process_id":
                selected_data = widget.currentData() 
                if selected_data: value_str = str(selected_data)
                else: value_str = "" 
            elif isinstance(widget, QDateTimeEdit) and attr_name == "data_hora":
                value_str = widget.dateTime().toString(Qt.DateFormat.ISODate) 
            
            if is_required and not value_str:
                QMessageBox.warning(self, "Campo Obrigatório", f"O campo '{label_text.replace(':', '')}' é obrigatório.")
                widget.setFocus(); has_errors = True; break 
            
            if value_str or not is_required: 
                hearing_data_payload[attr_name] = value_str
        
        if has_errors: return

        print(f"HearingFormDialog: Dados da audiência para API (payload): {hearing_data_payload}")
        
        api_response = None
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            if self.hearing_id_to_edit:
                print(f"HearingFormDialog: Chamando hearings_api_service.update_hearing para user: {self.user_id}, hearing_id: {self.hearing_id_to_edit}")
                api_response = self.hearings_api_service.update_hearing(self.user_id, self.hearing_id_to_edit, hearing_data_payload)
            else:
                print(f"HearingFormDialog: Chamando hearings_api_service.add_hearing para user: {self.user_id}")
                api_response = self.hearings_api_service.add_hearing(self.user_id, hearing_data_payload)
        finally:
            QApplication.restoreOverrideCursor()

        print(f"HearingFormDialog: Resposta da API: {api_response}")
        if api_response and api_response.get("success"):
            msg = api_response.get("message", f"Audiência {'atualizada' if self.hearing_id_to_edit else 'adicionada'} com sucesso!")
            QMessageBox.information(self, "Sucesso", msg)
            self.accept() 
        else:
            error_msg = "Falha na operação com a API de Audiências."
            if isinstance(api_response, dict):
                error_msg = api_response.get("message", f"Não foi possível {'atualizar' if self.hearing_id_to_edit else 'adicionar'} a audiência via API.")
            QMessageBox.critical(self, "Erro na Operação", error_msg)


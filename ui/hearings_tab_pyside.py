# advocacia_app/ui/hearings_tab_pyside.py

from typing import Any, Dict, List, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QScrollArea, QTextBrowser, QApplication, QDialog, QSplitter,
    QCalendarWidget
)
from PySide6.QtCore import Qt, Slot, QDate, QTime, QDateTime
from PySide6.QtGui import QFont, QColor, QTextCharFormat, QBrush
import json
import datetime

from .hearing_form_dialog_pyside import HearingFormDialog_pyside
# from services.process_api_service import ProcessApiService 
# from services.hearings_api_service import HearingsApiService

class HearingsTab_pyside(QWidget):
    def __init__(self, user_id: str, hearings_api_service, process_api_service, parent=None):
        super().__init__(parent)
        self.user_id = user_id
        self.hearings_api_service = hearings_api_service
        self.process_api_service = process_api_service 
        
        self.selected_hearing_id: Optional[str] = None
        self.all_hearings_cache: List[Dict[str, Any]] = [] 
        self.process_details_cache: Dict[str, Dict[str, Any]] = {} 

        print(f"HearingsTab_pyside: Instanciada com user_id: {self.user_id}")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)

        action_bar_layout = QHBoxLayout()
        self.search_entry = QLineEdit()
        self.search_entry.setPlaceholderText("Buscar por Nº Processo, Local, Tipo...")
        self.search_entry.textChanged.connect(self.filter_hearings_display)
        action_bar_layout.addWidget(self.search_entry)

        add_hearing_btn = QPushButton("Agendar Nova Audiência")
        add_hearing_btn.clicked.connect(self.open_add_hearing_dialog)
        action_bar_layout.addWidget(add_hearing_btn)
        main_layout.addLayout(action_bar_layout)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)

        left_panel_widget = QWidget()
        left_panel_layout = QVBoxLayout(left_panel_widget)
        left_panel_layout.setContentsMargins(0,0,0,0)

        self.calendar_widget = QCalendarWidget()
        self.calendar_widget.setGridVisible(True)
        self.calendar_widget.setMinimumDate(QDate.currentDate().addYears(-2))
        self.calendar_widget.setMaximumDate(QDate.currentDate().addYears(5))
        self.calendar_widget.clicked[QDate].connect(self.on_calendar_date_selected)
        left_panel_layout.addWidget(self.calendar_widget)

        self.show_all_hearings_button = QPushButton("Mostrar Todas as Audiências")
        self.show_all_hearings_button.clicked.connect(self.load_all_hearings_from_api)
        left_panel_layout.addWidget(self.show_all_hearings_button)
        
        self.hearings_table = QTableWidget()
        self.hearings_table.setColumnCount(6) 
        self.hearings_table.setHorizontalHeaderLabels(["ID", "Nº Processo", "Data e Hora", "Local", "Vara", "Tipo"])
        self.hearings_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.hearings_table.setColumnHidden(0, True) 
        self.hearings_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive) 
        self.hearings_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents) 
        self.hearings_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.hearings_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.hearings_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.hearings_table.itemSelectionChanged.connect(self.on_hearing_selected_from_table)
        left_panel_layout.addWidget(self.hearings_table)
        
        self.splitter.addWidget(left_panel_widget)

        right_panel_widget = QWidget()
        right_panel_layout = QVBoxLayout(right_panel_widget)
        right_panel_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.edit_hearing_btn = QPushButton("Editar Audiência Selecionada")
        self.edit_hearing_btn.clicked.connect(self.open_edit_hearing_dialog)
        self.edit_hearing_btn.setEnabled(False)
        right_panel_layout.addWidget(self.edit_hearing_btn)

        self.delete_hearing_btn = QPushButton("Remover Audiência Selecionada")
        self.delete_hearing_btn.clicked.connect(self.delete_selected_hearing)
        self.delete_hearing_btn.setEnabled(False)
        right_panel_layout.addWidget(self.delete_hearing_btn)
        
        self.details_display_browser = QTextBrowser()
        self.details_display_browser.setOpenExternalLinks(True)
        self.details_display_browser.setFont(QFont("Arial", 10))
        right_panel_layout.addWidget(self.details_display_browser)
        
        self.splitter.addWidget(right_panel_widget)
        
        self.splitter.setStretchFactor(0, 1) 
        self.splitter.setStretchFactor(1, 1) 

        main_layout.addWidget(self.splitter)
        self.setLayout(main_layout)

        self.load_all_hearings_from_api() 

    def _get_process_display_info(self, process_id: str) -> str:
        if not process_id: return "Processo não associado"
        if process_id in self.process_details_cache:
            proc_info = self.process_details_cache[process_id]
            client_name = proc_info.get('client_nome_completo', proc_info.get('client_cpf', 'N/A'))
            return f"{proc_info.get('numero_processo', 'N/P Desconhecido')} (Cliente: {client_name})"

        print(f"HearingsTab: Buscando detalhes do processo ID {process_id} para exibição...")
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            response = self.process_api_service.get_process_details(self.user_id, process_id)
            if response and response.get("success") and "process" in response:
                process_data = response["process"]
                self.process_details_cache[process_id] = process_data 
                client_name = process_data.get('client_nome_completo', process_data.get('client_cpf', 'N/A'))
                return f"{process_data.get('numero_processo', 'N/P Desconhecido')} (Cliente: {client_name})"
            else:
                return f"Processo ID: {process_id} (Detalhes não encontrados)"
        except Exception as e:
            print(f"Erro ao buscar detalhes do processo {process_id}: {e}")
            return f"Processo ID: {process_id} (Erro ao buscar detalhes)"
        finally:
            QApplication.restoreOverrideCursor()

    def _populate_hearings_table(self, hearings_data: List[Dict[str, Any]]):
        self.hearings_table.setRowCount(0)
        self.hearings_table.setSortingEnabled(False)
        for row, hearing_item in enumerate(hearings_data):
            self.hearings_table.insertRow(row)
            self.hearings_table.setItem(row, 0, QTableWidgetItem(str(hearing_item.get("hearing_id", "N/A"))))
            
            process_display_text = self._get_process_display_info(hearing_item.get("process_id"))
            self.hearings_table.setItem(row, 1, QTableWidgetItem(process_display_text))
            
            data_hora_str = hearing_item.get("data_hora", "N/A")
            display_data_hora = data_hora_str
            try: 
                dt_obj = QDateTime.fromString(data_hora_str, Qt.DateFormat.ISODate)
                if dt_obj.isValid(): display_data_hora = dt_obj.toString("dd/MM/yyyy HH:mm")
            except: pass 
            self.hearings_table.setItem(row, 2, QTableWidgetItem(display_data_hora))
            
            self.hearings_table.setItem(row, 3, QTableWidgetItem(hearing_item.get("local", "N/A")))
            self.hearings_table.setItem(row, 4, QTableWidgetItem(hearing_item.get("vara", "N/A")))
            self.hearings_table.setItem(row, 5, QTableWidgetItem(hearing_item.get("tipo", "N/A")))
        self.hearings_table.setSortingEnabled(True)
        self.clear_hearing_details_display()
        self.edit_hearing_btn.setEnabled(False)
        self.delete_hearing_btn.setEnabled(False)

    def _highlight_calendar_dates(self):
        """Destaca datas no calendário com cores baseadas na proximidade da audiência."""
        # Limpar destaques anteriores
        default_format = QTextCharFormat() # Formato padrão para resetar
        # Iterar por todas as datas visíveis no mês atual pode ser necessário para um reset completo
        # ou manter um registro das datas formatadas anteriormente.
        # Por simplicidade, vamos redefinir todas as datas que tinham formato especial.
        # Uma forma mais robusta seria iterar pelas datas do mês atual e aplicar default_format.
        # Aqui, vamos aplicar o formato padrão a todas as datas que vamos re-colorir.
        
        # Formatos de cor
        format_far = QTextCharFormat() # Mais de 7 dias
        format_far.setBackground(QBrush(QColor(200, 255, 200))) # Verde claro

        format_medium = QTextCharFormat() # 1 a 7 dias
        format_medium.setBackground(QBrush(QColor(255, 255, 150))) # Amarelo claro
        format_medium.setFontWeight(QFont.Weight.Bold)

        format_near = QTextCharFormat() # Hoje ou muito próximo
        format_near.setBackground(QBrush(QColor(255, 180, 180))) # Vermelho claro
        format_near.setFontWeight(QFont.Weight.Bold)
        format_near.setToolTip("Audiência hoje ou muito próxima!") # Adiciona tooltip

        today = QDate.currentDate()
        
        # Primeiro, resetar o formato de todas as datas que podem ter sido destacadas
        # Isso é importante se as audiências mudam ou são removidas.
        # Uma maneira simples é resetar todas as datas do calendário, mas pode ser lento.
        # Vamos resetar apenas as datas que tinham audiências.
        all_dates_in_calendar = {} # {QDate: QTextCharFormat}
        for hearing in self.all_hearings_cache:
             data_hora_str = hearing.get("data_hora")
             if data_hora_str:
                try:
                    dt_obj = QDateTime.fromString(data_hora_str, Qt.DateFormat.ISODate)
                    if dt_obj.isValid():
                        q_date = dt_obj.date()
                        self.calendar_widget.setDateTextFormat(q_date, default_format) # Reseta primeiro
                        all_dates_in_calendar[q_date] = default_format # Guarda para aplicar o formato correto depois
                except Exception:
                    pass
        
        # Aplicar novos formatos
        for hearing in self.all_hearings_cache:
            data_hora_str = hearing.get("data_hora")
            if data_hora_str:
                try:
                    dt_obj = QDateTime.fromString(data_hora_str, Qt.DateFormat.ISODate)
                    if dt_obj.isValid():
                        hearing_qdate = dt_obj.date()
                        days_to_hearing = today.daysTo(hearing_qdate)
                        
                        chosen_format = default_format # Começa com o padrão
                        if days_to_hearing < 0: # Audiência passada
                            pass # Poderia ter um formato para datas passadas, e.g., cinza
                        elif days_to_hearing <= 1: # Hoje ou amanhã (ou muito próximo)
                            chosen_format = format_near
                        elif days_to_hearing <= 7: # Próximos 7 dias
                            chosen_format = format_medium
                        else: # Mais de 7 dias
                            chosen_format = format_far
                        
                        # Se já houver um formato mais "urgente" para esta data, não sobrescreva
                        current_format_for_date = all_dates_in_calendar.get(hearing_qdate, default_format)
                        if chosen_format.background() != default_format.background(): # Se o novo formato é um destaque
                            # Prioridade: Vermelho > Amarelo > Verde
                            if current_format_for_date.background() == format_near.background():
                                # Já é vermelho, não muda
                                pass
                            elif current_format_for_date.background() == format_medium.background() and chosen_format.background() == format_far.background():
                                # Já é amarelo, não muda para verde
                                pass
                            else:
                                all_dates_in_calendar[hearing_qdate] = chosen_format
                except Exception as e:
                    print(f"Erro ao processar data '{data_hora_str}' para destaque: {e}")

        # Aplicar os formatos finais
        for q_date, fmt in all_dates_in_calendar.items():
            self.calendar_widget.setDateTextFormat(q_date, fmt)


    def load_all_hearings_from_api(self, search_term: Optional[str] = None, date_filter: Optional[QDate] = None):
        print(f"HearingsTab: load_all_hearings_from_api. User ID: {self.user_id}, Busca: '{search_term}', Data: {date_filter.toString('yyyy-MM-dd') if date_filter else 'N/A'}")
        if not self.user_id:
            QMessageBox.critical(self, "Erro Interno", "ID do utilizador não está disponível.")
            return
        
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        api_response = None
        try:
            start_date_str = date_filter.toString("yyyy-MM-dd") if date_filter else None
            end_date_str = start_date_str 
            
            api_response = self.hearings_api_service.get_hearings_by_user(self.user_id, start_date=start_date_str, end_date=end_date_str)
        except Exception as e:
            print(f"Erro ao chamar API para buscar audiências: {e}")
            QMessageBox.critical(self, "Erro de API", f"Erro ao buscar audiências: {e}")
            self.all_hearings_cache = [] # Limpa cache em caso de erro de API
        finally:
            QApplication.restoreOverrideCursor()

        if api_response and api_response.get("success"):
            self.all_hearings_cache = api_response.get("hearings", [])
            print(f"HearingsTab: {len(self.all_hearings_cache)} audiências recebidas da API.")
        elif api_response: # Se houve resposta, mas não sucesso
            QMessageBox.warning(self, "Erro ao Carregar Audiências", 
                                api_response.get("message", "Não foi possível buscar as audiências."))
            self.all_hearings_cache = []
        # Se api_response for None (devido a exceção), o cache não é alterado ou já foi limpo.
            
        filtered_for_display = self.all_hearings_cache
        if date_filter: # Se filtrando por data, a API já deve ter filtrado.
            pass # A API já filtrou por data
        elif search_term: # Filtro de busca local se a API não suportar ou para refinar
            search_lower = search_term.lower()
            filtered_for_display = [
                h for h in self.all_hearings_cache if
                search_lower in h.get("local", "").lower() or
                search_lower in h.get("tipo", "").lower() or
                search_lower in h.get("vara", "").lower() or
                search_lower in self._get_process_display_info(h.get("process_id","")).lower()
            ]
        
        self._populate_hearings_table(filtered_for_display)
        self._highlight_calendar_dates() 


    @Slot(QDate)
    def on_calendar_date_selected(self, date: QDate):
        print(f"HearingsTab: Data selecionada no calendário: {date.toString('dd/MM/yyyy')}")
        self.search_entry.clear() 
        self.load_all_hearings_from_api(date_filter=date) 

    @Slot()
    def filter_hearings_display(self):
        search_term = self.search_entry.text()
        current_selected_date = self.calendar_widget.selectedDate()
        if search_term and current_selected_date.isValid(): # Se houver busca e data selecionada
            self.calendar_widget.setSelectedDate(QDate()) # Limpa seleção de data para buscar em tudo
            self.load_all_hearings_from_api(search_term=search_term)
        else:
            self.load_all_hearings_from_api(search_term=search_term, date_filter=current_selected_date if current_selected_date.isValid() else None)


    @Slot() 
    def on_hearing_selected_from_table(self):
        selected_items = self.hearings_table.selectedItems()
        if selected_items:
            selected_row = self.hearings_table.currentRow() 
            hearing_id_item = self.hearings_table.item(selected_row, 0) 
            if hearing_id_item and hearing_id_item.text() != "N/A":
                self.selected_hearing_id = hearing_id_item.text()
                print(f"HearingsTab: Audiência selecionada da tabela - ID {self.selected_hearing_id}")
                self.display_hearing_details(self.selected_hearing_id)
                self.edit_hearing_btn.setEnabled(True)
                self.delete_hearing_btn.setEnabled(True)
                return
        
        self.selected_hearing_id = None
        self.clear_hearing_details_display()
        self.edit_hearing_btn.setEnabled(False)
        self.delete_hearing_btn.setEnabled(False)

    def display_hearing_details(self, hearing_id_to_display: str):
        self.clear_hearing_details_display()
        hearing_info = next((h for h in self.all_hearings_cache if h.get("hearing_id") == hearing_id_to_display), None)

        if hearing_info:
            html_parts = ["<h3>Detalhes da Audiência:</h3><table width='100%' cellspacing='0' cellpadding='3' style='border-collapse: collapse;'>"]
            process_display = self._get_process_display_info(hearing_info.get("process_id"))
            html_parts.append(f"<tr><td valign='top' style='padding: 4px; border: 1px solid #ddd;' width='120px'><b>Processo:</b></td><td style='padding: 4px; border: 1px solid #ddd;'>{process_display}</td></tr>")
            data_hora_str = hearing_info.get("data_hora", "N/A")
            display_dt = data_hora_str
            try:
                dt = QDateTime.fromString(data_hora_str, Qt.DateFormat.ISODate)
                if dt.isValid(): display_dt = dt.toString("dd/MM/yyyy 'às' HH:mm")
            except: pass
            html_parts.append(f"<tr><td valign='top' style='padding: 4px; border: 1px solid #ddd;'><b>Data e Hora:</b></td><td style='padding: 4px; border: 1px solid #ddd;'>{display_dt}</td></tr>")
            html_parts.append(f"<tr><td valign='top' style='padding: 4px; border: 1px solid #ddd;'><b>Local:</b></td><td style='padding: 4px; border: 1px solid #ddd;'>{hearing_info.get('local', 'N/A')}</td></tr>")
            html_parts.append(f"<tr><td valign='top' style='padding: 4px; border: 1px solid #ddd;'><b>Vara:</b></td><td style='padding: 4px; border: 1px solid #ddd;'>{hearing_info.get('vara', 'N/A')}</td></tr>")
            html_parts.append(f"<tr><td valign='top' style='padding: 4px; border: 1px solid #ddd;'><b>Tipo:</b></td><td style='padding: 4px; border: 1px solid #ddd;'>{hearing_info.get('tipo', 'N/A')}</td></tr>")
            notas = hearing_info.get('notas', '').replace('\n', '<br>')
            html_parts.append(f"<tr><td valign='top' style='padding: 4px; border: 1px solid #ddd;'><b>Notas:</b></td><td style='padding: 4px; border: 1px solid #ddd;'>{notas if notas else 'Nenhuma'}</td></tr>")
            html_parts.append("</table>")
            self.details_display_browser.setHtml("".join(html_parts))
        else:
            self.details_display_browser.setHtml("<font color='red'>Detalhes da audiência não encontrados no cache.</font>")

    def clear_hearing_details_display(self):
        self.details_display_browser.setHtml("Selecione uma audiência para ver os detalhes.")

    def open_add_hearing_dialog(self, process_id_to_preselect: Optional[str] = None):
        print("HearingsTab: open_add_hearing_dialog chamado.")
        # Garante que process_id_to_preselect seja string ou None
        preselect_id = process_id_to_preselect if isinstance(process_id_to_preselect, str) else None
        
        dialog = HearingFormDialog_pyside(
            self.hearings_api_service, 
            self.process_api_service, 
            self.user_id,
            initial_process_id=preselect_id,
            parent=self
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_all_hearings_from_api()

    def open_edit_hearing_dialog(self):
        if not self.selected_hearing_id:
            QMessageBox.warning(self, "Seleção Necessária", "Por favor, selecione uma audiência na lista para editar.")
            return
        print(f"HearingsTab: open_edit_hearing_dialog para ID {self.selected_hearing_id}")
        
        dialog = HearingFormDialog_pyside(
            self.hearings_api_service, 
            self.process_api_service, 
            self.user_id, 
            hearing_id_to_edit=self.selected_hearing_id, 
            parent=self
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_all_hearings_from_api()
            # Tenta manter a seleção ou recarregar os detalhes
            if self.selected_hearing_id in [h.get('hearing_id') for h in self.all_hearings_cache]:
                 self.display_hearing_details(self.selected_hearing_id)
            else: # Audiência pode ter sido alterada de forma que não está mais no cache com mesmo ID, ou deletada
                 self.clear_hearing_details_display()
                 self.edit_hearing_btn.setEnabled(False)
                 self.delete_hearing_btn.setEnabled(False)


    def delete_selected_hearing(self):
        if not self.selected_hearing_id:
            QMessageBox.warning(self, "Seleção Necessária", "Por favor, selecione uma audiência para remover.")
            return
        
        hearing_info = next((h for h in self.all_hearings_cache if h.get("hearing_id") == self.selected_hearing_id), None)
        confirm_text = f"Tem certeza que deseja remover esta audiência?"
        if hearing_info:
            dt_display = hearing_info.get("data_hora", "Data desconhecida")
            try:
                dt_obj = QDateTime.fromString(dt_display, Qt.DateFormat.ISODate)
                if dt_obj.isValid(): dt_display = dt_obj.toString("dd/MM/yyyy HH:mm")
            except: pass
            confirm_text = (f"Tem certeza que deseja remover a audiência:\n"
                            f"Tipo: {hearing_info.get('tipo', 'N/A')}\n"
                            f"Data: {dt_display}\n"
                            f"Local: {hearing_info.get('local', 'N/A')}\n\n"
                            "Esta ação não pode ser desfeita.")
        
        reply = QMessageBox.question(self, "Confirmar Remoção", confirm_text,
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            api_response = None
            try:
                api_response = self.hearings_api_service.delete_hearing(self.user_id, self.selected_hearing_id)
            except Exception as e:
                print(f"Erro ao chamar delete_hearing: {e}")
                QMessageBox.critical(self, "Erro na Remoção", f"Erro ao tentar remover audiência: {e}")
            finally:
                QApplication.restoreOverrideCursor()

            if api_response and api_response.get("success"):
                QMessageBox.information(self, "Sucesso", api_response.get("message", "Audiência removida com sucesso."))
                self.load_all_hearings_from_api() 
                self.clear_hearing_details_display() 
                self.edit_hearing_btn.setEnabled(False) 
                self.delete_hearing_btn.setEnabled(False)
            elif api_response: 
                error_msg = api_response.get("message", "Não foi possível remover a audiência via API.")
                QMessageBox.critical(self, "Erro na Remoção", error_msg)

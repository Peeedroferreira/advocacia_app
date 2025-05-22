import customtkinter as ctk
from tkinter import ttk, messagebox
from database.db_handler import DBHandler
from ui.widgets.calendar_popup import CalendarPopup # Para selecionar data/hora
from tkcalendar import Calendar # Para o calendário na própria aba
from datetime import datetime
from typing import Optional, List, Dict, Any

class HearingsTab(ctk.CTkFrame):
    def __init__(self, master, db_handler: DBHandler):
        super().__init__(master, fg_color="transparent")
        self.db_handler = db_handler
        self.pack(fill="both", expand=True)

        self.selected_hearing_id: Optional[int] = None
        self.all_processes: List[Dict[str, Any]] = []

        self.create_widgets()
        self.load_hearings()

    def create_widgets(self):
        main_paned_window = ttk.PanedWindow(self, orient="horizontal")
        main_paned_window.pack(fill="both", expand=True, padx=10, pady=10)

        left_frame_container = ctk.CTkFrame(main_paned_window, fg_color="transparent")
        main_paned_window.add(left_frame_container, weight=2)

        top_frame = ctk.CTkFrame(left_frame_container, fg_color="transparent")
        top_frame.pack(fill="x", pady=(0,10))

        ctk.CTkLabel(top_frame, text="Buscar Audiência:").pack(side="left", padx=(0, 5))
        self.search_entry = ctk.CTkEntry(top_frame, placeholder_text="Nº Processo, Local, Vara...")
        self.search_entry.pack(side="left", padx=5, fill="x", expand=True)
        self.search_entry.bind("<KeyRelease>", lambda event: self.filter_hearings())

        add_button = ctk.CTkButton(top_frame, text="Adicionar", command=self.add_hearing_dialog)
        add_button.pack(side="right", padx=5)
        edit_button = ctk.CTkButton(top_frame, text="Editar", command=self.edit_hearing_dialog)
        edit_button.pack(side="right", padx=5)
        remove_button = ctk.CTkButton(top_frame, text="Remover", command=self.remove_hearing)
        remove_button.pack(side="right", padx=5)

        columns = ("id", "processo_numero", "data_hora", "local", "vara", "tipo")
        self.tree = ttk.Treeview(left_frame_container, columns=columns, show="headings", selectmode="browse")
        
        self.tree.heading("id", text="ID")
        self.tree.heading("processo_numero", text="Nº Processo")
        self.tree.heading("data_hora", text="Data e Hora")
        self.tree.heading("local", text="Local")
        self.tree.heading("vara", text="Vara")
        self.tree.heading("tipo", text="Tipo")

        self.tree.column("id", width=40, stretch=False, anchor="center")
        self.tree.column("processo_numero", width=130)
        self.tree.column("data_hora", width=140, anchor="center")
        self.tree.column("local", width=150)
        self.tree.column("vara", width=120)
        self.tree.column("tipo", width=100)
        
        self.apply_treeview_style()
        self.tree.pack(fill="both", expand=True, pady=(0,0))
        self.tree.bind("<<TreeviewSelect>>", self.on_hearing_select)
        
        right_frame_container = ctk.CTkFrame(main_paned_window, fg_color="transparent")
        main_paned_window.add(right_frame_container, weight=1)

        ctk.CTkLabel(right_frame_container, text="Calendário de Audiências", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)
        self.calendar_view = Calendar(right_frame_container, selectmode='day', date_pattern='yyyy-mm-dd', locale='pt_BR')
        self.calendar_view.pack(fill="both", expand=True, padx=10, pady=5)
        self.calendar_view.bind("<<CalendarSelected>>", self.on_calendar_date_selected)

        clear_calendar_filter_button = ctk.CTkButton(right_frame_container, text="Mostrar Todas Audiências", command=self.load_hearings)
        clear_calendar_filter_button.pack(pady=5)

        self.update_process_list_cache()
        self.highlight_calendar_dates_with_hearings()

    def apply_treeview_style(self):
        style = ttk.Style(self)
        # (Mesma lógica de estilo da DemandsTab)
        current_theme = ctk.get_appearance_mode()
        bg_color = "#2B2B2B" if current_theme == "Dark" else "white"
        fg_color = "white" if current_theme == "Dark" else "black"
        heading_bg = "#212121" if current_theme == "Dark" else "#E1E1E1"
        heading_active_bg = "#313131" if current_theme == "Dark" else "#D1D1D1"

        style.theme_use("clam")
        style.configure("Treeview", background=bg_color, foreground=fg_color, fieldbackground=bg_color, borderwidth=0)
        style.configure("Treeview.Heading", background=heading_bg, foreground=fg_color, relief="flat")
        style.map("Treeview.Heading", background=[('active', heading_active_bg)])


    def update_process_list_cache(self):
        self.all_processes = self.db_handler.fetch_all("SELECT id, numero_processo FROM processos ORDER BY numero_processo ASC")

    def on_hearing_select(self, event=None):
        selected_item = self.tree.selection()
        if selected_item:
            self.selected_hearing_id = self.tree.item(selected_item[0])["values"][0]
        else:
            self.selected_hearing_id = None

    def load_hearings(self, search_term: str = "", filter_date: Optional[str] = None):
        for i in self.tree.get_children():
            self.tree.delete(i)
        
        query = """
            SELECT h.id, p.numero_processo, 
                   STRFTIME('%d/%m/%Y %H:%M', h.data_hora) as data_hora_formatada, 
                   h.local, h.vara, h.tipo
            FROM audiencias h
            LEFT JOIN processos p ON h.processo_id = p.id
        """
        params = []
        conditions = []

        if search_term:
            conditions.append("(p.numero_processo LIKE ? OR h.local LIKE ? OR h.vara LIKE ? OR h.tipo LIKE ?)")
            params.extend([f"%{search_term}%", f"%{search_term}%", f"%{search_term}%", f"%{search_term}%"])
        
        if filter_date: # filter_date é 'YYYY-MM-DD'
            # Filtra pelo dia, ignorando a hora para o calendário
            conditions.append("DATE(h.data_hora) = ?")
            params.append(filter_date)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        query += " ORDER BY h.data_hora ASC, p.numero_processo ASC"
            
        hearings_data = self.db_handler.fetch_all(query, tuple(params))
        for hearing in hearings_data:
            self.tree.insert("", "end", values=(
                hearing["id"], 
                hearing["numero_processo"] if hearing["numero_processo"] else "N/A",
                hearing["data_hora_formatada"],
                hearing["local"],
                hearing["vara"],
                hearing["tipo"]
            ))
        self.selected_hearing_id = None
        if not filter_date:
            self.highlight_calendar_dates_with_hearings()

    def filter_hearings(self):
        search_term = self.search_entry.get()
        self.load_hearings(search_term=search_term, filter_date=None)

    def on_calendar_date_selected(self, event=None):
        selected_date_str = self.calendar_view.get_date() # Formato YYYY-MM-DD
        self.load_hearings(filter_date=selected_date_str)

    def highlight_calendar_dates_with_hearings(self):
        self.calendar_view.calevent_remove('all')
        hearings_dates = self.db_handler.fetch_all("SELECT DISTINCT DATE(data_hora) as hearing_date FROM audiencias WHERE data_hora IS NOT NULL")
        
        for hearing_date_obj in hearings_dates:
            date_str = hearing_date_obj["hearing_date"] # Formato YYYY-MM-DD
            if date_str:
                try:
                    event_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                    self.calendar_view.calevent_create(event_date, 'Audiência', 'hearing_scheduled')
                except ValueError:
                    print(f"Data inválida no banco para audiência: {date_str}")
        
        self.calendar_view.tag_config('hearing_scheduled', background='cornflowerblue', foreground='white')


    def add_hearing_dialog(self):
        self.update_process_list_cache()
        if not self.all_processes:
            messagebox.showinfo("Aviso", "Nenhum processo cadastrado.", parent=self)
            return
        HearingFormDialog(self, title="Agendar Nova Audiência", db_handler=self.db_handler, processes=self.all_processes)

    def edit_hearing_dialog(self):
        if not self.selected_hearing_id:
            messagebox.showwarning("Seleção Necessária", "Selecione uma audiência para editar.", parent=self)
            return
        
        hearing_data_raw = self.db_handler.fetch_one("SELECT * FROM audiencias WHERE id = ?", (self.selected_hearing_id,))
        if hearing_data_raw:
            hearing_data = dict(hearing_data_raw)
            self.update_process_list_cache()
            HearingFormDialog(self, title="Editar Audiência", db_handler=self.db_handler, processes=self.all_processes, hearing_data=hearing_data)
        else:
            messagebox.showerror("Erro", "Audiência não encontrada.", parent=self)

    def remove_hearing(self):
        if not self.selected_hearing_id:
            messagebox.showwarning("Seleção Necessária", "Selecione uma audiência para remover.", parent=self)
            return

        confirm = messagebox.askyesno("Confirmar Remoção", "Tem certeza que deseja remover esta audiência?", parent=self)
        if confirm:
            self.db_handler.execute_query("DELETE FROM audiencias WHERE id = ?", (self.selected_hearing_id,))
            messagebox.showinfo("Sucesso", "Audiência removida com sucesso.", parent=self)
            self.load_hearings()
        self.selected_hearing_id = None


class HearingFormDialog(ctk.CTkToplevel):
    def __init__(self, master_tab, title, db_handler, processes, hearing_data=None):
        super().__init__(master_tab.master)
        self.master_tab = master_tab
        self.db_handler = db_handler
        self.processes = processes
        self.hearing_data = hearing_data

        self.grab_set()
        self.title(title)
        self.resizable(False, False)
        
        master_win = self.master_tab.winfo_toplevel()
        x = master_win.winfo_x() + (master_win.winfo_width() - 550) // 2
        y = master_win.winfo_y() + (master_win.winfo_height() - 600) // 2
        self.geometry(f"550x600+{x}+{y}") # Aumentado para mais campos

        self.entries = {}
        self.process_var = ctk.StringVar()
        self.data_var = ctk.StringVar() # Data AAAA-MM-DD
        self.hora_var = ctk.StringVar(value="09") # Hora HH
        self.minuto_var = ctk.StringVar(value="00") # Minuto MM
        
        tipos_audiencia = ["Instrução", "Conciliação", "Julgamento", "Una", "Justificação", "Outra"]

        form_frame = ctk.CTkFrame(self, fg_color="transparent")
        form_frame.pack(padx=20, pady=20, fill="both", expand=True)

        # Layout
        ctk.CTkLabel(form_frame, text="Processo:").grid(row=0, column=0, padx=5, pady=8, sticky="w")
        process_cb = ctk.CTkComboBox(form_frame, width=350, variable=self.process_var, values=[p['numero_processo'] for p in self.processes])
        process_cb.grid(row=0, column=1, columnspan=3, padx=5, pady=8, sticky="ew")
        self.entries["processo_id"] = process_cb

        ctk.CTkLabel(form_frame, text="Data:").grid(row=1, column=0, padx=5, pady=8, sticky="w")
        data_entry = ctk.CTkEntry(form_frame, width=150, textvariable=self.data_var, placeholder_text="AAAA-MM-DD")
        data_entry.grid(row=1, column=1, padx=5, pady=8, sticky="ew")
        self.entries["data"] = data_entry
        calendar_btn = ctk.CTkButton(form_frame, text="📅", width=40, command=self.open_calendar_popup_data)
        calendar_btn.grid(row=1, column=2, padx=5, pady=8)

        ctk.CTkLabel(form_frame, text="Hora:").grid(row=2, column=0, padx=5, pady=8, sticky="w")
        time_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
        time_frame.grid(row=2, column=1, columnspan=3, padx=0, pady=8, sticky="ew")
        
        hora_cb = ctk.CTkComboBox(time_frame, width=70, variable=self.hora_var, values=[f"{h:02d}" for h in range(24)])
        hora_cb.pack(side="left", padx=(0,5))
        ctk.CTkLabel(time_frame, text=":").pack(side="left", padx=2)
        minuto_cb = ctk.CTkComboBox(time_frame, width=70, variable=self.minuto_var, values=[f"{m:02d}" for m in range(0, 60, 5)]) # Intervalos de 5 min
        minuto_cb.pack(side="left", padx=5)
        self.entries["hora"] = hora_cb
        self.entries["minuto"] = minuto_cb

        ctk.CTkLabel(form_frame, text="Local:").grid(row=3, column=0, padx=5, pady=8, sticky="w")
        local_entry = ctk.CTkEntry(form_frame, width=350, placeholder_text="Ex: Fórum Central, Sala 101")
        local_entry.grid(row=3, column=1, columnspan=3, padx=5, pady=8, sticky="ew")
        self.entries["local"] = local_entry

        ctk.CTkLabel(form_frame, text="Vara:").grid(row=4, column=0, padx=5, pady=8, sticky="w")
        vara_entry = ctk.CTkEntry(form_frame, width=350, placeholder_text="Ex: 1ª Vara Cível")
        vara_entry.grid(row=4, column=1, columnspan=3, padx=5, pady=8, sticky="ew")
        self.entries["vara"] = vara_entry

        ctk.CTkLabel(form_frame, text="Tipo de Audiência:").grid(row=5, column=0, padx=5, pady=8, sticky="w")
        tipo_cb = ctk.CTkComboBox(form_frame, width=350, values=tipos_audiencia)
        tipo_cb.grid(row=5, column=1, columnspan=3, padx=5, pady=8, sticky="ew")
        self.entries["tipo"] = tipo_cb
        
        ctk.CTkLabel(form_frame, text="Notas:").grid(row=6, column=0, padx=5, pady=8, sticky="nw")
        notas_tb = ctk.CTkTextbox(form_frame, width=350, height=80)
        notas_tb.grid(row=6, column=1, columnspan=3, padx=5, pady=8, sticky="nsew")
        self.entries["notas"] = notas_tb
        
        form_frame.columnconfigure(1, weight=1)
        form_frame.rowconfigure(6, weight=1) # Notas expande

        if self.hearing_data:
            # Preencher campos
            proc_id = self.hearing_data.get("processo_id")
            if proc_id:
                for p in self.processes:
                    if p['id'] == proc_id: self.process_var.set(p['numero_processo']); break
            
            data_hora_str = self.hearing_data.get("data_hora") # Formato YYYY-MM-DD HH:MM:SS
            if data_hora_str:
                dt_obj = datetime.strptime(data_hora_str, "%Y-%m-%d %H:%M:%S")
                self.data_var.set(dt_obj.strftime("%Y-%m-%d"))
                self.hora_var.set(dt_obj.strftime("%H"))
                self.minuto_var.set(dt_obj.strftime("%M"))

            self.entries["local"].insert(0, self.hearing_data.get("local", ""))
            self.entries["vara"].insert(0, self.hearing_data.get("vara", ""))
            self.entries["tipo"].set(self.hearing_data.get("tipo", tipos_audiencia[0]))
            notas = self.hearing_data.get("notas", "")
            if notas: self.entries["notas"].insert("1.0", notas)
        else:
            if self.processes: self.process_var.set(self.processes[0]['numero_processo'])
            self.entries["tipo"].set(tipos_audiencia[0])


        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.pack(pady=10, fill="x", padx=20)
        save_button = ctk.CTkButton(button_frame, text="Salvar", command=self.save_hearing)
        save_button.pack(side="right", padx=5)
        cancel_button = ctk.CTkButton(button_frame, text="Cancelar", command=self.destroy, fg_color="gray")
        cancel_button.pack(side="right", padx=5)

    def open_calendar_popup_data(self):
        initial_date = self.data_var.get()
        CalendarPopup(self, on_date_select_callback=lambda date: self.data_var.set(date), initial_date=initial_date, title="Selecionar Data da Audiência")

    def save_hearing(self):
        selected_proc_num = self.process_var.get()
        proc_id = next((p['id'] for p in self.processes if p['numero_processo'] == selected_proc_num), None)
        
        data_str = self.data_var.get().strip()
        hora_str = self.hora_var.get()
        minuto_str = self.minuto_var.get()
        
        local = self.entries["local"].get().strip()
        vara = self.entries["vara"].get().strip()
        tipo = self.entries["tipo"].get()
        notas = self.entries["notas"].get("1.0", "end-1c").strip()

        if not proc_id: messagebox.showerror("Erro", "Selecione um processo.", parent=self); return
        if not data_str: messagebox.showerror("Erro", "Data da audiência é obrigatória.", parent=self); return
        
        try:
            datetime.strptime(data_str, "%Y-%m-%d") # Valida data
            data_hora_completa_str = f"{data_str} {hora_str}:{minuto_str}:00" # Formato YYYY-MM-DD HH:MM:SS
            datetime.strptime(data_hora_completa_str, "%Y-%m-%d %H:%M:%S") # Valida data e hora completa
        except ValueError:
            messagebox.showerror("Data/Hora Inválida", "Formato de data (AAAA-MM-DD) ou hora inválido.", parent=self)
            return

        try:
            if self.hearing_data: # Editando
                query = """UPDATE audiencias SET processo_id=?, data_hora=?, local=?, vara=?, tipo=?, notas=?
                           WHERE id = ?"""
                params = (proc_id, data_hora_completa_str, local, vara, tipo, notas, self.hearing_data["id"])
            else: # Adicionando
                query = """INSERT INTO audiencias (processo_id, data_hora, local, vara, tipo, notas)
                           VALUES (?, ?, ?, ?, ?, ?)"""
                params = (proc_id, data_hora_completa_str, local, vara, tipo, notas)
            
            self.db_handler.execute_query(query, params)
            messagebox.showinfo("Sucesso", f"Audiência {'atualizada' if self.hearing_data else 'agendada'} com sucesso!", parent=self)
            self.master_tab.load_hearings()
            self.destroy()
        except Exception as e:
            messagebox.showerror("Erro ao Salvar", f"Ocorreu um erro: {e}", parent=self)


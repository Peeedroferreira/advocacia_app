import customtkinter as ctk
from tkinter import ttk, messagebox
from database.db_handler import DBHandler
from ui.widgets.calendar_popup import CalendarPopup # Importar o popup de calendário
from tkcalendar import Calendar # Para o calendário na própria aba
from datetime import datetime
from typing import Optional, List, Dict, Any

class DemandsTab(ctk.CTkFrame):
    def __init__(self, master, db_handler: DBHandler):
        super().__init__(master, fg_color="transparent")
        self.db_handler = db_handler
        self.pack(fill="both", expand=True)

        self.selected_demand_id: Optional[int] = None
        self.all_processes: List[Dict[str, Any]] = [] # Cache de processos

        self.create_widgets()
        self.load_demands()

    def create_widgets(self):
        # Frame principal dividido em duas colunas: Ações/Lista e Calendário
        main_paned_window = ttk.PanedWindow(self, orient="horizontal")
        main_paned_window.pack(fill="both", expand=True, padx=10, pady=10)

        # --- Frame Esquerdo (Ações e Lista de Demandas) ---
        left_frame_container = ctk.CTkFrame(main_paned_window, fg_color="transparent")
        main_paned_window.add(left_frame_container, weight=2) # Mais peso para a lista

        top_frame = ctk.CTkFrame(left_frame_container, fg_color="transparent")
        top_frame.pack(fill="x", pady=(0,10))

        ctk.CTkLabel(top_frame, text="Buscar Demanda:").pack(side="left", padx=(0, 5))
        self.search_entry = ctk.CTkEntry(top_frame, placeholder_text="Descrição ou Nº Processo...")
        self.search_entry.pack(side="left", padx=5, fill="x", expand=True)
        self.search_entry.bind("<KeyRelease>", lambda event: self.filter_demands())

        add_button = ctk.CTkButton(top_frame, text="Adicionar", command=self.add_demand_dialog)
        add_button.pack(side="right", padx=5)
        
        edit_button = ctk.CTkButton(top_frame, text="Editar", command=self.edit_demand_dialog)
        edit_button.pack(side="right", padx=5)

        remove_button = ctk.CTkButton(top_frame, text="Remover", command=self.remove_demand)
        remove_button.pack(side="right", padx=5)

        columns = ("id", "processo_numero", "descricao", "prazo_final", "status")
        self.tree = ttk.Treeview(left_frame_container, columns=columns, show="headings", selectmode="browse")
        # Configurações de cabeçalho e coluna (semelhantes às outras abas)
        self.tree.heading("id", text="ID")
        self.tree.heading("processo_numero", text="Nº Processo")
        self.tree.heading("descricao", text="Descrição da Demanda")
        self.tree.heading("prazo_final", text="Prazo Final")
        self.tree.heading("status", text="Status")

        self.tree.column("id", width=40, stretch=False, anchor="center")
        self.tree.column("processo_numero", width=130)
        self.tree.column("descricao", width=250)
        self.tree.column("prazo_final", width=100, anchor="center")
        self.tree.column("status", width=100, anchor="center")
        
        self.apply_treeview_style() # Aplicar estilo
        self.tree.pack(fill="both", expand=True, pady=(0,0))
        self.tree.bind("<<TreeviewSelect>>", self.on_demand_select)
        
        # --- Frame Direito (Calendário) ---
        right_frame_container = ctk.CTkFrame(main_paned_window, fg_color="transparent")
        main_paned_window.add(right_frame_container, weight=1)

        ctk.CTkLabel(right_frame_container, text="Calendário de Demandas", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)
        
        # Usando tkcalendar.Calendar diretamente na aba
        self.calendar_view = Calendar(right_frame_container, selectmode='day', date_pattern='yyyy-mm-dd', locale='pt_BR')
        self.calendar_view.pack(fill="both", expand=True, padx=10, pady=5)
        self.calendar_view.bind("<<CalendarSelected>>", self.on_calendar_date_selected)

        # Botão para limpar filtro do calendário
        clear_calendar_filter_button = ctk.CTkButton(right_frame_container, text="Mostrar Todas as Demandas", command=self.load_demands)
        clear_calendar_filter_button.pack(pady=5)

        self.update_process_list_cache()
        self.highlight_calendar_dates_with_demands()


    def apply_treeview_style(self):
        style = ttk.Style(self)
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
        # Seleciona id e numero_processo para o combobox
        self.all_processes = self.db_handler.fetch_all("SELECT id, numero_processo FROM processos ORDER BY numero_processo ASC")

    def on_demand_select(self, event=None):
        selected_item = self.tree.selection()
        if selected_item:
            self.selected_demand_id = self.tree.item(selected_item[0])["values"][0]
        else:
            self.selected_demand_id = None

    def load_demands(self, search_term: str = "", filter_date: Optional[str] = None):
        for i in self.tree.get_children():
            self.tree.delete(i)
        
        query = """
            SELECT d.id, p.numero_processo, d.descricao, 
                   STRFTIME('%d/%m/%Y', d.prazo_final) as prazo_final_formatado, d.status
            FROM demandas d
            LEFT JOIN processos p ON d.processo_id = p.id
        """
        params = []
        conditions = []

        if search_term:
            conditions.append("(d.descricao LIKE ? OR p.numero_processo LIKE ?)")
            params.extend([f"%{search_term}%", f"%{search_term}%"])
        
        if filter_date: # filter_date deve estar no formato 'YYYY-MM-DD'
            conditions.append("d.prazo_final = ?")
            params.append(filter_date)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        query += " ORDER BY d.prazo_final ASC, p.numero_processo ASC"
            
        demands_data = self.db_handler.fetch_all(query, tuple(params))
        for demand in demands_data:
            self.tree.insert("", "end", values=(
                demand["id"], 
                demand["numero_processo"] if demand["numero_processo"] else "N/A",
                demand["descricao"], 
                demand["prazo_final_formatado"],
                demand["status"]
            ))
        self.selected_demand_id = None
        if not filter_date: # Só atualiza o calendário se não estiver filtrando por data (evita loop)
            self.highlight_calendar_dates_with_demands()


    def filter_demands(self):
        search_term = self.search_entry.get()
        # Não filtra por data aqui, o calendário faz isso
        self.load_demands(search_term=search_term, filter_date=None)


    def on_calendar_date_selected(self, event=None):
        selected_date_str = self.calendar_view.get_date() # Formato YYYY-MM-DD
        self.load_demands(filter_date=selected_date_str)


    def highlight_calendar_dates_with_demands(self):
        self.calendar_view.calevent_remove('all') # Limpa eventos anteriores
        
        demands_with_deadlines = self.db_handler.fetch_all("SELECT DISTINCT prazo_final FROM demandas WHERE prazo_final IS NOT NULL")
        
        for demand_date_obj in demands_with_deadlines:
            date_str = demand_date_obj["prazo_final"] # Formato YYYY-MM-DD do DB
            if date_str:
                try:
                    event_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                    # Adiciona um evento ao calendário. 'demand_due' é uma tag para o evento.
                    self.calendar_view.calevent_create(event_date, 'Prazo', 'demand_due')
                except ValueError:
                    print(f"Data inválida no banco para demanda: {date_str}")
        
        # Configura a aparência da tag 'demand_due'
        # Cores podem ser ajustadas. Ex: 'red' para prazos.
        self.calendar_view.tag_config('demand_due', background='orange', foreground='black')


    def add_demand_dialog(self):
        self.update_process_list_cache()
        if not self.all_processes:
            messagebox.showinfo("Aviso", "Nenhum processo cadastrado. Por favor, adicione um processo primeiro.", parent=self)
            return
        DemandFormDialog(self, title="Adicionar Nova Demanda", db_handler=self.db_handler, processes=self.all_processes)

    def edit_demand_dialog(self):
        if not self.selected_demand_id:
            messagebox.showwarning("Seleção Necessária", "Por favor, selecione uma demanda para editar.", parent=self)
            return
        
        demand_data_raw = self.db_handler.fetch_one("SELECT * FROM demandas WHERE id = ?", (self.selected_demand_id,))
        if demand_data_raw:
            demand_data = dict(demand_data_raw)
            self.update_process_list_cache()
            DemandFormDialog(self, title="Editar Demanda", db_handler=self.db_handler, processes=self.all_processes, demand_data=demand_data)
        else:
            messagebox.showerror("Erro", "Demanda não encontrada.", parent=self)

    def remove_demand(self):
        if not self.selected_demand_id:
            messagebox.showwarning("Seleção Necessária", "Por favor, selecione uma demanda para remover.", parent=self)
            return

        confirm = messagebox.askyesno("Confirmar Remoção", "Tem certeza que deseja remover esta demanda?", parent=self)
        if confirm:
            self.db_handler.execute_query("DELETE FROM demandas WHERE id = ?", (self.selected_demand_id,))
            messagebox.showinfo("Sucesso", "Demanda removida com sucesso.", parent=self)
            self.load_demands() # Recarrega e atualiza o calendário
        self.selected_demand_id = None


class DemandFormDialog(ctk.CTkToplevel):
    def __init__(self, master_tab, title, db_handler, processes, demand_data=None):
        super().__init__(master_tab.master)
        self.master_tab = master_tab
        self.db_handler = db_handler
        self.processes = processes # Lista de dicts {'id': id, 'numero_processo': numero}
        self.demand_data = demand_data

        self.grab_set()
        self.title(title)
        self.resizable(False, False)
        
        master_win = self.master_tab.winfo_toplevel()
        x = master_win.winfo_x() + (master_win.winfo_width() - 500) // 2
        y = master_win.winfo_y() + (master_win.winfo_height() - 500) // 2 # Aumentado para data
        self.geometry(f"500x500+{x}+{y}")

        self.entries = {}
        self.process_var = ctk.StringVar()
        self.status_var = ctk.StringVar()
        self.prazo_final_var = ctk.StringVar() # Para o campo de data

        status_options = ["Pendente", "Em andamento", "Concluída", "Cancelada"]

        form_frame = ctk.CTkFrame(self, fg_color="transparent")
        form_frame.pack(padx=20, pady=20, fill="both", expand=True)

        # Layout
        ctk.CTkLabel(form_frame, text="Processo Associado:").grid(row=0, column=0, padx=5, pady=8, sticky="w")
        process_combobox = ctk.CTkComboBox(form_frame, width=300, variable=self.process_var, 
                                           values=[p['numero_processo'] for p in self.processes])
        process_combobox.grid(row=0, column=1, columnspan=2, padx=5, pady=8, sticky="ew")
        self.entries["processo_id"] = process_combobox

        ctk.CTkLabel(form_frame, text="Descrição da Demanda:").grid(row=1, column=0, padx=5, pady=8, sticky="nw")
        desc_textbox = ctk.CTkTextbox(form_frame, width=300, height=100)
        desc_textbox.grid(row=1, column=1, columnspan=2, padx=5, pady=8, sticky="nsew")
        self.entries["descricao"] = desc_textbox
        
        ctk.CTkLabel(form_frame, text="Prazo Final:").grid(row=2, column=0, padx=5, pady=8, sticky="w")
        prazo_entry = ctk.CTkEntry(form_frame, width=200, textvariable=self.prazo_final_var, placeholder_text="AAAA-MM-DD")
        prazo_entry.grid(row=2, column=1, padx=5, pady=8, sticky="ew")
        self.entries["prazo_final"] = prazo_entry
        calendar_button = ctk.CTkButton(form_frame, text="📅", width=40, command=self.open_calendar_popup)
        calendar_button.grid(row=2, column=2, padx=5, pady=8)


        ctk.CTkLabel(form_frame, text="Status:").grid(row=3, column=0, padx=5, pady=8, sticky="w")
        status_optionmenu = ctk.CTkOptionMenu(form_frame, width=300, variable=self.status_var, values=status_options)
        status_optionmenu.grid(row=3, column=1, columnspan=2, padx=5, pady=8, sticky="ew")
        self.entries["status"] = status_optionmenu
        
        form_frame.columnconfigure(1, weight=1)
        form_frame.rowconfigure(1, weight=1) # Descrição expande

        if self.demand_data:
            # Selecionar processo
            process_id_to_select = self.demand_data.get("processo_id")
            if process_id_to_select:
                for proc_obj in self.processes:
                    if proc_obj['id'] == process_id_to_select:
                        self.process_var.set(proc_obj['numero_processo'])
                        break
            
            desc_text = self.demand_data.get("descricao", "")
            if desc_text:
                self.entries["descricao"].insert("1.0", desc_text)
            
            prazo = self.demand_data.get("prazo_final") # Formato YYYY-MM-DD
            if prazo:
                self.prazo_final_var.set(prazo)

            self.status_var.set(self.demand_data.get("status", status_options[0]))
        else: # Nova demanda
            if self.processes:
                 self.process_var.set(self.processes[0]['numero_processo'])
            self.status_var.set(status_options[0])


        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.pack(pady=10, fill="x", padx=20)

        save_button = ctk.CTkButton(button_frame, text="Salvar", command=self.save_demand)
        save_button.pack(side="right", padx=5)
        cancel_button = ctk.CTkButton(button_frame, text="Cancelar", command=self.destroy, fg_color="gray")
        cancel_button.pack(side="right", padx=5)

    def open_calendar_popup(self):
        initial_date_str = self.prazo_final_var.get()
        CalendarPopup(self, on_date_select_callback=self.set_prazo_final, initial_date=initial_date_str, title="Selecionar Prazo Final")

    def set_prazo_final(self, selected_date):
        self.prazo_final_var.set(selected_date) # selected_date já vem como YYYY-MM-DD

    def save_demand(self):
        descricao = self.entries["descricao"].get("1.0", "end-1c").strip()
        prazo_final_str = self.prazo_final_var.get().strip() # YYYY-MM-DD
        status = self.status_var.get()
        
        selected_process_numero = self.process_var.get()
        processo_id = None
        for proc_obj in self.processes:
            if proc_obj['numero_processo'] == selected_process_numero:
                processo_id = proc_obj['id']
                break

        if not descricao:
            messagebox.showerror("Campo Obrigatório", "Descrição da demanda é obrigatória.", parent=self)
            return
        if not processo_id:
            messagebox.showerror("Campo Obrigatório", "Processo associado é obrigatório.", parent=self)
            return
        
        # Validação da data (opcional, mas bom ter)
        if prazo_final_str:
            try:
                datetime.strptime(prazo_final_str, "%Y-%m-%d")
            except ValueError:
                messagebox.showerror("Data Inválida", "Formato de Prazo Final inválido. Use AAAA-MM-DD.", parent=self)
                return
        else: # Se a data não for obrigatória, pode ser NULL
            prazo_final_str = None


        try:
            if self.demand_data: # Editando
                query = """UPDATE demandas SET processo_id=?, descricao=?, prazo_final=?, status=?
                           WHERE id = ?"""
                params = (processo_id, descricao, prazo_final_str, status, self.demand_data["id"])
            else: # Adicionando
                query = """INSERT INTO demandas (processo_id, descricao, prazo_final, status)
                           VALUES (?, ?, ?, ?)"""
                params = (processo_id, descricao, prazo_final_str, status)
            
            self.db_handler.execute_query(query, params)
            
            messagebox.showinfo("Sucesso", f"Demanda {'atualizada' if self.demand_data else 'adicionada'} com sucesso!", parent=self)
            self.master_tab.load_demands() # Recarrega a lista e atualiza o calendário
            self.destroy()
        except Exception as e:
            messagebox.showerror("Erro ao Salvar", f"Ocorreu um erro: {e}", parent=self)

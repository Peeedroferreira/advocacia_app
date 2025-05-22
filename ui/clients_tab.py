import customtkinter as ctk
from tkinter import ttk, messagebox, simpledialog
from database.db_handler import DBHandler
from typing import Optional

class ClientsTab(ctk.CTkFrame):
    def __init__(self, master, db_handler: DBHandler):
        super().__init__(master, fg_color="transparent")
        self.db_handler = db_handler
        self.pack(fill="both", expand=True)

        self.selected_client_id: Optional[int] = None

        self.create_widgets()
        self.load_clients()

    def create_widgets(self):
        # Frame para busca e botões de ação
        top_frame = ctk.CTkFrame(self, fg_color="transparent")
        top_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(top_frame, text="Buscar Cliente:").pack(side="left", padx=(0, 5))
        self.search_entry = ctk.CTkEntry(top_frame, placeholder_text="Nome ou CPF...")
        self.search_entry.pack(side="left", padx=5, fill="x", expand=True)
        self.search_entry.bind("<KeyRelease>", lambda event: self.filter_clients())

        self.search_by_var = ctk.StringVar(value="Nome")
        search_by_options = ["Nome", "CPF"]
        search_by_menu = ctk.CTkOptionMenu(top_frame, variable=self.search_by_var, values=search_by_options, command=lambda _: self.filter_clients())
        search_by_menu.pack(side="left", padx=5)
        
        add_button = ctk.CTkButton(top_frame, text="Adicionar Cliente", command=self.add_client_dialog)
        add_button.pack(side="right", padx=5)
        
        edit_button = ctk.CTkButton(top_frame, text="Editar Cliente", command=self.edit_client_dialog)
        edit_button.pack(side="right", padx=5)

        remove_button = ctk.CTkButton(top_frame, text="Remover Cliente", command=self.remove_client)
        remove_button.pack(side="right", padx=5)

        # Treeview para listar clientes
        columns = ("id", "nome", "cpf", "telefone", "email")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", selectmode="browse")

        self.tree.heading("id", text="ID")
        self.tree.heading("nome", text="Nome Completo")
        self.tree.heading("cpf", text="CPF")
        self.tree.heading("telefone", text="Telefone")
        self.tree.heading("email", text="E-mail")

        self.tree.column("id", width=50, minwidth=40, stretch=False, anchor="center")
        self.tree.column("nome", width=250, minwidth=150)
        self.tree.column("cpf", width=120, minwidth=100, anchor="center")
        self.tree.column("telefone", width=120, minwidth=100, anchor="center")
        self.tree.column("email", width=200, minwidth=150)
        
        # Estilo para o Treeview (para combinar com CustomTkinter)
        style = ttk.Style(self)
        # Usar um tema que se adapte melhor, ou definir cores manualmente
        current_theme = ctk.get_appearance_mode()
        if current_theme == "Dark":
            style.theme_use("clam") # Ou 'alt', 'default', 'classic'
            style.configure("Treeview",
                            background="#2B2B2B",
                            foreground="white",
                            fieldbackground="#2B2B2B",
                            borderwidth=0)
            style.configure("Treeview.Heading",
                            background="#212121",
                            foreground="white",
                            relief="flat")
            style.map("Treeview.Heading", background=[('active', '#313131')])
        else: # Light mode
            style.theme_use("clam")
            style.configure("Treeview",
                            background="white",
                            foreground="black",
                            fieldbackground="white",
                            borderwidth=0)
            style.configure("Treeview.Heading",
                            background="#E1E1E1",
                            foreground="black",
                            relief="flat")
            style.map("Treeview.Heading", background=[('active', '#D1D1D1')])


        self.tree.pack(fill="both", expand=True, padx=10, pady=(0,10))
        self.tree.bind("<<TreeviewSelect>>", self.on_client_select)

        # Scrollbar para o Treeview
        scrollbar = ttk.Scrollbar(self.tree, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        # scrollbar.pack(side="right", fill="y") # Não funciona bem com pack dentro do treeview
        # Colocar treeview e scrollbar em um frame se necessário para melhor layout

    def on_client_select(self, event=None):
        selected_item = self.tree.selection()
        if selected_item:
            self.selected_client_id = self.tree.item(selected_item[0])["values"][0]
        else:
            self.selected_client_id = None

    def load_clients(self, search_term: str = "", search_by: str = "Nome"):
        for i in self.tree.get_children():
            self.tree.delete(i)
        
        query = "SELECT id, nome, cpf, telefone, email FROM clientes"
        params = []
        if search_term:
            if search_by == "Nome":
                query += " WHERE nome LIKE ?"
            elif search_by == "CPF":
                query += " WHERE cpf LIKE ?"
            params.append(f"%{search_term}%")
        query += " ORDER BY nome ASC"
            
        clients_data = self.db_handler.fetch_all(query, tuple(params))
        for client in clients_data:
            self.tree.insert("", "end", values=(client["id"], client["nome"], client["cpf"], client["telefone"], client["email"]))
        self.selected_client_id = None # Limpar seleção após recarregar

    def filter_clients(self):
        search_term = self.search_entry.get()
        search_by = self.search_by_var.get()
        self.load_clients(search_term, search_by)

    def add_client_dialog(self):
        dialog = ClientFormDialog(self, title="Adicionar Novo Cliente", db_handler=self.db_handler)
        # A lógica de inserção e recarregamento está dentro do ClientFormDialog ou é chamada por ele
        # Se o dialog retornar um status de sucesso, recarregamos
        # Isso é simplificado aqui; o dialog deveria ter um callback ou retornar um valor
        # self.load_clients() # O ClientFormDialog chamará self.master_tab.load_clients()

    def edit_client_dialog(self):
        if not self.selected_client_id:
            messagebox.showwarning("Seleção Necessária", "Por favor, selecione um cliente para editar.", parent=self)
            return
        
        client_data = self.db_handler.fetch_one("SELECT * FROM clientes WHERE id = ?", (self.selected_client_id,))
        if client_data:
            dialog = ClientFormDialog(self, title="Editar Cliente", db_handler=self.db_handler, client_data=dict(client_data))
            # self.load_clients() # O ClientFormDialog chamará self.master_tab.load_clients()
        else:
            messagebox.showerror("Erro", "Cliente não encontrado.", parent=self)


    def remove_client(self):
        if not self.selected_client_id:
            messagebox.showwarning("Seleção Necessária", "Por favor, selecione um cliente para remover.", parent=self)
            return

        client_info = self.db_handler.fetch_one("SELECT nome, cpf FROM clientes WHERE id = ?", (self.selected_client_id,))
        if not client_info:
            messagebox.showerror("Erro", "Cliente não encontrado.", parent=self)
            return

        confirm = messagebox.askyesno("Confirmar Remoção",
                                      f"Tem certeza que deseja remover o cliente:\nNome: {client_info['nome']}\nCPF: {client_info['cpf']}\n\nTODOS OS PROCESSOS, DEMANDAS E AUDIÊNCIAS ASSOCIADOS A ESTE CLIENTE SERÃO REMOVIDOS.",
                                      parent=self)
        if confirm:
            # Devido ao ON DELETE CASCADE nas chaves estrangeiras,
            # remover um cliente também removerá processos, demandas e audiências associadas.
            self.db_handler.execute_query("DELETE FROM clientes WHERE id = ?", (self.selected_client_id,))
            messagebox.showinfo("Sucesso", "Cliente removido com sucesso.", parent=self)
            self.load_clients()
        self.selected_client_id = None


class ClientFormDialog(ctk.CTkToplevel):
    def __init__(self, master_tab, title, db_handler, client_data=None):
        super().__init__(master_tab.master) # O master do Toplevel deve ser a janela principal ou uma aba
        self.master_tab = master_tab # Referência à aba de clientes para recarregar a lista
        self.db_handler = db_handler
        self.client_data = client_data # Dados para edição; None para adição

        self.grab_set()
        self.title(title)
        # self.geometry("450x400") # Ajustar conforme necessário
        self.resizable(False, False)
        
        # Centralizar
        master_win = self.master_tab.winfo_toplevel()
        x = master_win.winfo_x() + (master_win.winfo_width() - 450) // 2
        y = master_win.winfo_y() + (master_win.winfo_height() - 400) // 2
        self.geometry(f"450x400+{x}+{y}")


        self.entries = {}
        fields = [
            ("Nome Completo:", "nome", ""),
            ("CPF:", "cpf", ""),
            ("Telefone:", "telefone", ""),
            ("E-mail:", "email", ""),
            ("Endereço:", "endereco", "")
        ]

        form_frame = ctk.CTkFrame(self, fg_color="transparent")
        form_frame.pack(padx=20, pady=20, fill="both", expand=True)

        for i, (label_text, key, placeholder) in enumerate(fields):
            label = ctk.CTkLabel(form_frame, text=label_text)
            label.grid(row=i, column=0, padx=5, pady=8, sticky="w")
            entry = ctk.CTkEntry(form_frame, placeholder_text=placeholder, width=280)
            entry.grid(row=i, column=1, padx=5, pady=8, sticky="ew")
            self.entries[key] = entry
            if client_data and client_data.get(key):
                entry.insert(0, client_data.get(key))
        
        form_frame.columnconfigure(1, weight=1) # Faz a coluna dos entries expandir

        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.pack(pady=10, fill="x", padx=20)

        save_button = ctk.CTkButton(button_frame, text="Salvar", command=self.save_client)
        save_button.pack(side="right", padx=5)
        cancel_button = ctk.CTkButton(button_frame, text="Cancelar", command=self.destroy, fg_color="gray")
        cancel_button.pack(side="right", padx=5)

        if client_data: # Se for edição, o CPF não deve ser editável idealmente, ou requer cuidado
            self.entries["cpf"].configure(state="disabled")


    def save_client(self):
        data = {key: entry.get().strip() for key, entry in self.entries.items()}

        if not data["nome"] or not data["cpf"]:
            messagebox.showerror("Campos Obrigatórios", "Nome e CPF são obrigatórios.", parent=self)
            return

        # Validação de CPF (simples, pode ser melhorada)
        if not data["cpf"].isdigit() or not (11 <= len(data["cpf"]) <= 14): # 11 para CPF, 14 para CNPJ
            messagebox.showerror("CPF Inválido", "CPF deve conter apenas números e ter 11 dígitos (ou 14 para CNPJ).", parent=self)
            return

        try:
            if self.client_data: # Editando
                # CPF não é alterado aqui, usamos o ID para o WHERE
                query = """UPDATE clientes SET nome=?, telefone=?, email=?, endereco=?
                           WHERE id = ?"""
                params = (data["nome"], data["telefone"], data["email"], data["endereco"], self.client_data["id"])
            else: # Adicionando
                query = """INSERT INTO clientes (nome, cpf, telefone, email, endereco)
                           VALUES (?, ?, ?, ?, ?)"""
                params = (data["nome"], data["cpf"], data["telefone"], data["email"], data["endereco"])
            
            self.db_handler.execute_query(query, params)
            
            messagebox.showinfo("Sucesso", f"Cliente {'atualizado' if self.client_data else 'adicionado'} com sucesso!", parent=self)
            self.master_tab.load_clients() # Recarrega a lista na aba principal
            self.destroy()
        except Exception as e: # Especificamente sqlite3.IntegrityError para CPF duplicado
            if "UNIQUE constraint failed: clientes.cpf" in str(e):
                 messagebox.showerror("Erro", f"Já existe um cliente com o CPF {data['cpf']}.", parent=self)
            else:
                messagebox.showerror("Erro ao Salvar", f"Ocorreu um erro: {e}", parent=self)


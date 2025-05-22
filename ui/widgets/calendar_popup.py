import customtkinter as ctk
from tkcalendar import Calendar
from datetime import datetime

class CalendarPopup(ctk.CTkToplevel):
    def __init__(self, master, on_date_select_callback=None, initial_date=None, title="Selecionar Data"):
        super().__init__(master)
        self.on_date_select_callback = on_date_select_callback
        
        self.title(title)
        self.lift()  # Traz a janela para frente
        self.attributes("-topmost", True)  # Mantém no topo
        self.grab_set() # Impede interação com a janela pai

        # Centralizar o Toplevel em relação ao master
        master_x = master.winfo_rootx()
        master_y = master.winfo_rooty()
        master_width = master.winfo_width()
        master_height = master.winfo_height()
        
        width = 300
        height = 320 # Ajustado para caber o botão
        
        x = master_x + (master_width - width) // 2
        y = master_y + (master_height - height) // 2
        self.geometry(f"{width}x{height}+{x}+{y}")
        self.resizable(False, False)

        current_year = datetime.now().year
        if initial_date:
            try:
                if isinstance(initial_date, str):
                    initial_date = datetime.strptime(initial_date, "%Y-%m-%d") # ou "%d/%m/%Y"
                day, month, year = initial_date.day, initial_date.month, initial_date.year
            except ValueError:
                day, month, year = datetime.now().day, datetime.now().month, current_year
        else:
            day, month, year = datetime.now().day, datetime.now().month, current_year

        self.cal = Calendar(self, selectmode='day',
                            year=year, month=month, day=day,
                            date_pattern='yyyy-mm-dd', # Formato da data retornada
                            locale='pt_BR') # Para nomes em português
        self.cal.pack(pady=10, padx=10, fill="both", expand=True)

        confirm_button = ctk.CTkButton(self, text="Confirmar", command=self.emit_date)
        confirm_button.pack(pady=10)

        self.protocol("WM_DELETE_WINDOW", self.on_close) # Lidar com o fechamento

    def emit_date(self):
        selected_date = self.cal.get_date() # Formato 'yyyy-mm-dd'
        if self.on_date_select_callback:
            self.on_date_select_callback(selected_date)
        self.on_close()

    def on_close(self):
        self.grab_release()
        self.destroy()

if __name__ == '__main__':
    # Teste do CalendarPopup
    class AppTest(ctk.CTk):
        def __init__(self):
            super().__init__()
            self.title("Teste Popup Calendário")
            self.geometry("400x300")

            self.date_label = ctk.CTkLabel(self, text="Nenhuma data selecionada")
            self.date_label.pack(pady=20)

            self.open_button = ctk.CTkButton(self, text="Abrir Calendário", command=self.open_calendar)
            self.open_button.pack(pady=10)

        def open_calendar(self):
            # Exemplo de data inicial (pode ser string ou datetime)
            # initial = datetime.now() + timedelta(days=5)
            initial = "2024-12-25"
            CalendarPopup(self, on_date_select_callback=self.update_date_label, initial_date=initial)

        def update_date_label(self, selected_date):
            self.date_label.configure(text=f"Data Selecionada: {selected_date}")

    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("blue")
    app = AppTest()
    app.mainloop()

import customtkinter as ctk
from tkinter import scrolledtext, messagebox, ttk
import os
import datetime
import logging
import threading
import time 
import math 
import queue
from PIL import Image, ImageTk 


COLOR_BG_DARK = "#19232D"  
COLOR_BG_MEDIUM = "#26323F" 
COLOR_BG_LIGHT = "#37474F"  
COLOR_TEXT_PRIMARY = "#FFFFFF" 
COLOR_TEXT_ACCENT = "#64B5F6" 
COLOR_TEXT_ACCENT_LIGHT = "#90CAF9" 
COLOR_TEXT_SUCCESS = "#8BC34A"
COLOR_TEXT_WARNING = "#FFC107" 
COLOR_TEXT_ERROR = "#F44336"  
COLOR_BORDER = "#455A64"    
COLOR_SEPARATOR = "#546E7A"


FONT_PRIMARY = ("Segoe UI", 30)
FONT_LABEL_BOLD = ("Segoe UI", 20, "bold")
FONT_HEADER = ("Segoe UI", 30, "bold")
FONT_SUBHEADER = ("Segoe UI", 20, "bold")
FONT_CARD_VALUE = ("Consolas", 24, "bold")
FONT_CARD_LABEL = ("Segoe UI", 9)
FONT_LOG = ("Consolas", 15)
FONT_TIMER_ACCENT = ("Consolas", 20, "bold")

FONT_TABLE_HEADER = ("Segoe UI", 9, "bold") 
FONT_TABLE_CONTENT = ("Segoe UI", 9) 


app_logger = logging.getLogger(__name__)


def ease_out_quad(t):
    return 1 - (1 - t) * (1 - t)

def ease_in_out_quad(t):
    if t < 0.5:
        return 2 * t * t
    return 1 - (-2 * t + 2) ** 2 / 2

class LogTextHandler(logging.Handler):
    """
    Um handler de log personalizado que envia mensagens de log para um widget ScrolledText.
    """
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget
        self.text_widget.configure(state='disabled') 

    def emit(self, record):
        msg = self.format(record)
        self.text_widget.configure(state='normal')

       
        max_lines = 1000
        if int(self.text_widget.index('end-1c').split('.')[0]) > max_lines:
           
            self.text_widget.delete(1.0, 2.0)

        self.text_widget.insert(ctk.END, msg + "\n") 
        self.text_widget.see(ctk.END)
        self.text_widget.configure(state='disabled')


class Tooltip:
    """
    Classe para criar tooltips (dicas de ferramenta) para widgets.
    Será adaptada para CTk.
    """
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        self.id = None
        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)

    def show_tooltip(self, event=None):
        self.id = self.widget.after(500, self._show_tooltip_after_delay)

    def _show_tooltip_after_delay(self):
        if self.tooltip_window or not self.text:
            return
        x = y = 0
       
        x, y, cx, cy = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 20

        self.tooltip_window = ctk.CTkToplevel(self.widget) 
        self.tooltip_window.wm_overrideredirect(True) 
        self.tooltip_window.wm_geometry(f"+{x}+{y}")

        
        label = ctk.CTkLabel(self.tooltip_window, text=self.text,
                             fg_color="#F1FCEB", 
                             text_color="black", 
                             corner_radius=5, 
                             font=("tahoma", 8, "normal"), wraplength=200)
        label.pack(ipadx=5, ipady=3) 


    def hide_tooltip(self, event=None):
        if self.id:
            self.widget.after_cancel(self.id)
        if self.tooltip_window:
            self.tooltip_window.destroy()
        self.tooltip_window = None


class AppGUI:
    def __init__(self, master,
                 toggle_monitor_callback, abrir_relatorios_callback, abrir_logs_callback,
                 intervalo_consulta_ms, intervalo_atualizacao_ms):
        self.master = master
        self.toggle_monitor_callback = toggle_monitor_callback
        self.abrir_relatorios_callback = abrir_relatorios_callback
        self.abrir_logs_callback = abrir_logs_callback

        self.intervalo_consulta_ms = intervalo_consulta_ms
        self.intervalo_atualizacao_ms = intervalo_atualizacao_ms

        self.executando_consultas_ui = False
        self.ultima_consulta_rows = []
        self.ultima_consulta_columns = []
        self.current_filter = ""
        self.search_bar_visible = False
        self.current_view = "Dashboard"

       
        self._resize_after_id = None
        self._animation_id = None
        self._page_transition_id = None

        self.animation_step_time = 10
        self.animation_duration = 300
        self.page_transition_duration = 400

        self.log_queue = queue.Queue() 

        self._setup_ctk_theme()
        self._create_widgets()
    

       
        self.view_frame_map = {
            "Dashboard": self.dashboard_frame,
            "Monitoramento": self.monitoring_frame,
            "Logs": self.logs_frame
        }

        self._log_text_handler = LogTextHandler(self.log_text)

        
        self.master.bind("<Configure>", self._debounce_resize)

       
        self.show_view("Dashboard", animate=False) 
        
    def _atualizar_card_email_status(self):
        if self.ultima_hora_envio_email:
            self.lbl_email_status_card.configure(
                text=f"ENVIADO\n{self.ultima_hora_envio_email}",
                text_color=COLOR_TEXT_SUCCESS,
                justify="center"
            )
        else:
            self.lbl_email_status_card.configure(
                text="N/A",
                text_color=COLOR_TEXT_ACCENT,
                justify="center"
            )


    def _debounce_resize(self, event):
        """
        Método de debounce para o evento de redimensionamento.
        Cancela qualquer agendamento anterior e agenda um novo.
        """
        if event.width != self.master.winfo_width() or event.height != self.master.winfo_height():
            if self._resize_after_id:
                self.master.after_cancel(self._resize_after_id)
            self._resize_after_id = self.master.after(150, self._on_resize) 


    def _setup_ctk_theme(self):
       
        ctk.set_appearance_mode("white") 
        ctk.set_default_color_theme("blue")

    def _create_widgets(self):
        self.master.grid_columnconfigure(0, weight=0) 
        self.master.grid_columnconfigure(1, weight=1) 
        self.master.grid_rowconfigure(0, weight=1)

        
        sidebar_frame = ctk.CTkFrame(self.master, width=200, corner_radius=10)
        sidebar_frame.grid(row=0, column=0, sticky="nswe", padx=10, pady=10)
        sidebar_frame.grid_propagate(False)
        sidebar_frame.grid_columnconfigure(0, weight=1)

      
        self.main_content_frame = ctk.CTkFrame(self.master, corner_radius=10)
        self.main_content_frame.grid(row=0, column=1, sticky="nswe", padx=10, pady=10)
        self.main_content_frame.grid_columnconfigure(0, weight=1)
        self.main_content_frame.grid_rowconfigure(0, weight=0) 
        self.main_content_frame.grid_rowconfigure(1, weight=0) 
        self.main_content_frame.grid_rowconfigure(2, weight=1)


        ctk.CTkLabel(sidebar_frame, text="🔷 Monitoramento",
                     font=ctk.CTkFont("Segoe UI", 12, "bold"),
                     text_color=COLOR_TEXT_ACCENT,
                     ).pack(pady=(20, 20), padx=15, anchor="w")


        ctk.CTkFrame(sidebar_frame, height=2, fg_color=COLOR_SEPARATOR, corner_radius=0).pack(fill="x", padx=10, pady=(0, 10))


        ctk.CTkLabel(sidebar_frame, text="GERAL",
                     font=FONT_CARD_LABEL,
                     ).pack(pady=(10, 5), padx=15, anchor="w")

        self.btn_dashboard = ctk.CTkButton(sidebar_frame, text="Dashboard",
                                            command=lambda: self.show_view("Dashboard"),
                                            corner_radius=8,
                                            fg_color="transparent",
                                            hover_color=COLOR_BG_LIGHT,
                                            anchor="w", font=("Segoe UI", 11, "bold"))
        self.btn_dashboard.pack(fill="x", pady=2, padx=10)
        Tooltip(self.btn_dashboard, "Visão geral do status do monitoramento e últimos resultados.")

        self.btn_monitoring = ctk.CTkButton(sidebar_frame, text="Monitoramento",
                                            command=lambda: self.show_view("Monitoramento"),
                                            corner_radius=8,
                                            fg_color="transparent",
                                            hover_color=COLOR_BG_LIGHT,
                                            anchor="w", font=("Segoe UI", 11, "bold"))
        self.btn_monitoring.pack(fill="x", pady=2, padx=10)
        Tooltip(self.btn_monitoring, "Aba principal para controlar e visualizar o monitoramento.")

        self.btn_logs_sidebar = ctk.CTkButton(sidebar_frame, text="Logs",
                                              command=lambda: self.show_view("Logs"),
                                              corner_radius=8,
                                              fg_color="transparent",
                                              hover_color=COLOR_BG_LIGHT,
                                              anchor="w", font=("Segoe UI", 11, "bold"))
        self.btn_logs_sidebar.pack(fill="x", pady=2, padx=10)
        Tooltip(self.btn_logs_sidebar, "Visualiza os registros de atividade e erros do sistema.")

    
        ctk.CTkFrame(sidebar_frame, height=2, fg_color=COLOR_SEPARATOR, corner_radius=0).pack(fill="x", padx=10, pady=(10, 10))

        ctk.CTkLabel(sidebar_frame, text="FERRAMENTAS",
                     font=FONT_CARD_LABEL,
                     ).pack(pady=(10, 5), padx=15, anchor="w")

        btn_open_reports = ctk.CTkButton(sidebar_frame, text="Abrir Relatórios",
                                         command=self.abrir_relatorios_callback,
                                         corner_radius=8,
                                         fg_color="transparent",
                                         hover_color=COLOR_BG_LIGHT,
                                         anchor="w", font=("Segoe UI", 11, "bold"))
        btn_open_reports.pack(fill="x", pady=2, padx=10)
        Tooltip(btn_open_reports, "Abre a pasta onde os relatórios CSV são salvos.")

        btn_open_logs = ctk.CTkButton(sidebar_frame, text="Abrir Pasta de Logs",
                                      command=self.abrir_logs_callback,
                                      corner_radius=8,
                                      fg_color="transparent",
                                      hover_color=COLOR_BG_LIGHT,
                                      anchor="w", font=("Segoe UI", 11, "bold"))
        btn_open_logs.pack(fill="x", pady=2, padx=10)
        Tooltip(btn_open_logs, "Abre a pasta onde os arquivos de log são salvos.")

        
        self.top_bar_frame = ctk.CTkFrame(self.main_content_frame, fg_color="transparent")
        self.top_bar_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 0))
        self.top_bar_frame.grid_columnconfigure(0, weight=1)
        self.top_bar_frame.grid_columnconfigure(1, weight=1)
        self.top_bar_frame.grid_columnconfigure(2, weight=0)

        self.greeting_label = ctk.CTkLabel(self.top_bar_frame,
                                           text=f"{self.get_time_of_day_greeting()}",
                                           font=FONT_HEADER)
        self.greeting_label.grid(row=0, column=0, sticky="w", padx=(0,20))



        self.search_bar_frame = ctk.CTkFrame(self.top_bar_frame, fg_color="transparent")
        self.search_bar_frame.grid_columnconfigure(0, weight=1) 

        
        self.search_entry_dashboard = ctk.CTkEntry(self.search_bar_frame,
                                                   width=0, 
                                                   font=FONT_PRIMARY,
                                                   placeholder_text="Pesquisar na tabela...")
        self.search_entry_dashboard.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.search_entry_dashboard.bind("<Return>", lambda event: self.apply_filter())
        Tooltip(self.search_entry_dashboard, "Digite um termo para filtrar os resultados da tabela abaixo.")

        btn_search = ctk.CTkButton(self.search_bar_frame, text="🔍 Buscar",
                                   command=self.apply_filter,
                                   corner_radius=8)
        btn_search.pack(side="left", padx=(0,5))
        Tooltip(btn_search, "Clique para aplicar o filtro na tabela.")

        btn_clear_filter = ctk.CTkButton(self.search_bar_frame, text="Limpar Filtro",
                                         command=self.clear_filter,
                                         corner_radius=8,
                                         fg_color="gray",
                                         hover_color="darkgray")
        btn_clear_filter.pack(side="left", padx=(0, 20))
        Tooltip(btn_clear_filter, "Limpa o filtro e mostra todos os resultados novamente.")

   
        self.btn_toggle_search = ctk.CTkButton(self.top_bar_frame, text="🔎",
                                               command=self.toggle_search_bar,
                                               width=40,
                                               corner_radius=8)
        
        ctk.CTkFrame(self.main_content_frame, height=2, fg_color=COLOR_SEPARATOR, corner_radius=0).grid(row=1, column=0, sticky="ew", pady=(10, 10))

       
        self.dashboard_frame = ctk.CTkFrame(self.main_content_frame, corner_radius=10, fg_color="transparent")
        self.dashboard_frame.grid(row=2, column=0, sticky="nsew", padx=0, pady=0) 

        self.monitoring_frame = ctk.CTkFrame(self.main_content_frame, corner_radius=10, fg_color="transparent")
        self.monitoring_frame.grid(row=2, column=0, sticky="nsew", padx=0, pady=0) 
        self.logs_frame = ctk.CTkFrame(self.main_content_frame, corner_radius=10, fg_color="transparent")
        self.logs_frame.grid(row=2, column=0, sticky="nsew", padx=0, pady=0) 


       
        self.dashboard_frame.grid_columnconfigure((0,1), weight=1)
        self.dashboard_frame.grid_rowconfigure(1, weight=1) 

        cards_frame = ctk.CTkFrame(self.dashboard_frame, corner_radius=10)
        cards_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(10, 10), padx=15)
        cards_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self.lbl_status_card = self._create_status_card(cards_frame, "STATUS GERAL", "Iniciando...", COLOR_TEXT_PRIMARY, 0)
        self.lbl_last_query_time_card = self._create_status_card(cards_frame, "TEMPO ÚLTIMA CONSULTA", "N/A", COLOR_TEXT_PRIMARY, 1)
        self.lbl_rows_found_card = self._create_status_card(cards_frame, "LINHAS ENCONTRADAS", "N/A", COLOR_TEXT_PRIMARY, 2)
        self.lbl_email_status_card = self._create_status_card(cards_frame, "STATUS EMAIL", "N/A", COLOR_TEXT_PRIMARY, 3)

      
        results_frame = ctk.CTkFrame(self.dashboard_frame, corner_radius=10)
        results_frame.grid(row=1, column=0, columnspan=2, sticky="nswe", padx=15, pady=10)
        results_frame.grid_columnconfigure(0, weight=1)
        results_frame.grid_rowconfigure(0, weight=1)

        s = ttk.Style()
        s.theme_use('clam')
        s.configure("Treeview",
                    background=COLOR_BG_MEDIUM,
                    foreground=COLOR_TEXT_PRIMARY,
                    fieldbackground=COLOR_BG_MEDIUM,
                    font=FONT_TABLE_CONTENT,
                    rowheight=25)
        s.map('Treeview',
              background=[('selected', COLOR_TEXT_ACCENT)],
              foreground=[('selected', 'white')])
        s.configure("Treeview.Heading",
                    font=FONT_TABLE_HEADER,
                    background=COLOR_BG_LIGHT,
                    foreground=COLOR_TEXT_PRIMARY,
                    relief="flat")
        s.map('Treeview.Heading',
              background=[('active', COLOR_BORDER)])

        self.treeview_results = ttk.Treeview(results_frame, show="headings", style="Treeview")
        self.treeview_results.grid(row=0, column=0, sticky="nswe")

        scrollbar_y = ctk.CTkScrollbar(results_frame, orientation="vertical", command=self.treeview_results.yview)
        scrollbar_y.grid(row=0, column=1, sticky="ns")
        self.treeview_results.configure(yscrollcommand=scrollbar_y.set)

        scrollbar_x = ctk.CTkScrollbar(results_frame, orientation="horizontal", command=self.treeview_results.xview)
        scrollbar_x.grid(row=1, column=0, sticky="ew")
        self.treeview_results.configure(xscrollcommand=scrollbar_x.set)

        # --- Monitoring Frame Conteúdo ---
        self.monitoring_frame.grid_columnconfigure(0, weight=1)
        self.monitoring_frame.grid_rowconfigure(0, weight=1)

        monitor_panel = ctk.CTkFrame(self.monitoring_frame, corner_radius=10)
        monitor_panel.pack(fill="both", expand=True, padx=20, pady=20)
        monitor_panel.grid_columnconfigure(0, weight=1)
        monitor_panel.grid_rowconfigure((0,1,2,3), weight=0)
        monitor_panel.grid_rowconfigure(4, weight=1)


        ctk.CTkLabel(monitor_panel, text="Controle de Monitoramento",
                     font=FONT_SUBHEADER).pack(pady=10)

        self.status_label = ctk.CTkLabel(monitor_panel, text="Status: Aguardando iniciar...",
                                         font=FONT_PRIMARY)
        self.status_label.pack(pady=5)

        self.countdown_label = ctk.CTkLabel(monitor_panel, text="00:00",
                                             font=FONT_TIMER_ACCENT,
                                             text_color=COLOR_TEXT_SUCCESS)
        self.countdown_label.pack(pady=5)

        self.progressbar = ctk.CTkProgressBar(monitor_panel, orientation="horizontal",
                                              height=15,
                                              corner_radius=8,
                                              progress_color=COLOR_TEXT_ACCENT)
        self.progressbar.pack(pady=10, fill="x", padx=50)
        self.progressbar.set(0)

        self.btn_toggle_monitor = ctk.CTkButton(monitor_panel, text="Iniciar Monitoramento",
                                                command=self.toggle_monitor_callback,
                                                corner_radius=8,
                                                height=40,
                                                font=("Segoe UI", 12, "bold"))
        self.btn_toggle_monitor.pack(pady=20)

        # --- Logs Frame Conteúdo ---
        self.logs_frame.grid_columnconfigure(0, weight=1)
        self.logs_frame.grid_rowconfigure(0, weight=1)

        current_theme = ctk.get_appearance_mode().lower()
        if current_theme == "white":
            log_bg_color = ctk.ThemeManager.theme["CTkFrame"]["fg_color"][0]
            log_text_color = ctk.ThemeManager.theme["CTkLabel"]["text_color"][0]
        else:
            log_bg_color = ctk.ThemeManager.theme["CTkFrame"]["fg_color"][1]
            log_text_color = ctk.ThemeManager.theme["CTkLabel"]["text_color"][1]


        self.log_text = scrolledtext.ScrolledText(self.logs_frame, wrap="word",
                                                 font=FONT_LOG,
                                                 bg=log_bg_color,
                                                 fg=log_text_color,
                                                 insertbackground="white",
                                                 relief="flat",
                                                 borderwidth=0)
        self.log_text.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)


    def show_view(self, view_name, animate=False):
        if self.current_view == view_name and animate:
            return
        if self._page_transition_id:
            self.master.after_cancel(self._page_transition_id)
            self._page_transition_id = None
        if animate:
            self._animate_page_transition(self.current_view, view_name)
        else:
            self.dashboard_frame.grid_remove()
            self.monitoring_frame.grid_remove()
            self.logs_frame.grid_remove()
            frame_to_show = self.view_frame_map.get(view_name)
            if frame_to_show:
                frame_to_show.grid()
            else:
                app_logger.error(f"Erro: Frame '{view_name}' não encontrado no mapeamento para exibição instantânea.")
            self._update_view_visibility(view_name)
            self.current_view = view_name
            self._update_sidebar_button_style(view_name)
    def _update_view_visibility(self, view_name):
        if view_name == "Dashboard":
            self.btn_toggle_search.grid(row=0, column=2, sticky="e", padx=(0, 0))
            if self.search_bar_visible:
                self.search_bar_frame.grid(row=0, column=1, sticky="ew", padx=(0, 20))
                self.top_bar_frame.grid_columnconfigure(1, weight=1)
                self.search_entry_dashboard.configure(width=300)
            else:
                self.search_bar_frame.grid_forget()
                self.search_entry_dashboard.configure(width=0)
        else:
            self.search_bar_frame.grid_forget()
            self.search_entry_dashboard.configure(width=0)
            self.btn_toggle_search.grid_forget()
            self.top_bar_frame.grid_columnconfigure(1, weight=0)
        self.main_content_frame.grid_rowconfigure(2, weight=1)


    def _update_sidebar_button_style(self, active_view):
        self.btn_dashboard.configure(fg_color="transparent")
        self.btn_monitoring.configure(fg_color="transparent")
        self.btn_logs_sidebar.configure(fg_color="transparent")

        if active_view == "Dashboard":
            self.btn_dashboard.configure(fg_color=COLOR_BG_LIGHT)
        elif active_view == "Monitoramento":
            self.btn_monitoring.configure(fg_color=COLOR_BG_LIGHT)
        elif active_view == "Logs":
            self.btn_logs_sidebar.configure(fg_color=COLOR_BG_LIGHT)


    def _animate_page_transition(self, old_view_name, new_view_name):
        old_frame = self.view_frame_map.get(old_view_name)
        new_frame = self.view_frame_map.get(new_view_name)

        if not old_frame or not new_frame:
            app_logger.error(f"Erro: Frame não encontrado para transição. Old: {old_view_name}, New: {new_view_name}")
            self._update_view_visibility(new_view_name)
            self._update_sidebar_button_style(new_view_name)
            self.current_view = new_view_name
            return
        old_frame.grid(row=2, column=0, sticky="nsew", padx=0, pady=0)
        new_frame.grid(row=2, column=0, sticky="nsew", padx=0, pady=0)

        self.master.update_idletasks()
        main_content_width = self.main_content_frame.winfo_width()
        new_frame.place(relx=1.0, rely=0.0, relwidth=1.0, relheight=1.0, anchor="nw")
        old_frame.place(relx=0.0, rely=0.0, relwidth=1.0, relheight=1.0, anchor="nw")

        start_time = time.time()
        start_x_old = 0.0
        start_x_new = 1.0

        def animate_step():
            elapsed_time = (time.time() - start_time) * 1000 # em ms
            progress = min(1.0, elapsed_time / self.page_transition_duration)
            eased_progress = ease_in_out_quad(progress) # Usar easing para suavidade

            # Calcular a nova posição
            # Frame antigo: desliza de 0 para -1 (sai pela esquerda)
            new_x_old = start_x_old - eased_progress
            # Frame novo: desliza de 1 para 0 (entra pela direita)
            new_x_new = start_x_new - eased_progress

            old_frame.place(relx=new_x_old, rely=0.0, relwidth=1.0, relheight=1.0, anchor="nw")
            new_frame.place(relx=new_x_new, rely=0.0, relwidth=1.0, relheight=1.0, anchor="nw")

            if progress < 1.0:
                self._page_transition_id = self.master.after(self.animation_step_time, animate_step)
            else:
                # Animação concluída, posiciona os frames corretamente
                old_frame.place_forget() # Remove o frame antigo
                new_frame.place_forget() # Remove o place para que o grid volte a gerenciar
                new_frame.grid(row=2, column=0, sticky="nsew", padx=0, pady=0) # Volta para o grid

                self.current_view = new_view_name
                self._update_view_visibility(new_view_name)
                self._update_sidebar_button_style(new_view_name)
                self._page_transition_id = None
                app_logger.debug(f"Transição para {new_view_name} concluída.")

        self._page_transition_id = self.master.after(self.animation_step_time, animate_step)


    def _on_resize(self):
        """
        Método chamado quando a janela é redimensionada.
        Garante que as colunas da treeview se ajustem ao novo tamanho.
        """
        self.master.update_idletasks() # Crucial para obter as dimensões corretas.

        self._animate_column_widths(self.ultima_consulta_rows)


    def get_log_text_handler(self):
        """Retorna o handler de log para o ScrolledText da GUI."""
        return self._log_text_handler

    def get_time_of_day_greeting(self):
        """Retorna a saudação do dia baseada na hora atual."""
        current_hour = datetime.datetime.now().hour
        if current_hour >= 1 and current_hour <= 12:
            return "Bom dia!"
        elif current_hour >= 12 and current_hour <= 19:
            return "Boa tarde!"
        elif current_hour >= 19 and current_hour <= 00:
            return "Boa noite!"

    def _create_status_card(self, parent_frame, title_text, value_text, value_color, column_index):
        """Cria e retorna um frame de card de status com título e valor usando CTk."""
        card_frame = ctk.CTkFrame(parent_frame, corner_radius=10)
        card_frame.grid(row=0, column=column_index, sticky="nsew", padx=7, pady=7)
        card_frame.grid_columnconfigure(0, weight=1)

        title_label = ctk.CTkLabel(card_frame, text=title_text,
                                   font=FONT_CARD_LABEL)
        title_label.pack(pady=(5, 2))

        value_label = ctk.CTkLabel(card_frame, text=value_text,
                                   font=FONT_CARD_VALUE,
                                   text_color=value_color,
                                   justify="center")
        value_label.pack(pady=(2, 5))
        return value_label

    def update_status_labels_on_query_start(self):
        self.status_label.configure(text_color=COLOR_TEXT_WARNING, text="Status: Executando consulta...")
        self.lbl_status_card.configure(text="CONSULTANDO...", text_color=COLOR_TEXT_WARNING)
        current_theme_colors = ctk.ThemeManager.theme["CTkLabel"]["text_color"]
        text_color_for_current_mode = current_theme_colors[0] if ctk.get_appearance_mode() == "Dark" else current_theme_colors[1]

        self.lbl_last_query_time_card.configure(text="Calculando...", text_color=text_color_for_current_mode)
        self.lbl_rows_found_card.configure(text="...", text_color=text_color_for_current_mode)
        self.lbl_email_status_card.configure(text="AGUARDANDO ENVIO...", text_color=text_color_for_current_mode)
        self.progressbar.set(0)
        self.lbl_email_status_card.configure(justify="center")
        self.ultima_hora_envio_email = datetime.datetime.now().strftime("%H:%M:%S")
        self._atualizar_card_email_status()

    def update_status_labels_on_query_complete(self, total_rows, query_time, email_sent_status, status_message):
        current_theme_colors = ctk.ThemeManager.theme["CTkLabel"]["text_color"]
        text_color_for_current_mode = current_theme_colors[0] if ctk.get_appearance_mode() == "Dark" else current_theme_colors[1]

        self.status_label.configure(text=status_message, text_color=text_color_for_current_mode)
        self.lbl_last_query_time_card.configure(text=f"{query_time:.2f}s", text_color=text_color_for_current_mode)

        if email_sent_status is True:
            pass
            hora = datetime.datetime.now().strftime("%H:%M:%S")
            self.lbl_email_status_card.configure(text=f"ENVIADO\n{hora}", text_color=COLOR_TEXT_SUCCESS, justify="center")

        elif email_sent_status is False:
            self.lbl_email_status_card.configure(text="FALHA", text_color=COLOR_TEXT_ERROR)
        else: # None (não necessitou enviar ou não foi tentado)
            self.lbl_email_status_card.configure(text="N/A", text_color=text_color_for_current_mode)

        self.lbl_status_card.configure(text="ATIVO", text_color=COLOR_TEXT_SUCCESS)

    def update_countdown_and_progress(self, tempo_restante_ms):
        total_interval_seconds = self.intervalo_consulta_ms / 1000
        current_remaining_seconds = tempo_restante_ms / 1000

        if total_interval_seconds > 0:
            progress_percentage = ((total_interval_seconds - current_remaining_seconds) / total_interval_seconds)
            self.progressbar.set(progress_percentage)
        else:
            self.progressbar.set(0)

        minutes, seconds = divmod(int(current_remaining_seconds), 60)
        time_str = f"{minutes:02d}:{seconds:02d}"
        self.countdown_label.configure(text=time_str)

    def set_monitor_button_text(self, text):
        self.btn_toggle_monitor.configure(text=text)

    def reset_ui_on_stop(self):
        self.set_monitor_button_text("Iniciar Monitoramento")
        current_theme_colors = ctk.ThemeManager.theme["CTkLabel"]["text_color"]
        text_color_for_current_mode = current_theme_colors[0] if ctk.get_appearance_mode() == "Dark" else current_theme_colors[1]

        self.status_label.configure(text="Status: Monitoramento Parado.", text_color=text_color_for_current_mode)
        self.countdown_label.configure(text="00:00")
        self.progressbar.set(0)

        self.lbl_status_card.configure(text="PARADO", text_color=COLOR_TEXT_ERROR)
        self.lbl_last_query_time_card.configure(text="N/A", text_color=text_color_for_current_mode)
        self.lbl_rows_found_card.configure(text="N/A", text_color=text_color_for_current_mode)
        self.lbl_email_status_card.configure(text="N/A", text_color=text_color_for_current_mode)

        for i in self.treeview_results.get_children():
            self.treeview_results.delete(i)
        self.clear_filter()

    def start_auto_monitor(self):
        self.toggle_monitor_callback()

    def toggle_search_bar(self):
       
        if self.current_view != "Dashboard":
            return

        if self._animation_id:
            self.master.after_cancel(self._animation_id)
            self._animation_id = None

        if self.search_bar_visible:
            self.btn_toggle_search.configure(text="🔎")
            self.clear_filter() 
            self._animate_search_bar(target_width=0, direction="hide")
        else:
            self.search_bar_frame.grid(row=0, column=1, sticky="ew", padx=(0, 20))
            self.top_bar_frame.grid_columnconfigure(1, weight=1)
            self.btn_toggle_search.configure(text="✖️")
            self._animate_search_bar(target_width=300, direction="show") 
            self.search_entry_dashboard.focus_set()

        self.search_bar_visible = not self.search_bar_visible

    def _animate_search_bar(self, target_width, direction):
        current_width = self.search_entry_dashboard.winfo_width()
        if current_width <= 1 and direction == "hide": 
            self.search_bar_frame.grid_forget()
            return
        if current_width >= target_width and direction == "show": 
            return

        start_time = time.time()
        start_width = current_width

        def animate():
            elapsed_time = (time.time() - start_time) * 1000
            progress = min(1.0, elapsed_time / self.animation_duration)

            if direction == "show":
                eased_progress = ease_out_quad(progress)
                new_width = start_width + (target_width - start_width) * eased_progress
                if new_width >= target_width:
                    new_width = target_width
                    self.search_entry_dashboard.configure(width=int(new_width))
                    self._animation_id = None
                    return
            else: 
                eased_progress = ease_in_out_quad(progress) 
                new_width = start_width - (start_width - target_width) * eased_progress
                if new_width <= target_width:
                    new_width = target_width
                    self.search_entry_dashboard.configure(width=int(new_width))
                    self.search_bar_frame.grid_forget() 
                    self._animation_id = None
                    return

            self.search_entry_dashboard.configure(width=int(new_width))
            self._animation_id = self.master.after(self.animation_step_time, animate)

        self._animation_id = self.master.after(self.animation_step_time, animate)


    def display_results(self, rows, columns):
        for i in self.treeview_results.get_children():
            self.treeview_results.delete(i)

        self.treeview_results['columns'] = columns
        for col in columns:
            self.treeview_results.heading(col, text=col, anchor=ctk.W)
            self.treeview_results.column(col, anchor=ctk.W)

        self.ultima_consulta_rows = rows
        self.ultima_consulta_columns = columns

        self.apply_filter()

    def apply_filter(self):
        filter_text = self.search_entry_dashboard.get().strip().lower()
        self.current_filter = filter_text

        for i in self.treeview_results.get_children():
            self.treeview_results.delete(i)

        if not self.ultima_consulta_rows:
            self.lbl_rows_found_card.configure(text="0")
            self._animate_column_widths(displayed_rows=[])
            return

        filtered_count = 0
        displayed_rows = []

        for row_index, row in enumerate(self.ultima_consulta_rows):
            row_values_str = [str(item).lower() for item in row]

            if any(filter_text in value for value in row_values_str):
                formatted_row_for_display = []
                for item in row:
                    s_item = str(item)
                    if s_item.startswith("'") and s_item.endswith("'"):
                        s_item = s_item[1:-1]
                    elif s_item.startswith("(") and s_item.endswith(")"):
                        s_item = s_item[1:-1]
                    if s_item.endswith(','):
                        s_item = s_item[:-1]
                    formatted_row_for_display.append(s_item.strip())

                self.treeview_results.insert("", "end", values=formatted_row_for_display)
                filtered_count += 1
                displayed_rows.append(formatted_row_for_display)

        if filter_text:
            self.lbl_rows_found_card.configure(text=f"{filtered_count} / {len(self.ultima_consulta_rows)}")
        else:
            self.lbl_rows_found_card.configure(text=f"{len(self.ultima_consulta_rows)}")

        self._animate_column_widths(displayed_rows=displayed_rows)


    def clear_filter(self):
        self.search_entry_dashboard.delete(0, ctk.END)
        self.apply_filter()

    def _calculate_target_column_widths(self, displayed_rows):
        """
        Calcula as larguras ALVO para cada coluna.
        Esta função APENAS CALCULA, NÃO APLICA as larguras.
        """
        if not self.ultima_consulta_columns:
            return {}

        data_to_size = displayed_rows if displayed_rows is not None else self.ultima_consulta_rows

        char_width_approx = 8.0
        min_column_width = 50
        max_column_width = 300

        
        current_treeview_area_width = self.treeview_results.winfo_width()
        if current_treeview_area_width <= 1:
            current_treeview_area_width = self.main_content_frame.winfo_width() - 30 
            if current_treeview_area_width <= 0:
                current_treeview_area_width = 800


        column_widths = {}
        for col_name in self.ultima_consulta_columns:
            try:
                col_idx = self.ultima_consulta_columns.index(col_name)
                current_col_width = len(col_name) * char_width_approx + 25 

                for row_data in data_to_size[:100]: 
                    if col_idx < len(row_data):
                        cell_content = str(row_data[col_idx])
                        current_col_width = max(current_col_width, len(cell_content) * char_width_approx + 15)

                current_col_width = max(min_column_width, min(current_col_width, max_column_width))
                column_widths[col_name] = current_col_width

            except ValueError:
                app_logger.warning(f"Coluna '{col_name}' não encontrada para ajuste de largura.")
                column_widths[col_name] = min_column_width

        total_calculated_width = sum(column_widths.values())
        num_columns = len(self.ultima_consulta_columns)

        if num_columns > 0:
            if total_calculated_width < current_treeview_area_width:
                remaining_width = current_treeview_area_width - total_calculated_width
                base_extra_per_column = remaining_width / num_columns
                for col_name in column_widths:
                    new_width = column_widths[col_name] + base_extra_per_column
                    column_widths[col_name] = int(min(max_column_width, new_width))
            elif total_calculated_width > current_treeview_area_width:
                compression_factor = current_treeview_area_width / total_calculated_width
                for col_name in column_widths:
                    new_width = column_widths[col_name] * compression_factor
                    column_widths[col_name] = int(max(min_column_width, new_width))

        return column_widths

    def _animate_column_widths(self, displayed_rows):
        """
        Inicia a animação para ajustar as larguras das colunas da Treeview.
        """
        if not self.ultima_consulta_columns:
            return

        
        if self._animation_id:
            self.master.after_cancel(self._animation_id)
            self._animation_id = None

        target_widths = self._calculate_target_column_widths(displayed_rows)
        start_widths = {}

        for col_name in self.ultima_consulta_columns:
            try:
                
                start_widths[col_name] = self.treeview_results.column(col_name, "width")
            except Exception:
               
                start_widths[col_name] = self.treeview_results.column(col_name, "minwidth") 
        start_time = time.time()
        def animate_step():
            elapsed_time = (time.time() - start_time) * 1000 
            progress = min(1.0, elapsed_time / self.animation_duration)

            eased_progress = ease_out_quad(progress) 

            all_columns_reached_target = True

            for col_name in self.ultima_consulta_columns:
                start_w = start_widths.get(col_name, 0)
                target_w = target_widths.get(col_name, 0)

               
                if abs(start_w - target_w) < 1 and progress >= 0.99: 
                    new_width = target_w
                else:
                    new_width = start_w + (target_w - start_w) * eased_progress

                self.treeview_results.column(col_name, width=int(new_width))

                if abs(new_width - target_w) > 1:
                    all_columns_reached_target = False

            if not all_columns_reached_target and progress < 1.0:
                self._animation_id = self.master.after(self.animation_step_time, animate_step)
            else:
                
                for col_name in self.ultima_consulta_columns:
                    self.treeview_results.column(col_name, width=int(target_widths.get(col_name, 0)))
                app_logger.debug("Animação das colunas concluída.")
                self._animation_id = None 

        self._animation_id = self.master.after(self.animation_step_time, animate_step)
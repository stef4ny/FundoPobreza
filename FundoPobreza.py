import pyodbc
import logging
import time
import datetime
import os
import pandas as pd
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import subprocess
import platform
import threading
import sys
from tkinter import messagebox
import customtkinter as ctk
from typing import List, Tuple, Optional, Dict, Any
import winsound
from emailBuilder import htmlEmailBody, send_email
from functools import lru_cache
from PIL import Image, ImageTk
from config import INTERVALO_CONSULTA_MS
GLOBAL_INTERVALO_CONSULTA_MS = INTERVALO_CONSULTA_MS 


from config import (
    EMAIL_REMETENTE, SENHA_APPLICATIVO_GMAIL, EMAIL_DESTINATARIO,
    ASSUNTO_EMAIL,  DIRETORIO_RELATORIOS, DIRETORIO_LOGS, CORPO_EMAIL_FIXO,
    DB_DRIVER, DB_SYSTEM, DB_UID, DB_PWD, DB_DEFAULT_LIBRARIES,
    INTERVALO_ATUALIZACAO_MS,
    SQL_QUERY_ALERTA, #EMAIL_MAX_ROWS_DISPLAY,
    WORKING_HOURS_START_HOUR, WORKING_HOURS_END_HOUR
)

@lru_cache(maxsize=32)
def cached_conectdb():
    return conectdb()

@lru_cache(maxsize=32)
def executar_consulta_cached(query: str, data_referencia: datetime.date):
    conn = cached_conectdb()
    cursor = conn.cursor()
    cursor.execute(query)
    return cursor.fetchall()

class PaginatedResults:
    def __init__(self, all_results, page_size=50):
        self.all_results = all_results
        self.page_size = page_size
        self.current_page = 0
        
    def get_page(self, page_num):
        start = page_num * self.page_size
        end = start + self.page_size
        return self.all_results[start:end]
    
    @property
    def total_pages(self):
        return len(self.all_results) // self.page_size + 1


try:
    from telinha import AppGUI, LogTextHandler, COLOR_TEXT_SUCCESS, COLOR_TEXT_ERROR, COLOR_TEXT_WARNING, COLOR_TEXT_PRIMARY
except ImportError as e:
   
    temp_logger = logging.getLogger("temp_logger")
    temp_logger.setLevel(logging.ERROR)
    temp_handler = logging.StreamHandler(sys.stdout)
    temp_handler.setFormatter(logging.Formatter('[%(asctime)s] [%(levelname)s] %(message)s'))
    temp_logger.addHandler(temp_handler)
    temp_logger.error(f"Não foi possível importar AppGUI ou LogTextHandler de telinha.py: {e}")
    sys.exit(1)


if not os.path.exists(DIRETORIO_LOGS):
    os.makedirs(DIRETORIO_LOGS)


log_file_name = datetime.datetime.now().strftime(os.path.join(DIRETORIO_LOGS, "app_log_%Y-%m-%d.log"))


app_logger = logging.getLogger(__name__)
app_logger.setLevel(logging.INFO)

formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

file_handler = logging.FileHandler(log_file_name, encoding='utf-8')
file_handler.setFormatter(formatter)
app_logger.addHandler(file_handler)

stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setFormatter(formatter)
app_logger.addHandler(stream_handler)


consulta_agendada_id = None
contador_agendado_id = None
executando_consultas = False
consulta_thread = None


app_gui_instance = None


def conectdb():
    app_gui_instance.master.after(0, lambda: app_gui_instance.status_label.configure(text_color=COLOR_TEXT_WARNING, text="Status: Conectando ao banco de dados..."))
    try:
        conexao = pyodbc.connect(
            f'Driver={DB_DRIVER};'
            f'System={DB_SYSTEM};'
            f'Uid={DB_UID};'
            f'Pwd={DB_PWD};'
            f'DefaultLibraries={DB_DEFAULT_LIBRARIES};'
        )
        app_logger.info("Conexão com o banco realizada com sucesso.")
        return conexao
    except Exception as e:
        app_logger.error(f"Erro ao conectar no banco: {e}", exc_info=True)
        return None

def gerar_relatorio_csv(rows, columns):
    if not rows:
        app_logger.info("Não há dados para gerar o relatório CSV, Nenhum arquivo será criado.")  # só envia o arquivo .CSV se houver resultados.
        return None

    if not os.path.exists(DIRETORIO_RELATORIOS):
        os.makedirs(DIRETORIO_RELATORIOS) 
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    nome_arquivo_csv = f"alerta_pobreza_relatorio_{timestamp}.csv"
    caminho_arquivo_csv = os.path.join(DIRETORIO_RELATORIOS, nome_arquivo_csv)

    app_gui_instance.master.after(0, lambda: app_gui_instance.status_label.configure(text_color=COLOR_TEXT_WARNING, text="Status: Gerando relatório CSV..."))
    try:
        processed_rows = [list(row) for row in rows] if rows else []
        df = pd.DataFrame(processed_rows, columns=columns)

       
        if 'DATA' in df.columns:
           
            df['DATA'] = pd.to_datetime(df['DATA'], errors='coerce').dt.strftime('%d/%m/%y') 
           
            df['DATA'] = df['DATA'].fillna('')
           
            df['DATA'] = " " + df['DATA'].astype(str)

        df.to_csv(caminho_arquivo_csv, index=False, encoding='utf-8', sep=';')
        app_logger.info(f"Relatório CSV '{nome_arquivo_csv}' gerado com sucesso em '{DIRETORIO_RELATORIOS}'.")
        return caminho_arquivo_csv
    except Exception as e:
        app_logger.error(f"Erro ao gerar relatório CSV: {e}", exc_info=True)
        return None


def horarioTrabalho(): #AQUIIII
    now = datetime.datetime.now()
    is_weekday = 0 <= now.weekday() <= 4 
   
    is_working_hour = WORKING_HOURS_START_HOUR <= now.hour < WORKING_HOURS_END_HOUR
    return is_weekday and is_working_hour

def abrir_diretorio(caminho, tipo_diretorio, gui_instance):
    abs_caminho = os.path.abspath(caminho)
    if not os.path.exists(abs_caminho):
        os.makedirs(abs_caminho)
        app_logger.info(f"Diretório '{abs_caminho}' criado.")

    sistema = platform.system()
    try:
        if sistema == "Windows":
            os.startfile(abs_caminho)
        elif sistema == "Darwin":
            subprocess.Popen(["open", abs_caminho])
        else:
            subprocess.Popen(["xdg-open", abs_caminho])
        app_logger.info(f"Diretório de {tipo_diretorio} aberto: '{abs_caminho}'")
    except Exception as e:
        if gui_instance:
            gui_instance.master.after(0, lambda: messagebox.showerror("Erro", f"Não foi possível abrir a pasta de {tipo_diretorio}: {e}"))
        app_logger.error(f"Não foi possível abrir a pasta de {tipo_diretorio} ('{abs_caminho}'): {e}", exc_info=True)

def abrir_diretorio_relatorios():
    if app_gui_instance:
        abrir_diretorio(DIRETORIO_RELATORIOS, "relatórios", app_gui_instance)
    else:
        app_logger.warning("Instância da GUI não disponível para abrir diretório de relatórios.")

def abrir_diretorio_logs():
    if app_gui_instance:
        abrir_diretorio(DIRETORIO_LOGS, "logs", app_gui_instance)
    else:
        app_logger.warning("Instância da GUI não disponível para abrir diretório de logs.")


def _executar_consulta_logica(gui_instance_ref):
    global executando_consultas, consulta_agendada_id

    if not executando_consultas:
        app_logger.info("Consulta cancelada: Monitoramento foi parado.")
        return

    gui_instance_ref.master.after(0, lambda: gui_instance_ref.update_status_labels_on_query_start())

    df_for_email = pd.DataFrame()
    total_rows = 0
    query_time = 0.0
    email_sent_status = None
    status_message_on_complete = "Status: Consulta finalizada."

    try:
        if not horarioTrabalho():  #AQUIIIII
            app_logger.info(f"Fora do horário comercial (Seg-Sex, {WORKING_HOURS_START_HOUR}h-{WORKING_HOURS_END_HOUR}h). A consulta não será executada.")
            status_message_on_complete = "Status: Fora do horário comercial. Aguardando..."
            gui_instance_ref.master.after(0, lambda: gui_instance_ref.update_status_labels_on_query_complete(
                total_rows, query_time, None, status_message_on_complete
            ))
            
            if executando_consultas:
              
                consulta_agendada_id = gui_instance_ref.master.after(GLOBAL_INTERVALO_CONSULTA_MS, lambda: iniciar_thread_consulta(gui_instance_ref))
            return

        conn = conectdb()
        if conn is None:
            app_logger.error('Falha ao conectar ao banco de dados.')
            status_message_on_complete = "Status: Conexão falhou."
            gui_instance_ref.master.after(0, lambda: messagebox.showerror("Erro de Conexão", "Falha ao conectar ao banco de dados. Verifique o log."))
            gui_instance_ref.master.after(0, lambda: gui_instance_ref.update_status_labels_on_query_complete(
                total_rows, query_time, False, status_message_on_complete
            ))
            if executando_consultas:
               
                consulta_agendada_id = gui_instance_ref.master.after(GLOBAL_INTERVALO_CONSULTA_MS, lambda: iniciar_thread_consulta(gui_instance_ref))
            return

        cursor = conn.cursor()
        app_logger.info("Consulta Alerta Pobreza iniciada...")
        gui_instance_ref.master.after(0, lambda: gui_instance_ref.status_label.configure(text_color=COLOR_TEXT_WARNING, text="Status: Executando consulta SQL..."))

        t0 = time.time()
       
        query = SQL_QUERY_ALERTA  #QUERY
        cursor.execute(query)

        columns = [column[0] for column in cursor.description]
        rows = cursor.fetchall()
        total_rows = len(rows)
        query_time = time.time() - t0

        app_logger.info(f"Consulta executada em {query_time:.2f} segundos. Total de linhas retornadas: {total_rows}")
        gui_instance_ref.master.after(0, lambda: gui_instance_ref.status_label.configure(text_color=COLOR_TEXT_WARNING, text="Status: Processando resultados..."))

        processed_rows_for_df = [list(row) for row in rows] if rows else []
        df_resultados = pd.DataFrame(processed_rows_for_df, columns=columns)

       
        if 'DATA' in df_resultados.columns:
            df_resultados['DATA'] = pd.to_datetime(df_resultados['DATA'], errors='coerce').dt.strftime('%d/%m/%y') 
            df_resultados['DATA'] = df_resultados['DATA'].fillna('')


        gui_instance_ref.master.after(0, lambda: gui_instance_ref.display_results(df_resultados.values.tolist(), df_resultados.columns.tolist()))

        status_message_on_complete = f"Status: Consulta finalizada às {datetime.datetime.now().strftime('%H:%M:%S')}. {total_rows} linhas encontradas."

        lista_anexos = []
        if total_rows > 0:
            app_logger.info("Resultados encontrados. Gerando e enviando relatório(s)...")

            
            caminho_relatorio_csv = gerar_relatorio_csv(rows, columns) 
            if caminho_relatorio_csv:
                lista_anexos.append(caminho_relatorio_csv)

            
            df_for_email = df_resultados
            email_sent_status = send_email(
                anexos=lista_anexos,
                df_data_for_email=df_for_email,
                total_rows_found=total_rows,
                email_remetente=EMAIL_REMETENTE,
                senha_aplicativo=SENHA_APPLICATIVO_GMAIL,
                email_destinatario=EMAIL_DESTINATARIO,
                assunto_email=ASSUNTO_EMAIL,
                saudacao=gui_instance_ref.get_time_of_day_greeting() if gui_instance_ref else "Olá"
            ) 

        else:
          app_logger.info("Nenhum resultado encontrado. Relatório e e-mail não serão enviados.")
        gui_instance_ref.master.after(0, lambda: app_gui_instance.lbl_email_status_card.configure(
        text="NÃO ENVIADO (Sem Dados)", text_color=COLOR_TEXT_WARNING
    ))

        cursor.close()
        conn.close()
        app_logger.info("Conexão com o banco de dados fechada.")

    except Exception as e:
        app_logger.error(f"Erro inesperado durante a consulta: {e}", exc_info=True)
        status_message_on_complete = "Status: Erro na consulta."
        gui_instance_ref.master.after(0, lambda: messagebox.showerror("Erro de Consulta", f"Ocorreu um erro: {e}. Verifique o log."))
        email_sent_status = send_email(
            anexos=[],
            df_data_for_email=pd.DataFrame(),
            total_rows_found=0,
            email_remetente=EMAIL_REMETENTE,
            senha_aplicativo=SENHA_APPLICATIVO_GMAIL,
            email_destinatario=EMAIL_DESTINATARIO,
            assunto_email=ASSUNTO_EMAIL,
            saudacao=gui_instance_ref.get_time_of_day_greeting() if gui_instance_ref else "Olá"
        )
    finally:
        gui_instance_ref.master.after(0, lambda: gui_instance_ref.status_label.configure(text_color=COLOR_TEXT_PRIMARY, text="Status: Finalizando..."))
        gui_instance_ref.master.after(500, lambda: gui_instance_ref.update_status_labels_on_query_complete(
            total_rows, query_time, email_sent_status, status_message_on_complete
        ))
       
        if executando_consultas:
           
            consulta_agendada_id = gui_instance_ref.master.after(GLOBAL_INTERVALO_CONSULTA_MS, lambda: iniciar_thread_consulta(gui_instance_ref))


def iniciar_thread_consulta(gui_instance_ref):
    global consulta_thread, consulta_agendada_id, contador_agendado_id, executando_consultas

    if not executando_consultas:
        app_logger.info("Não reagendando consulta/contador: Monitoramento foi parado.")
        return

   
    if consulta_agendada_id:
        gui_instance_ref.master.after_cancel(consulta_agendada_id)
        consulta_agendada_id = None
        app_logger.debug("Agendamento de consulta anterior cancelado.")
    if contador_agendado_id:
        gui_instance_ref.master.after_cancel(contador_agendado_id)
        contador_agendado_id = None
        app_logger.debug("Agendamento de contador anterior cancelado.")

    app_logger.info("Agendando execução da próxima consulta e contador.")

    if consulta_thread and consulta_thread.is_alive():
        app_logger.info("Uma consulta já está em andamento. Não inicia nova thread.")
        
        gui_instance_ref.master.after(0, lambda: atualizar_contador_e_barra(
            gui_instance_ref, GLOBAL_INTERVALO_CONSULTA_MS 
        ))
    else:
        app_logger.info("Iniciando nova thread de consulta.")
        consulta_thread = threading.Thread(target=_executar_consulta_logica, args=(gui_instance_ref,))
        consulta_thread.daemon = True 
        consulta_thread.start()

       
        gui_instance_ref.master.after(0, lambda: atualizar_contador_e_barra(
            gui_instance_ref, GLOBAL_INTERVALO_CONSULTA_MS 
        ))


def atualizar_contador_e_barra(gui_instance_ref, tempo_restante_ms):
    global contador_agendado_id, executando_consultas

    if not executando_consultas:
        return

    tempo_restante_ms_next_step = max(0, tempo_restante_ms - INTERVALO_ATUALIZACAO_MS)

    gui_instance_ref.master.after(0, lambda: gui_instance_ref.update_countdown_and_progress(tempo_restante_ms))

    if tempo_restante_ms_next_step > 0:
        contador_agendado_id = gui_instance_ref.master.after(INTERVALO_ATUALIZACAO_MS, lambda: atualizar_contador_e_barra(
            gui_instance_ref, tempo_restante_ms_next_step
        ))
    else:
       
        gui_instance_ref.master.after(0, lambda: gui_instance_ref.status_label.configure(text_color=COLOR_TEXT_WARNING, text="Status: Preparando nova consulta..."))


def iniciar_monitoramento_logica(gui_instance_ref):
    global executando_consultas

    if executando_consultas:
        app_logger.info("Tentativa de iniciar monitoramento já ativo. Ignorado.")
        return

    executando_consultas = True
    gui_instance_ref.master.after(0, lambda: gui_instance_ref.set_monitor_button_text("Parar Monitoramento"))
    gui_instance_ref.master.after(0, lambda: gui_instance_ref.status_label.configure(text="Status: Monitoramento Iniciado. Agendando primeira consulta...", text_color=COLOR_TEXT_SUCCESS))
    app_logger.info('Monitoramento Iniciado.')

   
    iniciar_thread_consulta(gui_instance_ref)


def parar_monitoramento_logica(gui_instance_ref):
    global consulta_agendada_id, contador_agendado_id, executando_consultas

    if not executando_consultas:
        app_logger.info("Tentativa de parar monitoramento já inativo. Ignorado.")
        return

    executando_consultas = False
    app_logger.info('Monitoramento Parado.')

    if consulta_agendada_id:
        gui_instance_ref.master.after_cancel(consulta_agendada_id)
        consulta_agendada_id = None
        app_logger.info("Agendamento de consulta cancelado.")
    if contador_agendado_id:
        gui_instance_ref.master.after_cancel(contador_agendado_id)
        contador_agendado_id = None
        app_logger.info("Agendamento de contador cancelado.")

    gui_instance_ref.master.after(0, lambda: gui_instance_ref.reset_ui_on_stop())

    if consulta_thread and consulta_thread.is_alive():
        app_logger.warning("Uma consulta ainda está em andamento. Ela terminará e não reagendará.")
    else:
        app_logger.info("Nenhuma consulta ativa para esperar.")

def alternar_monitoramento_callback():
    global executando_consultas, app_gui_instance

    if app_gui_instance is None:
        app_logger.error("Instância da GUI não disponível para alternar monitoramento.")
        return

    if executando_consultas:
        parar_monitoramento_logica(app_gui_instance)
    else:
        iniciar_monitoramento_logica(app_gui_instance)

def main():
    global app_gui_instance, GLOBAL_INTERVALO_CONSULTA_MS

    
    ctk.set_appearance_mode("Dark")
    ctk.set_default_color_theme("blue")

    root = ctk.CTk()
    root.title("Monitoramento Alerta Pobreza")
    root.geometry("1200x800")
    root.minsize(900, 600)
    root.resizable(True, True)
    
   
    app_gui_instance = AppGUI(
        master=root,
        toggle_monitor_callback=alternar_monitoramento_callback,
        abrir_relatorios_callback=abrir_diretorio_relatorios,
        abrir_logs_callback=abrir_diretorio_logs,
        intervalo_consulta_ms=GLOBAL_INTERVALO_CONSULTA_MS,
        intervalo_atualizacao_ms=INTERVALO_ATUALIZACAO_MS
    )

    
    app_logger.addHandler(app_gui_instance._log_text_handler)

    
    current_log_file = datetime.datetime.now().strftime(os.path.join(DIRETORIO_LOGS, "app_log_%Y-%m-%d.log"))

    if os.path.exists(current_log_file):
        try:
            with open(current_log_file, "r", encoding="utf-8", errors="replace") as f:
             
                log_lines = f.readlines()
                for line in log_lines:
                 
                    level = logging.INFO
                    if "[ERROR]" in line.upper():
                        level = logging.ERROR
                    elif "[WARNING]" in line.upper():
                        level = logging.WARNING
                    app_gui_instance.log_queue.put((line, level)) 
            app_gui_instance.log_text.see(ctk.END)
        except Exception as e:
            app_gui_instance.log_text.insert(ctk.END, f"[ERRO] Falha ao carregar log: {e}\n")
            app_logger.error(f"[ERRO] Falha ao carregar log para a GUI: {e}", exc_info=True)

    
    root.after(500, app_gui_instance.start_auto_monitor)

    root.mainloop()

if __name__ == "__main__":
    main()
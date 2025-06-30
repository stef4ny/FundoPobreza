import pyodbc
import logging
import time
import tkinter as tk
import datetime
from tkinter import scrolledtext, messagebox, ttk
from ttkthemes import ThemedTk # Mantém ThemedTk para o visual
import os
import pandas as pd
import smtplib # Importado para envio de email
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

# --- Configuração Global ---
INTERVALO_CONSULTA_MS = 20 * 60 * 1000
INTERVALO_ATUALIZACAO_MS = 1000 # Usei esse nome para ser consistente com o nome anterior

# Variáveis globais para controle e agendamento da execução
consulta_agendada_id = None
contador_agendado_id = None
executando_consultas = False # Variável de controle de estado (iniciado/parado)

# --- CONFIGURAÇÕES DE E-MAIL ---
EMAIL_REMETENTE = 'rodriguestefany98@gmail.com' # Email do remetente (do seu último exemplo)
SENHA_APLICATIVO_GMAIL = 'wqlf ylft acow dmsa' # Senha de aplicativo do remetente (do seu último exemplo)
EMAIL_DESTINATARIO = 'stefany.rodrigues@nagem.com.br, felipe.amaral@nagem.com.br, wedici.lins@nagem.com.br ' # E-mail do destinatário
# ASSUNTO_EMAIL: Será definido como "Alerta Pobreza - Notas com Erro 815"
CORPO_EMAIL_FIXO = """
Prezado(a),

Este é um relatório automático do sistema de monitoramento de Alerta Pobreza.
Na última consulta, foram encontrados os seguintes resultados:

"""
DIRETORIO_RELATORIOS = "relatorios" # Nome da pasta para salvar os relatórios

# Configuração de log
logging.basicConfig(
    filename='log_execucao_gui.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# --- Função de Conexão com Banco de Dados ---
def conectdb():
    try:
        conexao = pyodbc.connect(
            'Driver={Client Access ODBC Driver (32-bit)};'
            'System=10.1.0.2;'
            'Uid=CLAUDIO;'
            'Pwd=19957;'
            'DefaultLibraries=NAG0001;'
        )
        logging.info("Conexão com o banco realizada com sucesso.")
        return conexao
    except Exception as e:
        logging.error(f"Erro ao conectar no banco: {e}")
        return None

# --- Função para Gerar Relatório TXT ---
def gerar_relatorio_txt(conteudo_relatorio_txt, output_widget):
    if not os.path.exists(DIRETORIO_RELATORIOS):
        os.makedirs(DIRETORIO_RELATORIOS)

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    nome_arquivo = f"alerta_pobreza_relatorio_{timestamp}.txt"
    caminho_arquivo = os.path.join(DIRETORIO_RELATORIOS, nome_arquivo)

    try:
        with open(caminho_arquivo, "w", encoding="utf-8") as f:
            f.write(conteudo_relatorio_txt)
        output_widget.insert(tk.END, f"Relatório TXT '{nome_arquivo}' gerado com sucesso em '{DIRETORIO_RELATORIOS}'.\n")
        logging.info(f"Relatório TXT gerado: {caminho_arquivo}")
        return caminho_arquivo
    except Exception as e:
        output_widget.insert(tk.END, f"Erro ao gerar relatório TXT: {e}\n")
        logging.error(f"Erro ao gerar relatório TXT: {e}")
        return None

# --- Função para Gerar Relatório CSV ---
def gerar_relatorio_csv(rows, columns, output_widget):
    if not os.path.exists(DIRETORIO_RELATORIOS):
        os.makedirs(DIRETORIO_RELATORIOS)

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    nome_arquivo_csv = f"alerta_pobreza_relatorio_{timestamp}.csv"
    caminho_arquivo_csv = os.path.join(DIRETORIO_RELATORIOS, nome_arquivo_csv)

    try:
        processed_rows = [list(row) for row in rows] if rows else [] 
        df = pd.DataFrame(processed_rows, columns=columns)
        df.to_csv(caminho_arquivo_csv, index=False, encoding='utf-8', sep=';')
        output_widget.insert(tk.END, f"Relatório CSV '{nome_arquivo_csv}' gerado com sucesso em '{DIRETORIO_RELATORIOS}'.\n")
        logging.info(f"Relatório CSV gerado: {caminho_arquivo_csv}")
        return caminho_arquivo_csv
    except Exception as e:
        output_widget.insert(tk.END, f"Erro ao gerar relatório CSV: {e}\n")
        logging.error(f"Erro ao gerar relatório CSV: {e}")
        return None

# --- Nova Função para obter a saudação baseada na hora do dia ---
def get_time_of_day_greeting():
    current_hour = datetime.datetime.now().hour
    if current_hour < 12:
        return "Bom dia"
    else:
        return "Boa tarde"

# --- Função para Enviar E-mail (usando smtplib) ---
def enviar_email(anexos, conteudo_tabelado_para_email, output_widget): # Renomeei a variável para clareza
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_REMETENTE
        msg['To'] = EMAIL_DESTINATARIO
        msg['Subject'] = "Alerta Pobreza - Notas com Erro 815" # Assunto direto

        # Adiciona a saudação baseada na hora do dia e combina com o corpo fixo e o conteúdo tabelado
        saudacao = get_time_of_day_greeting()
        corpo_final_email = f"{saudacao},\n\n" + CORPO_EMAIL_FIXO + conteudo_tabelado_para_email + "\nAtenciosamente,\nSistema de Monitoramento"
        msg.attach(MIMEText(corpo_final_email, 'plain'))

        # Anexa os arquivos
        for arquivo_path in anexos:
            if os.path.exists(arquivo_path):
                with open(arquivo_path, "rb") as attachment:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(attachment.read())
                encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition",
                    f"attachment; filename={os.path.basename(arquivo_path)}",
                )
                msg.attach(part)
                output_widget.insert(tk.END, f"Arquivo '{os.path.basename(arquivo_path)}' anexado ao e-mail.\n")
            else:
                output_widget.insert(tk.END, f"Aviso: Arquivo '{os.path.basename(arquivo_path)}' não encontrado para anexar.\n")
                logging.warning(f"Arquivo não encontrado para anexar: {arquivo_path}")

        # Conecta e envia o email
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls() # Inicia a criptografia TLS
            server.login(EMAIL_REMETENTE, SENHA_APLICATIVO_GMAIL) # Use a senha de aplicativo aqui
            server.send_message(msg)

        output_widget.insert(tk.END, f"Email com relatório(s) enviado para '{EMAIL_DESTINATARIO}'.\n")
        logging.info(f"Email enviado com anexo(s): {anexos}")
        return True
    except smtplib.SMTPAuthenticationError as auth_e:
        output_widget.insert(tk.END, f"Erro de autenticação SMTP: Verifique remetente e senha de aplicativo. {auth_e}\n")
        logging.error(f"Erro de autenticação SMTP: {auth_e}")
        messagebox.showerror("Erro de Email", f"Erro de autenticação: {auth_e}. Verifique seu email remetente e a senha de aplicativo.")
        return False
    except Exception as e:
        output_widget.insert(tk.END, f"Erro ao enviar email: {e}\n")
        logging.error(f"Erro ao enviar email: {e}")
        messagebox.showerror("Erro de Email", f"Não foi possível enviar o email. Verifique suas credenciais e conexão: {e}")
        return False

# --- Função para verificar se o horário atual está dentro do horário comercial ---
def is_within_working_hours():
    now = datetime.datetime.now()
    is_weekday = 0 <= now.weekday() <= 4 # Segunda-feira (0) a Sexta-feira (4)
    is_working_hour = 8 <= now.hour < 18 # Das 8h às 18h
    return is_weekday and is_working_hour

# --- Função Principal - Executa Consulta e Atualiza a GUI ---
def executar_consulta_gui(output_widget, status_label, contador_label, progress_bar_fill, root):
    global consulta_agendada_id, contador_agendado_id, executando_consultas

    if not executando_consultas:
        return

    # Verifica se está dentro do horário comercial antes de executar a consulta
    if not is_within_working_hours():
        msg = f"[{time.strftime('%H:%M:%S')}] Fora do horário comercial (Seg-Sex, 08h-18h). A consulta não será executada.\n"
        output_widget.insert(tk.END, msg)
        logging.info(msg.strip())
        status_label.config(text="Status: Fora do horário comercial. Aguardando...")
        
        # Reagenda para o próximo intervalo, mesmo que não esteja executando consultas
        root.after(INTERVALO_CONSULTA_MS, lambda: executar_consulta_gui(
            output_widget, status_label, contador_label, progress_bar_fill, root
        ))
        # Inicia a atualização do contador para o próximo intervalo
        root.after(INTERVALO_ATUALIZACAO_MS, lambda: atualizar_contador_e_barra(
            contador_label, status_label, progress_bar_fill, root, INTERVALO_CONSULTA_MS
        ))
        return

    output_widget.delete(1.0, tk.END)
    status_label.config(text="Status: Iniciando consulta...")
    
    progress_bar_fill['value'] = 0
    progress_bar_fill.stop()
    
    contador_label.config(text="Próximo em: --:--")

    # Esta variável agora irá conter apenas o conteúdo tabelado para o e-mail
    conteudo_tabelado_para_email = "" 

    try:
        conn = conectdb()
        if conn is None:
            messagebox.showerror("Erro de Conexão", "Falha ao conectar ao banco de dados.")
            output_widget.insert(tk.END, 'Falha ao conectar ao banco de dados.')
            status_label.config(text="Status: Conexão falhou.")
            return

        cursor = conn.cursor()
        
        # Mantém a mensagem de início da consulta no console/log
        inicio_consulta_msg = f'[{time.strftime("%H:%M:%S")}] Consulta Alerta Pobreza iniciada...\n'
        output_widget.insert(tk.END, inicio_consulta_msg)
        logging.info(inicio_consulta_msg.strip())
        
        status_label.config(text="Status: Executando consulta...")

        t0 = time.time()
        query = """
                    SELECT IDFEMP,DATEMS,NOTFIC,CODFIC,STAPRE
                    FROM CONOTD0M
                    WHERE 1=1
                      AND SUBSTR(DATEMS, 1, 6) = TO_CHAR(CURRENT DATE, 'YYYYMM')
                      AND STAPRE = '815'
                """

        cursor.execute(query)

        columns = [column[0] for column in cursor.description]
        rows = cursor.fetchall()

        query_time = time.time() - t0
        
        # Mantém a mensagem de tempo e linhas no console/log
        tempo_linhas_msg = f"Consulta executada em {query_time:.2f} segundos.\nTotal de linhas retornadas: {len(rows)}\n"
        output_widget.insert(tk.END, tempo_linhas_msg)
        logging.info(tempo_linhas_msg.strip())

        output_widget.insert(tk.END, "\n--- Resultados da Consulta ---\n")
        
        if rows:
            header_line = " | ".join(columns) + "\n"
            separator_line = "-" * (sum(len(c) for c in columns) + (len(columns) - 1) * 3) + "\n"
            
            output_widget.insert(tk.END, header_line)
            output_widget.insert(tk.END, separator_line)
            
            # Adiciona cabeçalho e separador ao conteúdo do e-mail
            conteudo_tabelado_para_email += header_line
            conteudo_tabelado_para_email += separator_line
            
            for row in rows:
                row_line = " | ".join(map(str, row)) + "\n"
                output_widget.insert(tk.END, row_line)
                # Adiciona cada linha de resultado ao conteúdo do e-mail
                conteudo_tabelado_para_email += row_line
            
            output_widget.insert(tk.END, "\nResultados encontrados. Gerando e enviando relatório(s)...\n")
            
            lista_anexos = []
            
            # Gera o relatório CSV (mantido do seu código original)
            caminho_relatorio_csv = gerar_relatorio_csv(rows, columns, output_widget)
            if caminho_relatorio_csv:
                lista_anexos.append(caminho_relatorio_csv)

            if lista_anexos:
                # Envia o e-mail com o conteúdo tabelado
                enviar_email(lista_anexos, conteudo_tabelado_para_email, output_widget)
            else:
                output_widget.insert(tk.END, "Nenhum arquivo de relatório foi gerado para envio.\n")
                logging.warning("Nenhum arquivo de relatório foi gerado para envio por email.")

        else: # Se não houver rows
            nenhum_resultado_msg = "Nenhum resultado encontrado para a consulta.\n"
            output_widget.insert(tk.END, nenhum_resultado_msg)
            logging.info("Nenhum resultado encontrado. Nenhum relatório será gerado/enviado.")
            # Se não houver resultados, o corpo do e-mail pode ser simplesmente uma mensagem de "nenhum resultado"
            conteudo_tabelado_para_email = "Nenhum resultado com o erro 815 foi encontrado na consulta atual.\n"
            enviar_email([], conteudo_tabelado_para_email, output_widget) # Envia email mesmo sem anexos se não houver erro

        cursor.close()
        conn.close()
        logging.info("Conexão com o banco de dados fechada.")
        status_label.config(text=f"Status: Consulta finalizada às {time.strftime('%H:%M:%S')}. {len(rows)} linhas encontradas.")

    except Exception as e:
        logging.error(f"Erro inesperado durante a consulta: {e}")
        messagebox.showerror("Erro de Consulta", f"Ocorreu um erro: {e}")
        error_msg = f"\n[{time.strftime('%H:%M:%S')}] Ocorreu um erro: {e}\n"
        output_widget.insert(tk.END, error_msg)
        # Adiciona a mensagem de erro ao corpo do e-mail, se ocorrer um erro na consulta
        conteudo_tabelado_para_email = f"Ocorreu um erro durante a consulta: {e}\nPor favor, verifique o log para mais detalhes."
        enviar_email([], conteudo_tabelado_para_email, output_widget) # Envia email com erro mesmo sem anexos
        status_label.config(text="Status: Erro na consulta.")
    finally:
        if executando_consultas: # Reagenda apenas se o monitoramento estiver ativo
            progress_bar_fill['value'] = 0
            root.after(INTERVALO_ATUALIZACAO_MS, lambda: atualizar_contador_e_barra(
                contador_label, status_label, progress_bar_fill, root, INTERVALO_CONSULTA_MS
            ))
            consulta_agendada_id = root.after(INTERVALO_CONSULTA_MS, lambda: executar_consulta_gui(
                output_widget, status_label, contador_label, progress_bar_fill, root
            ))

# --- Função para Atualizar Contador de Tempo e Barra de Progresso ---
def atualizar_contador_e_barra(contador_label, status_label, progress_bar_fill, root, tempo_restante_ms):
    global contador_agendado_id, executando_consultas

    if not executando_consultas:
        return

    tempo_restante_ms -= INTERVALO_ATUALIZACAO_MS

    minutos = int(tempo_restante_ms / 1000 / 60)
    segundos = int((tempo_restante_ms / 1000) % 60)

    # Calcula o valor da barra de progresso (de 0 a 100)
    progress_value = ((INTERVALO_CONSULTA_MS - tempo_restante_ms) / INTERVALO_CONSULTA_MS) * 100
    progress_bar_fill['value'] = progress_value

    if tempo_restante_ms > 0:
        contador_label.config(text=f"Próximo em: {minutos:02d}:{segundos:02d}")
        contador_agendado_id = root.after(INTERVALO_ATUALIZACAO_MS, lambda: atualizar_contador_e_barra(
            contador_label, status_label, progress_bar_fill, root, tempo_restante_ms
        ))
    else:
        contador_label.config(text="Próximo em: 00:00")
        status_label.config(text="Status: Preparando nova consulta...")

# --- Funções de Controle para Iniciar/Parar ---
def iniciar_consultas(output_widget, status_label, contador_label, progress_bar_fill, root, btn_alternar):
    global executando_consultas
    if executando_consultas:
        return

    executando_consultas = True
    btn_alternar.config(text="Parar Monitoramento")
    status_label.config(text="Status: Monitoramento Iniciado. Agendando primeira consulta...")
    output_widget.insert(tk.END, f'\n[{time.strftime("%H:%M:%S")}] Monitoramento Iniciado.\n')
    
    # Inicia a primeira execução e o contador
    executar_consulta_gui(output_widget, status_label, contador_label, progress_bar_fill, root)

def parar_consultas(root, btn_alternar, status_label, contador_label, progress_bar_fill, output_widget):
    global consulta_agendada_id, contador_agendado_id, executando_consultas

    if not executando_consultas:
        return

    executando_consultas = False
    btn_alternar.config(text="Iniciar Monitoramento")
    status_label.config(text="Status: Monitoramento Parado.")
    output_widget.insert(tk.END, f'\n[{time.strftime("%H:%M:%S")}] Monitoramento Parado.\n')

    # Cancela agendamentos pendentes
    if consulta_agendada_id:
        root.after_cancel(consulta_agendada_id)
        consulta_agendada_id = None
    if contador_agendado_id:
        root.after_cancel(contador_agendado_id)
        contador_agendado_id = None
    
    contador_label.config(text="Parado")
    progress_bar_fill['value'] = 0
    progress_bar_fill.stop()

def alternar_monitoramento(output_widget, status_label, contador_label, progress_bar_fill, root, btn_alternar):
    global executando_consultas
    if executando_consultas:
        parar_consultas(root, btn_alternar, status_label, contador_label, progress_bar_fill, output_widget)
    else:
        iniciar_consultas(output_widget, status_label, contador_label, progress_bar_fill, root, btn_alternar)

# --- Função de Configuração da GUI ---
def setup_gui():
    root = ThemedTk(theme="black") # Mantém ThemedTk
    root.title("Monitoramento Alerta Pobreza")
    root.geometry("900x700")

    fonte_padrao = ("Arial", 11)
    fonte_contador = ("Consolas", 18, "bold")
    fonte_resultado = ("Consolas", 10)

    style = ttk.Style()
    style.configure(".", font=fonte_padrao)
    style.configure("TButton", padding=6)
    style.map("TButton",
              foreground=[('pressed', 'white'), ('active', 'lightblue')],
              background=[('pressed', '!disabled', 'gray'), ('active', '#444444')])

    style.configure("Horizontal.TProgressbar", background='lime green', troughcolor='darkgray', bordercolor='black')

    control_frame = ttk.Frame(root, padding="10 10 10 10")
    control_frame.pack(side=tk.TOP, fill=tk.X)

    # Botão para alternar monitoramento (Iniciar/Parar)
    btn_alternar = ttk.Button(control_frame, text="Iniciar Monitoramento",
                              command=lambda: alternar_monitoramento(resultado_text, status_label, contador_label, progress_bar_fill, root, btn_alternar))
    btn_alternar.pack(side=tk.LEFT, padx=5)

    progress_bar_fill = ttk.Progressbar(control_frame, orient="horizontal", length=300, mode="determinate", style="Horizontal.TProgressbar")
    progress_bar_fill.pack(side=tk.LEFT, padx=5)

    contador_label = ttk.Label(control_frame, text="Próximo em: --:--", font=fonte_contador, foreground="lime green")
    contador_label.pack(side=tk.LEFT, padx=(20, 5))

    resultado_text = scrolledtext.ScrolledText(root, wrap=tk.WORD, width=100, height=30,
                                               font=fonte_resultado,
                                               bg="#333333",
                                               fg="#FFFFFF",
                                               insertbackground="white",
                                               selectbackground="#444444")
    resultado_text.pack(padx=10, pady=5, fill=tk.BOTH, expand=True)

    status_label = ttk.Label(root, text="Status: Monitoramento Iniciado Automaticamente.", anchor=tk.W,
                             relief=tk.SUNKEN,
                             padding=(5, 2),
                             background="#222222",
                             foreground="lightgray")
    status_label.pack(side=tk.BOTTOM, fill=tk.X)

    # --- Chamada para iniciar automaticamente ---
    # Inicia o monitoramento logo após a GUI ser configurada
    root.after(100, lambda: iniciar_consultas(resultado_text, status_label, contador_label, progress_bar_fill, root, btn_alternar))
    
    root.mainloop()

# --- Bloco Principal - Inicia a GUI ---
if __name__ == "__main__":
    setup_gui()
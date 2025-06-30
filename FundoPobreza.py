import pyodbc
import logging
import time
import sys
import tkinter as tk
from tkinter import scrolledtext, messagebox, ttk
import pandas as pd 
import os
import smtplib      
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders


INTERVALO_CONSULTA_MS = 1 * 60 * 1000 

INTERVALO_CONTADOR_MS = 1000

# Configuração de log
logging.basicConfig(
    filename='log_execucao_gui.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


EMAIL_REMETENTE = 'rodriguestefany98@gmail.com' 
SENHA_REMETENTE = 'wqlf ylft acow dmsa'             
EMAIL_DESTINATARIO = 'felipe.amaral@nagem.com.br' 
SMTP_SERVER = 'smtp.example.com'         
SMTP_PORT = 587                           


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


def enviar_email_alerta(conteudo, csv_filename=None):
    try:
        print("Preparando e-mail...")
        msg = MIMEMultipart()
        msg['From'] = EMAIL_REMETENTE
        msg['To'] = EMAIL_DESTINATARIO
        msg['Subject'] = 'Alerta! ERRO 815'

        corpo = f"\n\n\n\n Bom dia! 🍵  \n{conteudo}\n  UPDATE acima pronto para reprocessar. \n Atenciosamente,\n\n 🤖 Automação wRodaCupom."
        msg.attach(MIMEText(corpo, 'plain'))

        # Anexa o arquivo, se fornecido e existir
        if csv_filename and os.path.exists(csv_filename):
            with open(csv_filename, "rb") as attachment:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(attachment.read())
            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                f"attachment; filename={os.path.basename(csv_filename)}",
            )
            msg.attach(part)
            print(f"Arquivo {csv_filename} anexado ao e-mail.")

        print("Conectando ao servidor SMTP...")
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            print("Logando no servidor SMTP...")
            server.login(EMAIL_REMETENTE, SENHA_REMETENTE)
            print("Enviando e-mail...")
            server.send_message(msg)
        print("E-mail enviado com sucesso.")
    except Exception as e:
        print(f"Erro ao enviar e-mail: {e}")
        logging.error(f"Erro ao enviar e-mail: {e}")


def executar_consulta_gui(output_widget, status_label, contador_label, progress_bar_query, root):
    output_widget.delete(1.0, tk.END)
    status_label.config(text="Status: Iniciando consulta...")
    progress_bar_query.start() # Inicia a animação da barra de progresso da query
    contador_label.config(text="Próxima em: --:--") # Limpa o contador enquanto a consulta roda

    try:
        conn = conectdb()
        if conn is None:
            messagebox.showerror("Erro de Conexão", "Falha ao conectar com o banco de dados.")
            output_widget.insert(tk.END, 'Falha na conexão com o banco.')
            status_label.config(text="Status: Conexão falhou.")
            progress_bar_query.stop()
            return
            
        cursor = conn.cursor() 
        output_widget.insert(tk.END, f'[{time.strftime("%H:%M:%S")}] Consulta de Alerta Pobreza iniciada...\n') 
        status_label.config(text="Status: Executando query...")
        
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
        output_widget.insert(tk.END, f"Query executada em {query_time:.2f} segundos.\n")
        output_widget.insert(tk.END, f"Total de linhas retornadas: {len(rows)}\n")

        output_widget.insert(tk.END, "\n--- Resultados da Query ---\n")
        if rows:
            output_widget.insert(tk.END, " | ".join(columns) + "\n")
            output_widget.insert(tk.END, "-" * (sum(len(c) for c in columns) + (len(columns) - 1) * 3) + "\n") 
            
            for row in rows:
                output_widget.insert(tk.END, " | ".join(map(str, row)) + "\n")
            
            # --- Lógica para gerar Excel e enviar e-mail ---
            if len(rows) > 0: # Envia e-mail apenas se houver resultados
                df = pd.DataFrame(rows, columns=columns)
                excel_filename = f"Alerta_Pobreza_{time.strftime('%Y%m%d_%H%M%S')}.xlsx"
                
                try:
                    df.to_excel(excel_filename, index=False)
                    logging.info(f"Arquivo Excel '{excel_filename}' gerado com sucesso.")

                    assunto_email = "Alerta de Pobreza: Novos Registros Encontrados!"
                    corpo_email = (
                        f"Prezado(a),\n\n"
                        f"Este é um alerta automático do sistema de monitoramento de pobreza.\n"
                        f"Foram encontrados {len(rows)} novos registros que correspondem aos critérios de alerta.\n\n"
                        f"Detalhes dos registros estão anexados neste e-mail no arquivo '{excel_filename}'.\n\n"
                        f"Data e Hora da Consulta: {time.strftime('%d/%m/%Y %H:%M:%S')}\n\n"
                        f"Atenciosamente,\n"
                        f"Seu Sistema de Monitoramento"
                    )

                    if enviar_email_alerta(EMAIL_DESTINATARIO, assunto_email, corpo_email, excel_filename):
                        output_widget.insert(tk.END, f"\nAlerta de e-mail enviado com o arquivo '{excel_filename}'.\n")
                    else:
                        output_widget.insert(tk.END, "\nFalha ao enviar e-mail de alerta.\n")

                except Exception as e_excel_email:
                    logging.error(f"Erro ao gerar Excel ou enviar e-mail: {e_excel_email}")
                    output_widget.insert(tk.END, f"\nErro ao processar Excel/E-mail: {e_excel_email}\n")

        else:
            output_widget.insert(tk.END, "Nenhum resultado encontrado para a query.\n")
            logging.info("Nenhum registro encontrado para alerta de pobreza.")


        cursor.close()
        conn.close()
        logging.info("Conexão com o banco fechada.")
        status_label.config(text=f"Status: Consulta finalizada às {time.strftime('%H:%M:%S')}. {len(rows)} linhas encontradas.")

    except Exception as e: 
        logging.error(f"Erro inesperado durante a consulta: {e}")
        messagebox.showerror("Erro na Consulta", f"Ocorreu um erro: {e}")
        output_widget.insert(tk.END, f"\n[{time.strftime('%H:%M:%S')}] Ocorreu um erro: {e}\n")
        status_label.config(text="Status: Erro na consulta.")
    finally:
        progress_bar_query.stop() 
        progress_bar_query['value'] = 0 

   
    root.after(INTERVALO_CONTADOR_MS, lambda: atualizar_contador_tempo(
        contador_label, status_label, root, INTERVALO_CONSULTA_MS
    ))
    
    root.after(INTERVALO_CONSULTA_MS, lambda: executar_consulta_gui(
        output_widget, status_label, contador_label, progress_bar_query, root
    ))


def atualizar_contador_tempo(contador_label, status_label, root, tempo_restante_ms):
    tempo_restante_ms -= INTERVALO_CONTADOR_MS
    
    
    minutos = int(tempo_restante_ms / 1000 / 60)
    segundos = int((tempo_restante_ms / 1000) % 60)

    if tempo_restante_ms > 0:
        contador_label.config(text=f"Próxima em: {minutos:02d}:{segundos:02d}")
       
        root.after(INTERVALO_CONTADOR_MS, lambda: atualizar_contador_tempo(
            contador_label, status_label, root, tempo_restante_ms
        ))
    else:
        contador_label.config(text="Próxima em: 00:00")
        status_label.config(text="Status: Preparando nova consulta...")
       

def setup_gui():
    root = tk.Tk()
    root.title("Monitoramento de Alerta Pobreza")
    root.geometry("900x700") 

    
    control_frame = tk.Frame(root, padx=10, pady=10)
    control_frame.pack(side=tk.TOP, fill=tk.X)

    
    btn_buscar = tk.Button(control_frame, text="Forçar Consulta Agora", 
                            command=lambda: executar_consulta_gui(resultado_text, status_label, contador_label, progress_bar_query, root))
    btn_buscar.pack(side=tk.LEFT, padx=5)

    
    progress_bar_query = ttk.Progressbar(control_frame, orient="horizontal", length=150, mode="indeterminate")
    progress_bar_query.pack(side=tk.LEFT, padx = 5)
    
    
    contador_label = tk.Label(control_frame, text="Próxima em: --:--", font=("Arial", 14, "bold"), fg="darkgreen")
    contador_label.pack(side=tk.LEFT, padx=(20, 5))

    
    resultado_text = scrolledtext.ScrolledText(root, wrap=tk.WORD, width = 100, height = 30, font = ("Consolas", 10))
    resultado_text.pack(padx=10, pady=5, fill=tk.BOTH, expand=True)

    
    status_label = tk.Label(root, text="Status: Aguardando consulta inicial...", bd=1, relief=tk.SUNKEN, anchor = tk.W)
    status_label.pack(side=tk.BOTTOM, fill=tk.X)

    
    root.update_idletasks() 
    
    
    root.after(100, lambda: executar_consulta_gui(resultado_text, status_label, contador_label, progress_bar_query, root))
    
    root.mainloop()


if __name__ == "__main__":
    setup_gui()
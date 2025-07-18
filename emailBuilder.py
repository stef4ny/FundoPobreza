import datetime
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import os
import logging


app_logger = logging.getLogger(__name__)

def htmlEmailBody(total_rows, query_time, rows_data, columns_header):
    html_style = """
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f4f4f4; color: #333; }
        .container { max-width: 800px; margin: 0 auto; background-color: #ffffff; padding: 20px; border-radius: 8px; box-shadow: 0 0 10px rgba(0, 0, 0, 0.1); }
        h2 { color: #333; }
        p { line-height: 1.6; }
        .header { background-color: #4CAF50; color: white; padding: 10px 20px; text-align: center; border-radius: 8px 8px 0 0; }
        .data-table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        .data-table th, .data-table td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        .data-table th { background-color: #f2f2f2; color: #555; }
        .data-table tr:nth-child(even) { background-color: #f9f9f9; }
        .data-table tr:hover { background-color: #f1f1f1; }
        .footer { margin-top: 30px; font-size: 0.9em; color: #777; text-align: center; }
        .highlight { color: #007bff; font-weight: bold; }
    </style>
    """

    
    table_header_html = "<tr>"
    for col in columns_header:
        table_header_html += f"<th>{col}</th>"
    table_header_html += "</tr>"

    
    table_rows_html = ""
    for row in rows_data:
        table_rows_html += "<tr>"
        for item in row:
           
            formatted_item = str(item) if item is not None else "N/A"
            table_rows_html += f"<td>{formatted_item}</td>"
        table_rows_html += "</tr>"

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Relatório de Monitoramento</title>
        {html_style}
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Relatório de Monitoramento</h1>
            </div>
            <p>Prezado(a) usuário(a),</p>
            <p>Este é um relatório automático do sistema de monitoramento.</p>
            <p>
                A última consulta encontrou <span class="highlight">{total_rows}</span> linhas de dados
                e levou <span class="highlight">{query_time:.2f} segundos</span> para ser executada.
            </p>
            <p>Detalhes da consulta:</p>
            <table class="data-table">
                <thead>
                    {table_header_html}
                </thead>
                <tbody>
                    {table_rows_html}
                </tbody>
            </table>
            <div class="footer">
                <p>Este e-mail foi gerado automaticamente. Por favor, não responda.</p>
                <p>&copy; {datetime.datetime.now().year} Seu Sistema de Monitoramento</p>
            </div>
        </div>
    </body>
    </html>
    """
    return html_content

def send_email(anexos, df_data_for_email, total_rows_found, email_remetente, senha_aplicativo, email_destinatario, assunto_email, saudacao="Olá"):
    """
    Envia um e-mail com o relatório em HTML e anexos opcionais.
    
    Args:
        anexos (list): Lista de caminhos para arquivos a serem anexados.
        df_data_for_email (pd.DataFrame): DataFrame com os dados para o corpo do e-mail.
        total_rows_found (int): Número total de linhas encontradas na consulta.
        email_remetente (str): Endereço de e-mail do remetente.
        senha_aplicativo (str): Senha de aplicativo para autenticação SMTP.
        email_destinatario (str): Endereço(s) de e-mail do(s) destinatário(s), separados por vírgula.
        assunto_email (str): Assunto do e-mail.
        saudacao (str): Saudação personalizada para o e-mail.
    
    Returns:
        bool: True se o e-mail foi enviado com sucesso, False caso contrário.
    """
    email_sent_successfully = False
    try:
        msg = MIMEMultipart()
        msg['From'] = email_remetente
        
        destinatarios_list = [d.strip() for d in email_destinatario.split(',') if d.strip()]
        msg['To'] = ", ".join(destinatarios_list)
        msg['Subject'] = assunto_email

       
        html_body = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; text-align: center; color: #333; }}
                .container {{
                    max-width: 800px;
                    margin: 0 auto;
                    padding: 20px;
                    border: 1px solid #eee;
                    border-radius: 8px;
                    background-color: #fff;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}
                h2 {{ color: #0056b3; margin-bottom: 20px; }}
                p {{ line-height: 1.6; margin-bottom: 10px; text-align: center;}}
                .report-section {{ margin-top: 20px; }}
                table {{
                    width: 95%;
                    margin: 20px auto;
                    border-collapse: collapse;
                    border: 1px solid #ddd;
                }}
                th, td {{
                    border: 1px solid #ddd;
                    padding: 10px;
                    text-align: center;
                }}
                th {{
                    background-color: #e6f2ff;
                    color: #333;
                    font-weight: bold;
                }}
                tr:nth-child(even) {{ background-color: #f9f9f9; }}
                .footer {{ margin-top: 30px; font-size: 0.9em; color: #666; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h2>{assunto_email}</h2>
                <p>{saudacao},</p>
                <p>Este é um relatório automático do sistema de monitoramento de Alerta Pobreza.
Na última consulta, foram encontrados os seguintes resultados:</p>
        """
       
        from config import EMAIL_MAX_ROWS_DISPLAY
        df_display_for_email = df_data_for_email.head(EMAIL_MAX_ROWS_DISPLAY) if EMAIL_MAX_ROWS_DISPLAY > 0 else df_data_for_email

        if total_rows_found > 0 and not df_display_for_email.empty:
            html_body += f"""
                <div class="report-section">
                    <h3>Resultados da Consulta ({total_rows_found} linhas encontradas):</h3>
                    <p><i>Exibindo as primeiras {len(df_display_for_email)} linhas no corpo do email. O relatório completo está no anexo.</i></p>
                    {df_display_for_email.to_html(index=False)}
                </div>
            """
        else:
            html_body += """
                <div class="report-section">
                    <h3>Nenhum resultado com o status '815' foi encontrado na consulta atual.</h3>
                    <p>O monitoramento está ativo e continuará verificando em intervalos regulares.</p>
                </div>
            """

        html_body += """
                <p class="footer">Atenciosamente,<br>Sistema de Monitoramento</p>
            </div>
        </body>
        </html>
        """
        msg.attach(MIMEText(html_body, 'html'))

       
        if anexos:
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
                    app_logger.info(f"Arquivo '{os.path.basename(arquivo_path)}' anexado ao e-mail.")
                else:
                    app_logger.warning(f"Arquivo '{os.path.basename(arquivo_path)}' não encontrado para anexar.")
        else:
            app_logger.info("Nenhum anexo CSV para enviar no e-mail.")

        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(email_remetente, senha_aplicativo)
            server.send_message(msg, from_addr=email_remetente, to_addrs=destinatarios_list)

        app_logger.info(f"Email com relatório(s) enviado para '{email_destinatario}'.")
        email_sent_successfully = True
        return True
    except smtplib.SMTPAuthenticationError as auth_e:
        app_logger.error(f"Erro de autenticação SMTP: Verifique remetente e senha de aplicativo. {auth_e}", exc_info=True)
        return False
    except Exception as e:
        app_logger.error(f"Erro ao enviar email: {e}", exc_info=True)
        return False
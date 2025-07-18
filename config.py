# --- CONFIGURAÇÕES DE E-MAIL ---
EMAIL_REMETENTE = 'rodriguestefany98@gmail.com'
SENHA_APPLICATIVO_GMAIL = 'wqlf ylft acow dmsa' 
EMAIL_DESTINATARIO = 'stefany.rodrigues@nagem.com.br, desenvolvimentosuporte@nagem.com.br'   #  augusto.mendes@nagem.com.br, wedici.lins@nagem.com.br, felipe.amaral@nagem.com.br'
ASSUNTO_EMAIL = "Alerta Pobreza - Notas com Erro 815"
CORPO_EMAIL_FIXO = """
Prezado(a),

Este é um relatório automático do sistema de monitoramento de Alerta Pobreza.
Na última consulta, foram encontrados os seguintes resultados:

"""

#query

SQL_QUERY_ALERTA = """
SELECT
    IDFEMP AS LOJA,
    FNGCHARTODATE(DATEMS) AS DATA,
    NOTFIC AS "NOTA FISCAL",
    CODFIC AS " CODIGO FISCAL",
    STAPRE AS "STATUS PROCESSAMENTO",
    CASE IDFCLIFNC
        WHEN 'C' THEN 'Cliente'
        WHEN 'B' THEN 'B2C'
        WHEN 'F' THEN 'Fornecedor'
        WHEN 'T' THEN 'Transportadora'
    END AS TIPO,
    CASE TPOEMSNFE
        WHEN 1 THEN 'Normal'
        WHEN 2 THEN 'SCAN'
        WHEN 3 THEN 'DPEC'
        WHEN 4 THEN 'FS'
        WHEN 5 THEN 'FS-DA'
    END AS EMISSAO
FROM CONOTD0M
WHERE
    DATEMS >= TO_CHAR(CURRENT DATE, 'YYYYMM') || '01'
    AND DATEMS <= TO_CHAR(LAST_DAY(CURRENT DATE), 'YYYYMMDD')
    AND STAPRE = '815'
"""


# --- CONFIGURAÇÕES DE BANCO DE DADOS ---
DB_DRIVER = '{Client Access ODBC Driver (32-bit)}'
DB_SYSTEM = '10.1.0.2'
DB_UID = 'CLAUDIO'
DB_PWD = '19957'
DB_DEFAULT_LIBRARIES = 'NAG0001'

# --- CONFIGURAÇÕES GERAIS ---
DIRETORIO_RELATORIOS = 'relatorios' 
DIRETORIO_LOGS = 'logs'
INTERVALO_CONSULTA_MS = 60 * 60 * 1000 
INTERVALO_ATUALIZACAO_MS = 1000 


EMAIL_MAX_ROWS_DISPLAY = 10 

WORKING_HOURS_START_HOUR = 8  
WORKING_HOURS_END_HOUR = 18
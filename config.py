# --- CONFIGURAÇÕES DE E-MAIL ---
EMAIL_REMETENTE = '******@gmail.com'
SENHA_APPLICATIVO_GMAIL = '**** **** **** ****' 
EMAIL_DESTINATARIO = '*********@gmail.com.br
ASSUNTO_EMAIL = "Alerta Pobreza - Notas com Erro 815"
CORPO_EMAIL_FIXO = """
Prezado(a),

Este é um relatório automático do sistema de monitoramento de Alerta Pobreza.
Na última consulta, foram encontrados os seguintes resultados:

"""

#query

-- Exemplo de query SQL para consulta de documentos fiscais com status específico
-- Essa query é fictícia e serve apenas para fins demonstrativos

SQL_QUERY_EXEMPLO = """
SELECT
    ID_EMPRESA AS LOJA,
    CONVERTE_DATA(DT_EMISSAO) AS DATA,
    NUM_DOCUMENTO AS "NOTA FISCAL",
    COD_DOCUMENTO AS "CÓDIGO FISCAL",
    STATUS_PROC AS "STATUS PROCESSAMENTO",
    CASE TIPO_PESSOA
        WHEN 'C' THEN 'Cliente'
        WHEN 'B' THEN 'B2C'
        WHEN 'F' THEN 'Fornecedor'
        WHEN 'T' THEN 'Transportadora'
    END AS TIPO,
    CASE TIPO_EMISSAO
        WHEN 1 THEN 'Normal'
        WHEN 2 THEN 'SCAN'
        WHEN 3 THEN 'DPEC'
        WHEN 4 THEN 'FS'
        WHEN 5 THEN 'FS-DA'
    END AS EMISSAO
FROM TABELA_DOCUMENTOS
WHERE
    DT_EMISSAO >= TO_CHAR(CURRENT_DATE, 'YYYYMM') || '01'
    AND DT_EMISSAO <= TO_CHAR(LAST_DAY(CURRENT_DATE), 'YYYYMMDD')
    AND STATUS_PROC = '815'
"""



# --- CONFIGURAÇÕES DE BANCO DE DADOS ---
DB_DRIVER = '{C**** Access *** ****** (32-bit)}'
DB_SYSTEM = 'localhost'
DB_UID = '******'
DB_PWD = '*****'
DB_DEFAULT_LIBRARIES = '******'

# --- CONFIGURAÇÕES GERAIS ---
DIRETORIO_RELATORIOS = 'relatorios' 
DIRETORIO_LOGS = 'logs'
INTERVALO_CONSULTA_MS = 60 * 60 * 1000 
INTERVALO_ATUALIZACAO_MS = 1000 


EMAIL_MAX_ROWS_DISPLAY = 10 

WORKING_HOURS_START_HOUR = 8  
WORKING_HOURS_END_HOUR = 18


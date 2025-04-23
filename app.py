import streamlit as st
import psycopg2
import pandas as pd
import plotly.express as px
from dotenv import load_dotenv
import os
from urllib.parse import urlparse

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# Obtém as credenciais do Supabase
USER = os.getenv("user")
PASSWORD = os.getenv("password")
HOST = os.getenv("host")
PORT = os.getenv("port")
DBNAME = os.getenv("dbname")

# Função de conexão com o banco de dados PostgreSQL do Supabase
def conexao_db():
    try:
        conn = psycopg2.connect(
            user=USER,
            password=PASSWORD,
            host=HOST,
            port=PORT,
            dbname=DBNAME
        )
        return conn, conn.cursor()
    except Exception as e:
        st.error(f"Falha ao conectar ao banco de dados: {e}")
        return None, None

# Função para fechar a conexão
def fechar_conexao(conn):
    if conn:
        conn.commit()
        conn.close()

# Configurações da página
st.set_page_config(page_title="Bullet Journal", page_icon="📝", layout="wide")
st.title("🧠 Bullet Journal Digital")

# Menu lateral
abas = ["Objetivos", "Resumo do Dia", "Atividades", "Desempenho", "Exportar"]
st.sidebar.title("📋 Menu")
aba_selecionada = st.sidebar.selectbox("Selecione uma aba", abas)

# ABA 1 - Objetivos
if aba_selecionada == "Objetivos":
    st.header("🎯 Registro de Objetivos")
    prazo = st.selectbox("Prazo", ["Curto", "Médio", "Longo"])
    objetivo = st.selectbox("Objetivo", ["Pessoal", "Profissional", "Outros"])
    atividade = st.text_input("Atividade")
    if st.button("Registrar Objetivo"):
        conn, cursor = conexao_db()
        if conn:
            cursor.execute("INSERT INTO objetivos (prazo, objetivo, atividade) VALUES (%s, %s, %s)", (prazo, objetivo, atividade))
            df_objetivos = pd.read_sql_query("SELECT * FROM objetivos", conn)
            st.success("Objetivo registrado com sucesso!")
            st.dataframe(df_objetivos)
            fechar_conexao(conn)

# ABA 2 - Resumo do Dia
if aba_selecionada == "Resumo do Dia":
    st.header("🗕️ Resumo Diário")
    data = st.date_input("Data")
    humor = st.slider("Humor", 0, 5, 3)
    col1, col2, col3 = st.columns(3)
    with col1: check_agua = st.checkbox("Água")
    with col2: check_academia = st.checkbox("Academia")
    with col3: check_leitura = st.checkbox("Leitura")

    if st.button("Registrar Resumo"):
        conn, cursor = conexao_db()
        if conn:
            cursor.execute("""
                INSERT INTO resumo_dia (data, humor, check_agua, check_academia, check_leitura)
                VALUES (%s, %s, %s, %s, %s)""", (data, humor, check_agua, check_academia, check_leitura))
            df = pd.read_sql_query("SELECT * FROM resumo_dia", conn)
            st.success("Resumo registrado com sucesso!")
            st.dataframe(df)
            fechar_conexao(conn)

# ABA 3 - Atividades
if aba_selecionada == "Atividades":
    tab1, tab2 = st.tabs(["📌 Cadastro", "📖 Visualização"])
    with tab1:
        st.subheader("Cadastro de Atividades")
        conn, cursor = conexao_db()
        if conn:
            data = st.date_input("Data", key="data_input")
            hora_inicio = st.time_input("Hora de Início").strftime("%H:%M")
            hora_fim = st.time_input("Hora de Fim").strftime("%H:%M")
            objetivos = pd.read_sql_query("SELECT DISTINCT atividade FROM objetivos", conn)
            objetivo = st.selectbox("Objetivo", objetivos['atividade'] if not objetivos.empty else ["Nenhum objetivo"])
            atividade = st.text_input("Atividade")
            descricao = st.text_input("Descrição")
            if st.button("Registrar Atividade"):
                cursor.execute("""
                    INSERT INTO atividades (data, hora_inicio, hora_fim, objetivo, atividade, descricao)
                    VALUES (%s, %s, %s, %s, %s, %s)""", (data, hora_inicio, hora_fim, objetivo, atividade, descricao))
                df = pd.read_sql_query("SELECT * FROM atividades", conn)
                st.success("Atividade registrada com sucesso!")
                st.dataframe(df)
                fechar_conexao(conn)
    with tab2:
        st.subheader("Visualização de Atividades")
        data_escolhida_input = st.date_input("Data", key="data_escolhida")
        
        conn, _ = conexao_db()
        if conn:
            # A consulta SQL filtra diretamente pelo campo 'data' (do tipo DATE)
            df = pd.read_sql_query("SELECT * FROM atividades WHERE data = %s", conn, params=[data_escolhida_input])
            st.dataframe(df)
            fechar_conexao(conn)

# ABA 4 - Desempenho
if aba_selecionada == "Desempenho":
    st.header("📊 Gráficos de Desempenho")
    conn, _ = conexao_db()
    if conn:
        resumo = pd.read_sql_query("SELECT * FROM resumo_dia", conn)
        atividades = pd.read_sql_query("SELECT * FROM atividades", conn)
        fechar_conexao(conn)

        if not resumo.empty and not atividades.empty:
            resumo['data'] = pd.to_datetime(resumo['data'])
            atividades['data'] = pd.to_datetime(atividades['data'])

            df_unificado = pd.merge(atividades, resumo, on="data", how="left")
            st.subheader("Atividades por dia")
            fig1 = px.histogram(df_unificado, x="data", color="objetivo", title="Distribuição de Atividades")
            st.plotly_chart(fig1)

            st.subheader("Humor ao longo do tempo")
            fig2 = px.line(resumo, x="data", y="humor", title="Variação do Humor Diário")
            st.plotly_chart(fig2)

# ABA 5 - Exportar
if aba_selecionada == "Exportar":
    st.header("📄 Exportar Dados para Excel")
    conn, _ = conexao_db()
    if conn:
        df1 = pd.read_sql_query("SELECT * FROM atividades", conn)
        df2 = pd.read_sql_query("SELECT * FROM resumo_dia", conn)
        fechar_conexao(conn)

        df_merge = pd.merge(df1, df2, on="data", how="left")

        excel = pd.ExcelWriter("export_bullet_journal.xlsx", engine="xlsxwriter")
        df1.to_excel(excel, sheet_name="Atividades", index=False)
        df2.to_excel(excel, sheet_name="Resumo_Dia", index=False)
        df_merge.to_excel(excel, sheet_name="Unificado", index=False)
        excel.close()

        with open("export_bullet_journal.xlsx", "rb") as f:
            st.download_button("👅 Baixar Excel", f, file_name="bullet_journal.xlsx")

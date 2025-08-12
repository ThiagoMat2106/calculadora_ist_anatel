import pandas as pd
from playwright.sync_api import sync_playwright
import streamlit as st

# --- PARTE 1: EXTRAÇÃO E TRATAMENTO DOS DADOS ---

@st.cache_data
def extrair_dados_ist_completo():
    """
    Extrai todos os dados do IST do site da Anatel usando Playwright.
    """
    url = "https://www.gov.br/anatel/pt-br/regulado/competicao/tarifas-e-precos/valores-do-ist"
    
    st.info("Buscando dados do IST na Anatel...")

    try:
        with sync_playwright() as p:
            # Lançamento do navegador em modo headless, sem abrir a janela
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url)

            # Clica em todos os botões de expandir para que todas as tabelas sejam visíveis
            expand_buttons = page.locator('button.panel-heading').all()
            for button in expand_buttons:
                button.click()
            
            # Espera até que todas as tabelas estejam visíveis na página
            page.wait_for_selector('table', state='visible')

            page_source = page.content()
            browser.close()
            
            lista_de_tabelas = pd.read_html(page_source, decimal=',', thousands='.', header=0)
            df_ist_completo = pd.concat(lista_de_tabelas, ignore_index=True)
            
            df_ist_completo.columns = ['PERÍODO', 'VARIAÇÃO', 'ÍNDICE']
            df_ist_completo = df_ist_completo.dropna(subset=['PERÍODO']).reset_index(drop=True)
            df_ist_completo['ÍNDICE'] = df_ist_completo['ÍNDICE'].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False).astype(float)
            
            st.success("Dados do IST extraídos e compilados com sucesso.")
            return df_ist_completo

    except Exception as e:
        st.error(f"Ocorreu um erro ao extrair os dados: {e}")
        return pd.DataFrame()

# --- INTERFACE COM STREAMLIT ---

st.set_page_config(layout="wide", page_title="Calculadora de Reajuste IST")

st.title("Calculadora de Reajuste IST")
st.write("Insira os dados abaixo para calcular o reajuste do valor com base no Índice de Serviços de Telecomunicações.")

df_ist = extrair_dados_ist_completo()

if not df_ist.empty:
    st.subheader("Últimos valores carregados:")
    st.dataframe(df_ist.tail(), use_container_width=True)

    periodos_disponiveis = df_ist['PERÍODO'].tolist()
    
    with st.form(key='calculadora_form'):
        col1, col2, col3 = st.columns(3)
        with col1:
            valor_original = st.number_input("Valor Original do Contrato", min_value=0.01, format="%.2f", value=150.00)
        with col2:
            data_inicial_str = st.selectbox("Mês/Ano Inicial para o Reajuste", options=periodos_disponiveis, index=periodos_disponiveis.index('Jan/06'))
        with col3:
            data_final_str = st.selectbox("Mês/Ano Final para o Reajuste", options=periodos_disponiveis, index=len(periodos_disponiveis) - 1)
        
        submit_button = st.form_submit_button("Calcular Reajuste")

    if submit_button:
        try:
            ist_inicial_row =

import pandas as pd
from playwright.sync_api import sync_playwright
import streamlit as st
import subprocess
import sys

# --- CONFIGURAÇÃO DE INSTALAÇÃO DO PLAYWRIGHT ---

def install_playwright_browsers():
    try:
        # Apenas executa se não houver um navegador instalado
        p = sync_playwright().start()
        p.chromium.launch().close()
    except:
        st.info("Instalando navegadores do Playwright. Por favor, aguarde...")
        subprocess.run([sys.executable, "-m", "playwright", "install"], check=True, capture_output=True)
        p = sync_playwright().start()
        p.chromium.launch().close()
    finally:
        p.stop()
        st.success("Navegadores do Playwright instalados com sucesso.")

install_playwright_browsers()

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
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url)

            expand_buttons = page.locator('button.panel-heading').all()
            for button in expand_buttons:
                button.click()
            
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
    st.subheader("Últimos 5 valores carregados:")
    st.dataframe(df_ist.tail(5), use_container_width=True)
    
    # Adiciona um expander para mostrar a tabela completa
    with st.expander("Clique para ver todos os dados históricos"):
        st.dataframe(df_ist, use_container_width=True)

    periodos_disponiveis = df_ist['PERÍODO'].tolist()
    
    with st.form(key='calculadora_form'):
        col1, col2, col3 = st.columns(3)
        with col1:
            valor_original = st.number_input("Valor Original do Contrato (R$)", min_value=0.01, format="%.2f", value=150.00)
        with col2:
            data_inicial_str = st.selectbox("Mês/Ano Inicial para o Reajuste", options=periodos_disponiveis, index=0)
        with col3:
            data_final_str = st.selectbox("Mês/Ano Final para o Reajuste", options=periodos_disponiveis, index=len(periodos_disponiveis) - 1)
        
        submit_button = st.form_submit_button("Calcular Reajuste")

    if submit_button:
        try:
            ist_inicial_row = df_ist[df_ist['PERÍODO'] == data_inicial_str]
            ist_final_row = df_ist[df_ist['PERÍODO'] == data_final_str]

            if ist_inicial_row.empty or ist_final_row.empty:
                st.warning(f"Uma ou ambas as datas não foram encontradas na base de dados do IST.")
            else:
                ist_inicial = ist_inicial_row['ÍNDICE'].iloc[0]
                ist_final = ist_final_row['ÍNDICE'].iloc[0]

                valor_reajustado = valor_original * (ist_final / ist_inicial)
                reajuste_percentual = ((ist_final / ist_inicial) - 1) * 100

                st.subheader("Resultado do Cálculo")
                st.write(f"**Valor Original:** R$ {valor_original:.2f}")
                st.write(f"**Índice na data inicial ({data_inicial_str}):** {ist_inicial}")
                st.write(f"**Índice na data final ({data_final_str}):** {ist_final}")
                st.metric("Valor Reajustado", value=f"R$ {valor_reajustado:.2f}", delta=f"{reajuste_percentual:.2f}%")

        except Exception as e:
            st.error(f"Ocorreu um erro: {e}")
else:
    st.error("Não foi possível carregar os dados. Verifique a conexão com a internet.")

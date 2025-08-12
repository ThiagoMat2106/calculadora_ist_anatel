import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from time import sleep
import streamlit as st

# --- PARTE 1: EXTRAÇÃO E TRATAMENTO DOS DADOS ---

@st.cache_data
def extrair_dados_ist_completo():
    """
    Extrai todos os dados do IST do site da Anatel, com cache para performance.
    """
    url = "https://www.gov.br/anatel/pt-br/regulado/competicao/tarifas-e-precos/valores-do-ist"
    
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--log-level=3')
    
    # Esta linha usa o Chromium que é instalado pelo packages.txt
    options.binary_location = "/usr/bin/chromium"
    
    # Esta linha usa o chromedriver que vem com o Chromium
    service = Service(executable_path='/usr/bin/chromedriver')

    try:
        driver = webdriver.Chrome(service=service, options=options)
        st.info("Buscando dados do IST na Anatel...")
        driver.get(url)

        expand_buttons = driver.find_elements(By.CSS_SELECTOR, 'button.panel-heading')
        for button in expand_buttons:
            driver.execute_script("arguments[0].click();", button)
            sleep(0.5)

        page_source = driver.page_source
        driver.quit()
        
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
    st.error("Não foi possível carregar os dados. Verifique as configurações do Selenium e a conexão com a internet.")

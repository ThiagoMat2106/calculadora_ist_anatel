import pandas as pd
import requests
from playwright.sync_api import sync_playwright
import streamlit as st

# --- EXTRAÇÃO E TRATAMENTO DOS DADOS ---

@st.cache_data(ttl=86400)
def extrair_dados_ist_completo():
    """
    Extrai todos os dados do IST do site da Anatel usando Playwright.
    """
    url = "https://www.gov.br/anatel/pt-br/regulado/competicao/tarifas-e-precos/valores-do-ist"
    
    st.info("Buscando dados do IST na Anatel...")
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
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
            
            # Conversão para formato de data para ordenação correta
            def parse_ist_periodo(periodo_str):
                meses_pt_br = {'jan': 1, 'fev': 2, 'mar': 3, 'abr': 4, 'mai': 5, 'jun': 6, 'jul': 7, 'ago': 8, 'set': 9, 'out': 10, 'nov': 11, 'dez': 12, 'janeiro': 1, 'fevereiro': 2, 'março': 3, 'abril': 4, 'maio': 5, 'junho': 6, 'julho': 7, 'agosto': 8, 'setembro': 9, 'outubro': 10, 'novembro': 11, 'dezembro': 12}
                mes, ano_str = periodo_str.split('/')
                ano_str = ''.join(filter(str.isdigit, ano_str))
                ano = int('20' + ano_str) if len(ano_str) == 2 else int(ano_str)
                mes_num = meses_pt_br[mes.lower()]
                return pd.to_datetime(f"{ano}-{mes_num:02d}-01")
            
            df_ist_completo['DATA_ORDENACAO'] = df_ist_completo['PERÍODO'].apply(parse_ist_periodo)
            df_ist_completo = df_ist_completo.sort_values(by='DATA_ORDENACAO', ascending=True).reset_index(drop=True)
            df_ist_completo = df_ist_completo.drop('DATA_ORDENACAO', axis=1)

            st.success("Dados do IST extraídos e compilados com sucesso.")
            return df_ist_completo
    except Exception as e:
        st.error(f"Ocorreu um erro ao extrair os dados: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=86400)
def extrair_dados_ipca():
    """
    Extrai dados históricos do IPCA da API do IBGE.
    """
    url = "https://servicodados.ibge.gov.br/api/v3/agregados/1737/periodos/-250/variaveis/2265?localidades=N1[all]"
    
    st.info("Buscando dados do IPCA no IBGE...")
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        df_ipca = pd.DataFrame.from_dict(data[0]['resultados'][0]['series'][0]['serie'], orient='index', columns=['ÍNDICE'])
        df_ipca = df_ipca.reset_index().rename(columns={'index': 'PERÍODO'})
        
        # O IBGE retorna a data no formato 'YYYYMM', precisamos formatar para 'mmm/yy'
        df_ipca['PERÍODO'] = pd.to_datetime(df_ipca['PERÍODO'], format='%Y%m').dt.strftime('%b/%y').str.lower()
        df_ipca['ÍNDICE'] = df_ipca['ÍNDICE'].astype(float)
        
        st.success("Dados do IPCA extraídos e compilados com sucesso.")
        return df_ipca
    except Exception as e:
        st.error(f"Ocorreu um erro ao extrair os dados do IPCA: {e}")
        return pd.DataFrame()


# --- INTERFACE COM STREAMLIT ---

st.set_page_config(layout="wide", page_title="Calculadora de Reajuste")

# Menu de navegação na barra lateral
pagina = st.sidebar.radio("Selecione o Índice", ["Calculadora de Reajuste IST", "Calculadora de Reajuste IPCA", "Como Calcular o IST"])

if pagina == "Calculadora de Reajuste IST":
    st.title("Calculadora de Reajuste IST")
    st.write("Calcula o reajuste do valor com base no Índice de Serviços de Telecomunicações.")
    
    df_ist = extrair_dados_ist_completo()

    if not df_ist.empty:
        with st.expander("Clique para ver todos os dados históricos"):
            st.dataframe(df_ist, use_container_width=True)

        periodos_disponiveis = df_ist['PERÍODO'].tolist()
        
        with st.form(key='calculadora_form'):
            col1, col2, col3 = st.columns(3)
            with col1:
                valor_original = st.number_input("Valor Original do Contrato", min_value=0.01, format="%.2f", value=150.00)
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
                    valor_original_formatado = f"R$ {valor_original:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                    valor_reajustado_formatado = f"R$ {valor_reajustado:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

                    st.subheader("Resultado do Cálculo")
                    st.write(f"**Valor Original:** {valor_original_formatado}")
                    st.write(f"**Índice na data inicial ({data_inicial_str}):** {ist_inicial}")
                    st.write(f"**Índice na data final ({data_final_str}):** {ist_final}")
                    st.metric("Valor Reajustado", value=valor_reajustado_formatado, delta=f"{reajuste_percentual:.2f}%")

            except Exception as e:
                st.error(f"Ocorreu um erro: {e}")
    else:
        st.error("Não foi possível carregar os dados. Verifique a conexão com a internet.")

elif pagina == "Calculadora de Reajuste IPCA":
    st.title("Calculadora de Reajuste IPCA")
    st.write("Calcula o reajuste do valor com base no Índice Nacional de Preços ao Consumidor Amplo.")

    df_ipca = extrair_dados_ipca()

    if not df_ipca.empty:
        with st.expander("Clique para ver todos os dados históricos"):
            st.dataframe(df_ipca, use_container_width=True)

        periodos_disponiveis = df_ipca['PERÍODO'].tolist()

        with st.form(key='ipca_calculadora_form'):
            col1, col2, col3 = st.columns(3)
            with col1:
                valor_original = st.number_input("Valor Original do Contrato", min_value=0.01, format="%.2f", value=150.00, key='ipca_valor_original')
            with col2:
                data_inicial_str = st.selectbox("Mês/Ano Inicial para o Reajuste", options=periodos_disponiveis, index=0, key='ipca_data_inicial')
            with col3:
                data_final_str = st.selectbox("Mês/Ano Final para o Reajuste", options=periodos_disponiveis, index=len(periodos_disponiveis) - 1, key='ipca_data_final')

            submit_button = st.form_submit_button("Calcular Reajuste", key='ipca_submit')
        
        if submit_button:
            try:
                ipca_inicial_row = df_ipca[df_ipca['PERÍODO'] == data_inicial_str]
                ipca_final_row = df_ipca[df_ipca['PERÍODO'] == data_final_str]

                if ipca_inicial_row.empty or ipca_final_row.empty:
                    st.warning(f"Uma ou ambas as datas não foram encontradas na base de dados do IPCA.")
                else:
                    ipca_inicial = ipca_inicial_row['ÍNDICE'].iloc[0]
                    ipca_final = ipca_final_row['ÍNDICE'].iloc[0]
                    valor_reajustado = valor_original * (ipca_final / ipca_inicial)
                    reajuste_percentual = ((ipca_final / ipca_inicial) - 1) * 100
                    valor_original_formatado = f"R$ {valor_original:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                    valor_reajustado_formatado = f"R$ {valor_reajustado:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

                    st.subheader("Resultado do Cálculo")
                    st.write(f"**Valor Original:** {valor_original_formatado}")
                    st.write(f"**Índice na data inicial ({data_inicial_str}):** {ipca_inicial}")
                    st.write(f"**Índice na data final ({data_final_str}):** {ipca_final}")
                    st.metric("Valor Reajustado", value=valor_reajustado_formatado, delta=f"{reajuste_percentual:.2f}%")

            except Exception as e:
                st.error(f"Ocorreu um erro: {e}")
    else:
        st.error("Não foi possível carregar os dados do IBGE. Verifique a conexão com a internet ou se a API está disponível.")

elif pagina == "Como Calcular o IST":
    st.title("Como o reajuste do IST é calculado?")
    st.write("O Índice de Serviços de Telecomunicações (IST) é utilizado para reajustar valores contratuais com base na variação dos preços de serviços de telecomunicações no Brasil. O cálculo é feito de forma simples, utilizando a proporção entre os índices do período inicial e final.")
    
    st.markdown("---")
    
    st.subheader("Fórmula de Cálculo")
    st.write("A fórmula para encontrar o novo valor reajustado é:")
    st.code("Valor Reajustado = Valor Original * (Índice do Mês Final / Índice do Mês Inicial)", language="python")
    
    st.write("A fórmula para encontrar o percentual de reajuste é:")
    st.code("Reajuste Percentual = ((Índice do Mês Final / Índice do Mês Inicial) - 1) * 100", language="python")
    
    st.markdown("---")
    
    st.subheader("Exemplo Prático")
    st.write("Imagine que um contrato com valor de R$ 1.000,00 precisa ser reajustado de **Janeiro/2023** para **Janeiro/2024**.")
    
    st.write("1. **Valores do IST nos períodos:**")
    st.write("- **Janeiro/2023:** 114.77")
    st.write("- **Janeiro/2024:** 118.52")

    st.write("2. **Cálculo do Valor Reajustado:**")
    st.code("Valor Reajustado = 1.000 * (118.52 / 114.77) ≈ R$ 1.032,68", language="python")
    
    st.write("3. **Cálculo do Reajuste Percentual:**")
    st.code("Reajuste Percentual = ((118.52 / 114.77) - 1) * 100 ≈ 3,21%", language="python")

    st.write("A sua calculadora já faz todo esse trabalho automaticamente para você!")

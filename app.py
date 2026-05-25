import streamlit as st

# ==========================================
# CONFIGURAÇÃO DO NOVO DESTINO
# ==========================================
# Coloca aqui o link da tua nova App no Streamlit Cloud
NOVO_URL = "https://bbportugalapp2.streamlit.app/"

st.set_page_config(page_title="App Atualizada", page_icon="🚀", layout="centered")

st.markdown("""
<style>
    /* Esconde o menu lateral e o cabeçalho do Streamlit para ficar limpo */
    [data-testid="collapsedControl"] {display: none;}
    header {display: none !important;}
</style>
""", unsafe_allow_html=True)

st.title("🚀 A Fénix Negra tem uma nova morada!")
st.markdown("O ecossistema BBPT foi atualizado para uma versão muito mais rápida, estável e segura.")

st.warning("A redirecionar automaticamente para a nova aplicação...")

st.info(f"Se não fores redirecionado em 3 segundos, **[clica aqui para aceder ao novo Hub]({NOVO_URL})**.")

# ==========================================
# INJEÇÃO DE CÓDIGO PARA REDIRECIONAR O BROWSER
# ==========================================
# Usamos meta refresh como fallback e JavaScript para ação imediata
redirect_code = f"""
<meta http-equiv="refresh" content="3; url={NOVO_URL}">
<script>
    setTimeout(function() {{
        window.top.location.href = '{NOVO_URL}';
    }}, 2000);
</script>
"""

st.markdown(redirect_code, unsafe_allow_html=True)

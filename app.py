import streamlit as st

# ==========================================
# COLOCA AQUI O LINK DA NOVA APP
# ==========================================
NOVO_URL = "https://bbportugalapp2.streamlit.app/"

st.set_page_config(page_title="A redirecionar...", page_icon="🔗", layout="centered")

# Esconde o menu e o cabeçalho do Streamlit
st.markdown("""
<style>
    [data-testid="collapsedControl"] {display: none;}
    header {display: none !important;}
</style>
""", unsafe_allow_html=True)

st.info(f"A redirecionar... **[Clica aqui se demorar muito]({NOVO_URL})**")

# ==========================================
# MÉTODO INFALÍVEL: META REFRESH NATIVO
# ==========================================
# Injeta a instrução de redirecionamento diretamente no HTML da página principal, sem iframes.
# O "0" significa zero segundos de espera.
st.markdown(f'<meta http-equiv="refresh" content="0; url={NOVO_URL}">', unsafe_allow_html=True)

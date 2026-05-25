import streamlit as st

# ==========================================
# COLOCA AQUI O LINK DA NOVA APP
# ==========================================
NOVO_URL = "https://bbportugalapp2.streamlit.app/"

st.set_page_config(page_title="App Atualizada", page_icon="🚀", layout="centered")

st.markdown("""
<style>
    [data-testid="collapsedControl"] {display: none;}
    header {display: none !important;}
</style>
""", unsafe_allow_html=True)

st.title("🚀 Já está dispobível o BBPT Hub 2.0!")
st.markdown("O ecossistema BBPT foi atualizado para uma versão muito mais rápida, estável e segura.")

st.info(f"A redirecionar... Se não fores reencaminhado, **[clica aqui para aceder]({NOVO_URL})**.")

# ==========================================
# MÉTODO DE REDIRECIONAMENTO SEGURO (SEM LOOP)
# ==========================================
js_redirect = f"""
<script>
    // Espera 2 segundos e redireciona de forma limpa, substituindo o histórico
    setTimeout(function() {{
        window.location.replace('{NOVO_URL}');
    }}, 2000);
</script>
"""

st.components.v1.html(js_redirect, height=0)

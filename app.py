import streamlit as st

# ==========================================
# CHANGE THIS LINK TO UPDATE THE QR CODE DESTINATION
# ==========================================
NOVO_URL = "https://bbportugalapp2.streamlit.app/"

# Generic page config so it doesn't look out of place for different campaigns
st.set_page_config(page_title="A redirecionar...", page_icon="🔗", layout="centered")

st.markdown("""
<style>
    [data-testid="collapsedControl"] {display: none;}
    header {display: none !important;}
</style>
""", unsafe_allow_html=True)

# A clean, simple fallback message
st.info(f"A redirecionar... **[Clica aqui se demorar muito]({NOVO_URL})**")

# ==========================================
# MÉTODO DE REDIRECIONAMENTO SEGURO (MAIN WINDOW)
# ==========================================
js_redirect = f"""
<script>
    // window.top força o redirecionamento da aba inteira do browser,
    // escapando do iframe invisível do Streamlit.
    setTimeout(function() {{
        window.top.location.href = '{NOVO_URL}';
    }}, 0);
</script>
"""

st.components.v1.html(js_redirect, height=0)

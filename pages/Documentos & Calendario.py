import streamlit as st
import os

# ==========================================
# CONFIGURAÇÃO DE PÁGINA
# ==========================================
st.set_page_config(page_title="Documentos BBPT", layout="wide")

st.title("📚 Documentos e Informação Geral")
st.markdown("Aqui podes consultar e descarregar todas as regras oficiais, regulamentos da liga e guias da BBPT.")
st.write("")

# Cria as duas colunas principais
col_esq, col_dir = st.columns(2)

# ==========================================
# COLUNA ESQUERDA: MANUAIS E GUIAS VISUAIS
# ==========================================
with col_esq:
    st.header("📄 Manuais e Regulamentos")

    # Cartão: Rulebook Oficial
    with st.container(border=True):
        st.subheader("📖 Rulebook Oficial BBPT")
        st.write("Este é o documento principal e sagrado. Aqui encontras todas as regras de jogo, legalidade de peças, faltas e formato oficial dos torneios (3on3 Blind Pick).")
        
        st.write("") # Espaço antes do botão
        file_path_rulebook = "RULEBOOK OFICIAL BBPT UPDATE 2 FINAl.pdf"
        if os.path.exists(file_path_rulebook):
            with open(file_path_rulebook, "rb") as f:
                st.download_button(
                    label="📥 Descarregar PDF - Rulebook",
                    data=f,
                    file_name="Rulebook_Oficial_BBPT.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
        else:
            st.error("Ficheiro não encontrado.")

    # Cartão: Regulamento da Liga
    with st.container(border=True):
        st.subheader("🏆 Manual de Regulamento das Ligas")
        st.write("Documento essencial para perceber a mecânica da Liga BBPT. Explica o sistema de Drop Score (contam as tuas 8 melhores pontuações) e o funcionamento geral das ligas.")
        
        st.write("") # Espaço antes do botão
        file_path_liga = "Liga BBPT - MANUAL DE REGULAMENTO (2).pdf"
        if os.path.exists(file_path_liga):
            with open(file_path_liga, "rb") as f:
                st.download_button(
                    label="📥 Descarregar PDF - Liga",
                    data=f,
                    file_name="Regulamento_Liga_BBPT.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
        else:
            st.error("Ficheiro não encontrado.")

    st.write("")
    
    # Movido para a Coluna Esquerda
    st.header("🖼️ Formato BP")
    with st.container(border=True):
        st.subheader("📊 Faz aqui download da tabela mais atual")

        # Atualizado para ler o .jpg correto
        file_path_format = "BBPT_BP_Format.PNG"
        if os.path.exists(file_path_format):
            st.image(file_path_format, use_container_width=True)
        else:
            st.warning("Imagem do formato não encontrada no servidor.")

# ==========================================
# COLUNA DIREITA: CARTAZES E PRÓXIMOS TORNEIOS
# ==========================================
with col_dir:
    st.header("📅 Próximos Torneios")
    st.write("Fica atento aos próximos eventos agendados!")

    cartazes = [
        {
            "nome": " Torneio Critical Hit (09/05/2026) - Liga Critical X - Link do Challonge: https://challonge.com/tournaments/signup/Xwp8IJLMCB#/signup/z3jrsguioeg",
            "url": "https://cdn.discordapp.com/attachments/1280979233619050660/1501703664249737216/Torneio_Critical_Hit_31_01_copy_4-1.png?ex=69ff0445&is=69fdb2c5&hm=e30239a251ffee95815947c15095990cf18c8bc72bfc0076ad03c57b0e33e239&"
        },

        {
            "nome": " Torneio Mercadia (10/05/2026) - Mercadia Showdown - Link do Challonge : https://challonge.com/tournaments/signup/kyyU41xhoE#/signup/zag2e0uy3ll",
            "url": "https://cdn.discordapp.com/attachments/1280979233619050660/1501703548315111454/Torneio_Mercadia_08_02_3.png?ex=69ff042a&is=69fdb2aa&hm=a3c2673fb947302bdad5a7ec2f8191a817bb5da7f059e8d3a5bb95521bb4ffa3&"
        },
        {
            "nome": " Liga Fénix Negra (10/05/2026) - Link do Challonge: https://challonge.com/tournaments/signup/U5VMN5OArL#/signup/ctbysplc807",
            "url": "https://cdn.discordapp.com/attachments/1334224353142771815/1502324365969195008/4_por_5_fenix.jpg?ex=69ff4c18&is=69fdfa98&hm=5af689e9ca43e9fb7d707e59964e88530c01c85b741c4a6607fe7b1f0972a75f&"
        },
    ]
    
    if cartazes:
        for cartaz in cartazes:
            with st.container(border=True):
                st.subheader(f"📌 {cartaz['nome']}")
                
                # Truque das colunas para criar margens laterais invisíveis e "esmagar" a imagem no centro
                c1, c2, c3 = st.columns([1, 3, 1])
                with c2:
                    try:
                        st.image(cartaz["url"], use_container_width=True)
                    except Exception:
                        st.error("Erro ao carregar a imagem. Verifica o link do Discord.")
    else:
        with st.container(border=True):
            st.info("De momento não há novos torneios agendados.")

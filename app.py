import streamlit as st
import pandas as pd
import json
import os

# 1. Configuração da Página
st.set_page_config(
    page_title="BBPT Hub", 
    page_icon="logo.png",  # <-- ESTA É A MAGIA
    layout="wide"
)

# ==========================================
# 🛑 CSS MÁGICO PARA O BOTÃO MOBILE E FRAMES
# ==========================================
st.markdown("""
<style>
    /* Alvo: Botão de expandir o menu lateral */
    [data-testid="collapsedControl"] {
        background-color: #ff4b4b !important;
        border-radius: 8px !important;
        padding: 5px 15px !important;
        box-shadow: 0px 4px 6px rgba(0,0,0,0.2) !important;
        margin-top: 5px !important;
        margin-left: 5px !important;
        color: white !important;
    }
    
    [data-testid="collapsedControl"] svg {
        fill: white !important;
        color: white !important;
    }
    
    [data-testid="collapsedControl"]::after {
        content: "MENU";
        font-family: sans-serif;
        font-weight: 800;
        font-size: 14px;
        margin-left: 8px;
    }
</style>
""", unsafe_allow_html=True)

# 2. Carregar a Base de Dados
@st.cache_data
def load_data():
    try:
        with open('bbpt_master_db.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return None

def load_communications(file_path):
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if content:
                return content
    return None

db = load_data()

if not db:
    st.error("Base de dados não encontrada. Corre o bbpt_admin_sync.py primeiro.")
    st.stop()

# 3. Menu de Navegação Lateral
st.sidebar.image("logo.png", use_container_width=True)
st.sidebar.divider()
st.sidebar.title("🛡️ BBPT Hub")
# 👇 ADICIONADA A NOVA PÁGINA DE CONTACTOS 👇
page = st.sidebar.radio("Navegação:", [
    "Liga Critical", 
    "Liga Versus", 
    "Torneio de Equipas - Liga Versus", 
    "Rankings Globais", 
    "Ad-Hoc: Blader Profile",
    "Contactos & Equipa"
])
st.sidebar.caption(f"Última Atualização: {db['last_updated']}")

# ==========================================
# FUNÇÃO REUTILIZÁVEL PARA RENDERIZAR MÉTRICAS AVANÇADAS
# ==========================================
def render_advanced_metrics(metrics, league_mode=True):
    title_suffix = "League" if league_mode else "Global Rankings"
    
    st.subheader(f"📈 {title_suffix} Advanced Metrics")
    
    st.markdown(f"### 👑 Kings of the {title_suffix}")
    st.caption("Top players with the most 1st place finishes.")
    for king in metrics.get('kings', []): st.write(king)
    
    st.markdown(f"### ⚔️ Upset of the {title_suffix}")
    st.info(metrics.get('upset_season', 'N/A'))
    
    st.markdown("### 🛡️ The Gatekeeper")
    st.caption("Dominates Swiss but struggles in Top Cut.")
    st.warning(metrics.get('gatekeeper', 'N/A'))
    
    st.markdown("### 📊 Meta-Health (Média de Pontos Combinados)")
    st.success(metrics.get('meta_health', 'N/A'))
    st.markdown("""
    *(Jogos normais até 4 pts | Top Cut até 5 pts | Finais até 7 pts)*
    * **Alta (> 6.5 Pts):** Meta de Ataque Agressivo (Jogos rápidos e explosivos decididos por X-Treme Finishes de 3 pts. Ex: 4-0, 5-1)
    * **Média (5.0 - 6.5 Pts):** Meta Equilibrada (Mistura saudável de Spin, Burst e Over Finishes)
    * **Baixa (< 5.0 Pts):** Meta de Defesa/Stamina (Jogos longos, muitas rondas decididas por Spin Finishes de 1 ponto. Ex: 4-3, 5-4)
    """)

# ==========================================
# FUNÇÃO PARA RENDERIZAR PÁGINAS DE LIGA
# ==========================================
def render_league_page(league_name, league_key, comm_file):
    st.title(f"🏆 {league_name}")
    
    comunicado = load_communications(comm_file)
    if comunicado:
        st.info(f"📢 **Quadro de Avisos da Organização:**\n\n{comunicado}")
    
    data = db.get(league_key)
    if not data or not data.get("standings"):
        st.warning(f"Ainda não há dados de partidas disponíveis para a {league_name}.")
        return

    st.subheader("📊 League Standings")
    st.markdown("*Official points ranking based on Top 8 finishes.*")
    df_standings = pd.DataFrame(data['standings'])
    if not df_standings.empty:
        df_standings.set_index('Rank', inplace=True)
    st.dataframe(df_standings, use_container_width=True)

    st.divider()

    col1, col2 = st.columns([1, 1])
    with col1:
        render_advanced_metrics(data['advanced_metrics'], league_mode=True)

    with col2:
        st.subheader("📋 Tournament Audit Log")
        df_audit = pd.DataFrame(data['audit_log'])
        if not df_audit.empty:
            df_audit.index += 1
            df_audit.index.name = "#"
        st.dataframe(df_audit, use_container_width=True)

# ==========================================
# RENDERIZAÇÃO DA PÁGINA ESCOLHIDA
# ==========================================
if page == "Liga Critical":
    render_league_page("Liga Critical X", "league_critical", "comunicacoesCritical.txt")

elif page == "Liga Versus":
    render_league_page("Liga Versus", "league_versus", "comunicacoesVersus.txt")

elif page == "Torneio de Equipas - Liga Versus":
    st.title("🤝 Torneio de Equipas - Liga Versus")
    
    comunicado = load_communications("comunicacoesEquipasVersus.txt")
    if comunicado:
        st.info(f"📢 **Quadro de Avisos:**\n\n{comunicado}")
    
    st.divider()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 Standings Finais")
        st.markdown("Resultados oficiais do torneio de equipas.")
        try:
            st.image("foto_equipas.jpg", use_container_width=True)
        except Exception:
            st.warning("⚠️ Imagem 'foto_equipas.jpg' não encontrada. Por favor, faz o upload deste ficheiro no teu GitHub.")
            
    with col2:
        st.subheader("📺 VOD do Torneio")
        st.markdown("Acompanha a ação a partir do momento chave!")
        st.video("https://youtu.be/vsbuwPL5uzs?si=egyuV9P3j8Gdfc6z", start_time=1319, autoplay=True, muted=True)

elif page == "Rankings Globais":
    st.title("🌐 BBPT Global Power Rankings")
    
    comunicado = load_communications("comunicacoesGlobal.txt")
    if comunicado:
        st.info(f"📢 **Quadro de Avisos Global:**\n\n{comunicado}")
        
    st.markdown("O sistema oficial de Power Rating (ELO) baseado em todo o historial Ad-Hoc.")
    df_rankings = pd.DataFrame(db['global_versus']['rankings'])
    if not df_rankings.empty:
        df_rankings.set_index('Rank', inplace=True)
    st.dataframe(df_rankings, use_container_width=True)

    st.divider()

    render_advanced_metrics(db['global_versus'].get('advanced_metrics', {}), league_mode=False)

elif page == "Ad-Hoc: Blader Profile":
    st.title("👤 Blader Intelligence Profile")
    
    player_list = sorted(list(db['global_versus']['profiles'].keys()))
    selected_player = st.selectbox("Selecione o Blader para análise detalhada:", player_list)
    
    if selected_player:
        p_data = db['global_versus']['profiles'][selected_player]
        
# --- 1. EXTRACÇÃO DE DADOS E CÁLCULOS A PARTIR DO JSON ---
        total_jogadores = len(db['global_versus']['profiles'])
        
        rank_atual = "N/A"
        for r in db['global_versus'].get('rankings', []):
            if r['Player'] == selected_player:
                rank_atual = r['Rank']
                break
                
        # Total Eventos da Liga (O máximo de eventos jogados por algum jogador)
        total_eventos_liga = max((prof.get('events_played', 0) for prof in db['global_versus']['profiles'].values()), default=0)
        
        # Matemática de Vitórias e Derrotas
        total_matches = p_data.get('total_matches', 0)
        total_wins = sum(m.get('Wins', 0) for m in p_data.get('matchups', []))
        total_losses = total_matches - total_wins
        win_rate = p_data.get('win_rate', 0)
        
        events_played = p_data.get('events_played', 0)
        tournaments_won = p_data.get('tournaments_won', 0)
        
        # Extrair os Pódios (Lendo de forma inteligente o AI Prompt do teu JSON)
        first_place = 0
        second_place = 0
        third_place = 0
        fifth_place = 0
        made_top_cut = 0
        
        prompt_text = p_data.get('ai_prompt', '')
        import re
        podios_match = re.search(r'- Histórico de Pódios:\s*([^\n]+)', prompt_text)
        if podios_match:
            podios_str = podios_match.group(1)
            if "Nenhum" not in podios_str and "No Top" not in podios_str:
                for item in podios_str.split(','):
                    item = item.strip()
                    if 'x' in item:
                        try:
                            qtd_str, pos_str = item.split('x')
                            qtd = int(qtd_str.strip())
                            pos = pos_str.strip().lower()
                            
                            if '1st' in pos: first_place += qtd
                            elif '2nd' in pos: second_place += qtd
                            elif '3rd' in pos: third_place += qtd
                            elif '5th' in pos: fifth_place += qtd
                            
                            made_top_cut += qtd
                        except:
                            pass
        
        missed_top_cut = events_played - made_top_cut
        if missed_top_cut < 0: missed_top_cut = 0

        # --- 2. INTERFACE VISUAL ---
        st.markdown(f"## *{selected_player} | Rank: {rank_atual} of {total_jogadores} players*")
        st.divider()

        st.markdown("#### Personal Match Record")
        st.caption("Overview of your absolute win/loss performance across all matches.")

        c1, c2, c3 = st.columns(3)
        with c1:
            with st.container(border=True):
                st.markdown(f"<h2 style='text-align: center; color: #a1e533; margin: 0;'>{win_rate}%</h2>", unsafe_allow_html=True)
                st.markdown("<p style='text-align: center; color: gray; margin: 0;'>Overall Win Rate</p>", unsafe_allow_html=True)
        with c2:
            with st.container(border=True):
                st.markdown(f"<h2 style='text-align: center; color: #4CAF50; margin: 0;'>{total_wins}</h2>", unsafe_allow_html=True)
                st.markdown("<p style='text-align: center; color: gray; margin: 0;'>Total Wins</p>", unsafe_allow_html=True)
        with c3:
            with st.container(border=True):
                st.markdown(f"<h2 style='text-align: center; color: #F44336; margin: 0;'>{total_losses}</h2>", unsafe_allow_html=True)
                st.markdown("<p style='text-align: center; color: gray; margin: 0;'>Total Losses</p>", unsafe_allow_html=True)

        c4, c5, _ = st.columns(3)
        with c4:
            with st.container(border=True):
                st.markdown(f"<h2 style='text-align: center; margin: 0;'>{total_matches}</h2>", unsafe_allow_html=True)
                st.markdown("<p style='text-align: center; color: gray; margin: 0;'>Total Matches</p>", unsafe_allow_html=True)
        with c5:
            with st.container(border=True):
                st.markdown(f"<h2 style='text-align: center; color: #9C27B0; margin: 0;'>{p_data.get('elo_global', 'N/A')}</h2>", unsafe_allow_html=True)
                st.markdown("<p style='text-align: center; color: gray; margin: 0;'>Global ELO</p>", unsafe_allow_html=True)

        st.write("")

        st.markdown("#### Tournament Placements Record")
        st.caption("Breakdown of final ranks achieved and overall event participation.")

        t1, t2, t3 = st.columns(3)
        with t1:
            with st.container(border=True):
                st.markdown(f"<h2 style='text-align: center; margin: 0;'>{events_played} <span style='font-size: 0.5em; color: gray;'>/ {total_eventos_liga}</span></h2>", unsafe_allow_html=True)
                st.markdown("<p style='text-align: center; color: gray; margin: 0;'>Events Played</p>", unsafe_allow_html=True)
        with t2:
            with st.container(border=True):
                st.markdown(f"<h2 style='text-align: center; margin: 0;'>{tournaments_won}</h2>", unsafe_allow_html=True)
                st.markdown("<p style='text-align: center; color: gray; margin: 0;'>Tournaments Won</p>", unsafe_allow_html=True)

        t4, t5, t6 = st.columns(3)
        with t4:
            with st.container(border=True):
                st.markdown(f"<h2 style='text-align: center; margin: 0;'>{first_place}x</h2>", unsafe_allow_html=True)
                st.markdown("<p style='text-align: center; color: #FFD700; margin: 0;'>🥇 1st Place</p>", unsafe_allow_html=True)
        with t5:
            with st.container(border=True):
                st.markdown(f"<h2 style='text-align: center; margin: 0;'>{second_place}x</h2>", unsafe_allow_html=True)
                st.markdown("<p style='text-align: center; color: #C0C0C0; margin: 0;'>🥈 2nd Place</p>", unsafe_allow_html=True)
        with t6:
            with st.container(border=True):
                st.markdown(f"<h2 style='text-align: center; margin: 0;'>{third_place}x</h2>", unsafe_allow_html=True)
                st.markdown("<p style='text-align: center; color: #CD7F32; margin: 0;'>🥉 3rd Place</p>", unsafe_allow_html=True)

        t7, t8, _ = st.columns(3)
        with t7:
            with st.container(border=True):
                st.markdown(f"<h2 style='text-align: center; margin: 0;'>{fifth_place}x</h2>", unsafe_allow_html=True)
                st.markdown("<p style='text-align: center; color: gray; margin: 0;'>5th Place</p>", unsafe_allow_html=True)
        with t8:
            with st.container(border=True):
                st.markdown(f"<h2 style='text-align: center; color: #F44336; margin: 0;'>{missed_top_cut}x</h2>", unsafe_allow_html=True)
                st.markdown("<p style='text-align: center; color: gray; margin: 0;'>❌ Missed Top Cut</p>", unsafe_allow_html=True)

        st.divider()

        st.subheader("🤖 Pede Conselho ao teu AI Coach (Gratuito)")
        st.markdown("""
        Queres uma análise tática profunda ao teu perfil?  
        1. Clica no ícone de **Copiar** no canto superior direito da caixa abaixo.  
        2. Abre o teu assistente preferido (como o [Google Gemini](https://gemini.google.com/) ou o ChatGPT).  
        3. Cola o texto gerado, envia e lê as dicas personalizadas para melhorares o teu jogo!
        """)
        st.code(p_data.get('ai_prompt', 'N/A'), language='text')

        st.divider()

        st.subheader("🎯 Player Matchups (With True Elo Probability)")
        df_matchups = pd.DataFrame(p_data['matchups'])
        if not df_matchups.empty:
            df_matchups.index += 1
            df_matchups.index.name = "#"
        st.dataframe(df_matchups, use_container_width=True)

        st.divider()

        st.subheader("📖 Raw Match History")
        df_history = pd.DataFrame(p_data['raw_matches'])
        if not df_history.empty:
            df_history.index += 1
            df_history.index.name = "#"
        st.dataframe(df_history, use_container_width=True)

# 👇 A NOVA PÁGINA DE CONTACTOS E EQUIPA 👇
elif page == "Contactos & Equipa":
    st.title("📞 Contactos & Organização")
    
    # Redes Sociais com Botões
    st.subheader("🌐 Comunidade e Redes Sociais")
    
    # 🔥 CORREÇÃO AQUI: 4 COLUNAS EM VEZ DE 3 🔥
    c1, c2, c3, c4 = st.columns(4) 
    
    with c1:
        st.link_button("📸 Instagram", "https://www.instagram.com/beyblade_pt?utm_source=ig_web_button_share_sheet&igsh=ZDNlZDc0MzIxNw==", use_container_width=True)
    with c2:
        st.link_button("💬 Comunidade Whatsapp", "https://chat.whatsapp.com/GCLf0RjTFjFHzc1yK2VjPo?utm_source=ig&utm_medium=social&utm_content=link_in_bio&fbclid=PAZXh0bgNhZW0CMTEAc3J0YwZhcHBfaWQMMjU2MjgxMDQwNTU4AAGnIfazCWNONck6v0j57JdRIIAkPFMdx9LHQt4GCOhw-8I_JqQ87GIcN_2x2hE_aem_dl79Vk4wQKv_jaj375kITg", use_container_width=True)
    with c3:
        st.link_button("📺 YouTube", "https://www.youtube.com/@BeybladePortugal", use_container_width=True)
    with c4:
        st.link_button("📺 Discord", "https://discord.com/invite/KssWPXxFnq?utm_source=ig&utm_medium=social&utm_content=link_in_bio&fbclid=PAZXh0bgNhZW0CMTEAc3J0YwZhcHBfaWQMMjU2MjgxMDQwNTU4AAGnAEkk3ND2fdA8LQvrbAdxUFX_ErELi5XLZ_AqvTn-rxJ1Prtbh2crvWzNoKg_aem_eHLufOmDJBHm4oWRy1I3cQ", use_container_width=True)

    st.divider()
    
    st.subheader("👥 Quadro da Organização e Gestão")
    st.markdown("Conhece a equipa responsável pela manutenção e integridade da Liga BBPT.")
    
    # Carregar e processar o ficheiro de texto em Frames separados
    conteudo_org = load_communications("organizacao.txt")
    if conteudo_org:
        # Corta o texto sempre que houver "==="
        seccoes = conteudo_org.split("===")
        
        # O Streamlit coloca cada pedaço dentro de um quadro com borda!
        for seccao in seccoes:
            if seccao.strip():
                with st.container(border=True):
                    st.markdown(seccao.strip())
    else:
        st.info("Cria o ficheiro `organizacao.txt` no teu GitHub e usa `===` para separar as secções da tua equipa.")

import streamlit as st
import pandas as pd
import json
import base64
import os
import re

# 1. Configuração da Página
st.set_page_config(
    page_title="BBPT Hub", 
    page_icon="logo.png",
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

page = st.sidebar.radio("Navegação:", [
    "🏠 Página Inicial",
    "Liga Critical", 
    "Liga Versus", 
    "Torneio de Equipas - Liga Versus", 
    "Rankings Globais", 
    "Ad-Hoc: Blader Profile",
    "Contactos & Equipa"
])
st.sidebar.caption(f"Última Atualização: {db['last_updated']}")

# ==========================================
# FUNÇÕES REUTILIZÁVEIS
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

def render_league_page(league_name, league_key, comm_file):
    if "versus" in league_name.lower() or "versus" in league_key.lower():
        nome_ficheiro = "versus.png"
    else:
        nome_ficheiro = "critical.png"
        
    img_path = nome_ficheiro if os.path.exists(nome_ficheiro) else f"../{nome_ficheiro}"
    
    if os.path.exists(img_path):
        with open(img_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode()
        
        st.markdown(
            f"""
            <div style="display: flex; align-items: center; margin-bottom: 15px;">
                <img src="data:image/png;base64,{encoded_string}" width="70" style="margin-right: 15px;">
                <h1 style="margin: 0; padding: 0; font-size: 3.5rem;">{league_name}</h1>
            </div>
            """, 
            unsafe_allow_html=True
        )
    else:
        st.markdown(f"<h1 style='font-size: 3.5rem;'>🏆 {league_name}</h1>", unsafe_allow_html=True)
    
    comunicado = load_communications(comm_file)
    if comunicado:
        st.info(f"📢 **Quadro de Avisos da Organização:**\n\n{comunicado}")
    
    data = db.get(league_key)
    
    if not data or not data.get("standings_top8"):
        st.warning(f"Ainda não há dados de partidas disponíveis para a {league_name}.")
        return

    st.subheader("📊 League Standings")
    
    mostrar_totais = st.toggle("Mostrar Todas as Participações (Pontuação Total)")
    
    if mostrar_totais:
        st.markdown("*Classificação absoluta somando o resultado de **todos** os torneios disputados.*")
        df_standings = pd.DataFrame(data['standings_total'])
    else:
        st.markdown("*Pontuação oficial da liga baseada apenas nos **8 melhores** resultados de cada Blader.*")
        df_standings = pd.DataFrame(data['standings_top8'])

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

def make_img_button(img_file, link_url, title):
    # Função auxiliar para criar botões visuais a partir de imagens locais
    if os.path.exists(img_file):
        with open(img_file, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        img_src = f"data:image/png;base64,{b64}"
    else:
        # Imagem de substituição caso ainda não tenhas feito upload do ficheiro real
        img_src = f"https://via.placeholder.com/300x150/1f2333/ff4b4b?text={title.replace(' ', '+')}"
        
    return f"""
    <a href="{link_url}" target="_blank" style="text-decoration: none;">
        <div style="text-align: center; margin-bottom: 20px;">
            <img src="{img_src}" style="width: 100%; border-radius: 12px; box-shadow: 0px 4px 8px rgba(0,0,0,0.4); border: 2px solid #ff4b4b;">
            <div style="color: white; font-weight: 800; font-size: 1.2rem; margin-top: 8px; text-transform: uppercase;">{title}</div>
        </div>
    </a>
    """

# ==========================================
# RENDERIZAÇÃO DA PÁGINA ESCOLHIDA
# ==========================================
if page == "🏠 Página Inicial":
    # --- CABEÇALHO ---
    col_logo, col_titulo = st.columns([1, 4])
    with col_logo:
        st.image("logo.png", width=120)
    with col_titulo:
        st.markdown("<h1 style='font-size: 3.5rem; margin-bottom: 0;'>BBPT Hub</h1>", unsafe_allow_html=True)
        st.markdown("### O centro oficial de dados, ferramentas e estatísticas competitivas de Beyblade.")
    
    st.divider()
    
    # --- FERRAMENTAS OFICIAIS (BOTÕES DE IMAGEM) ---
    st.subheader("🛠️ Ferramentas Oficiais")
    st.markdown("Acede rapidamente aos nossos módulos principais:")
    
    # Substitui os "#" pelos URLs reais das tuas outras apps Streamlit
    c_btn1, c_btn2, c_btn3 = st.columns(3)
    with c_btn1:
        st.markdown(make_img_button("btn_deck_check.png", "https://bbpt-league-and-player-report-mhi67nu4yvzodwxzcrkor8.streamlit.app/Deck_Check", "Deck Check"), unsafe_allow_html=True)
    with c_btn2:
        st.markdown(make_img_button("btn_deck_builder.png", "https://bbpt-league-and-player-report-mhi67nu4yvzodwxzcrkor8.streamlit.app/Deck_Builder", "Deck Builder"), unsafe_allow_html=True)
    with c_btn3:
        st.markdown(make_img_button("btn_battle_logger.png", "https://bbpt-league-and-player-report-mhi67nu4yvzodwxzcrkor8.streamlit.app/Battle_Logger", "Battle Logger"), unsafe_allow_html=True)
        
    st.divider()
    
    # --- DASHBOARD (Mini-widget Top 1 Global e Avisos) ---
    c1, c2 = st.columns([1, 1])
    with c1:
        with st.container(border=True):
            st.markdown("<h3 style='text-align: center;'>👑 Ranking Global: #1 Atual</h3>", unsafe_allow_html=True)
            try:
                top1 = db['global_versus']['rankings'][0]
                st.markdown(f"<h1 style='text-align: center; color: #ff4b4b; margin:0; font-size: 4rem;'>{top1['Player']}</h1>", unsafe_allow_html=True)
                st.markdown(f"<p style='text-align: center; color: gray; font-size: 1.5rem;'>{top1['Elo']} ELO</p>", unsafe_allow_html=True)
            except:
                st.markdown("<p style='text-align: center;'>A calcular rankings...</p>", unsafe_allow_html=True)
                
    with c2:
        with st.container(border=True):
            st.markdown("#### 📢 Últimos Avisos")
            avisos = load_communications("comunicacoesGerais.txt")
            if avisos:
                st.write(avisos)
            else:
                st.info("Sempre que fizeres o teu deck check, não te esqueças de incluir uma foto das peças originais com que vais jogar!")

elif page == "Liga Critical":
    render_league_page("Liga Critical X", "league_critical", "comunicacoesCritical.txt")

elif page == "Liga Versus":
    render_league_page("Liga Versus X", "league_versus", "comunicacoesVersus.txt")

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
        
    st.markdown("O sistema de Power Rating (ELO) baseado em todo o historial Ad-Hoc.")
    df_rankings = pd.DataFrame(db['global_versus']['rankings'])
    if not df_rankings.empty:
        df_rankings.set_index('Rank', inplace=True)
    st.dataframe(df_rankings, use_container_width=True)

    st.divider()

    render_advanced_metrics(db['global_versus'].get('advanced_metrics', {}), league_mode=False)

    st.divider()
    st.subheader("📋 Audit Log: Torneios Globais")
    st.markdown("Lista de todos os torneios que estão a alimentar o Power Rating Global e os Perfis.")
    
    global_audit = db['global_versus'].get('audit_log', [])
    if global_audit:
        df_global_audit = pd.DataFrame(global_audit)
        if not df_global_audit.empty:
            df_global_audit.index += 1
            df_global_audit.index.name = "#"
        st.dataframe(df_global_audit, use_container_width=True)
    else:
        st.warning("⚠️ O Log de Torneios ainda não foi exportado para a base de dados global.")

elif page == "Ad-Hoc: Blader Profile":
    st.title("👤 Blader Intelligence Profile")
    
    player_list = sorted(list(db['global_versus']['profiles'].keys()))
    selected_player = st.selectbox("Selecione o Blader para análise detalhada:", player_list)
    
    if selected_player:
        p_data = db['global_versus']['profiles'][selected_player]
        target_player_lower = str(selected_player).strip().lower()
        
        # --- 1. EXTRACÇÃO DE DADOS BÁSICOS DO PROFILE GLOBAL ---
        total_jogadores = len(db['global_versus']['profiles'])
        
        rank_atual = "N/A"
        for r in db['global_versus'].get('rankings', []):
            if str(r.get('Player', '')).strip().lower() == target_player_lower:
                rank_atual = r.get('Rank', 'N/A')
                break
                
        total_eventos_globais = max((int(prof.get('events_played', 0)) for prof in db['global_versus']['profiles'].values()), default=0)
        
        total_matches = int(p_data.get('total_matches', 0))
        events_played = int(p_data.get('events_played', 0))
        
        total_wins = sum(int(m.get('Wins', 0)) for m in p_data.get('matchups', []))
        total_losses = total_matches - total_wins
        win_rate = p_data.get('win_rate', 0)
        
        # --- 2. EXTRAÇÃO DE PÓDIOS DIRETAMENTE DO AI PROMPT GLOBAL ---
        first_place = 0
        second_place = 0
        third_place = 0
        fourth_place = 0
        top_8_place = 0
        
        ai_prompt = p_data.get('ai_prompt', '')
        podios_match = re.search(r'Histórico de Pódios:\s*([^\n]+)', ai_prompt)
        
        if podios_match:
            record_str = podios_match.group(1).strip()
            
            if record_str and record_str != "Nenhum Top 8":
                for item in record_str.split(','):
                    item = item.strip().lower()
                    if not item: continue
                    
                    match = re.match(r'^(\d+)\s*[xX]\s*(.+)$', item)
                    if match:
                        qtd = int(match.group(1))
                        pos = match.group(2).strip()
                        
                        if pos == '1st': first_place += qtd
                        elif pos == '2nd': second_place += qtd
                        elif pos == '3rd': third_place += qtd
                        elif pos == '4th': fourth_place += qtd
                        elif pos in ['5th', '6th', '7th', '8th']: top_8_place += qtd
        
        tournaments_won = first_place
        made_top_cut = first_place + second_place + third_place + fourth_place + top_8_place
        
        missed_top_cut = events_played - made_top_cut
        if missed_top_cut < 0: missed_top_cut = 0

        # --- 3. INTERFACE VISUAL ---
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
                st.markdown(f"<h2 style='text-align: center; margin: 0;'>{events_played} <span style='font-size: 0.5em; color: gray;'>/ {total_eventos_globais}</span></h2>", unsafe_allow_html=True)
                st.markdown("<p style='text-align: center; color: gray; margin: 0;'>Events Played</p>", unsafe_allow_html=True)
        with t2:
            with st.container(border=True):
                st.markdown(f"<h2 style='text-align: center; margin: 0;'>{tournaments_won}</h2>", unsafe_allow_html=True)
                st.markdown("<p style='text-align: center; color: gray; margin: 0;'>Tournaments Won</p>", unsafe_allow_html=True)
        with t3:
            with st.container(border=True):
                st.markdown(f"<h2 style='text-align: center; margin: 0;'>{first_place}x</h2>", unsafe_allow_html=True)
                st.markdown("<p style='text-align: center; color: #FFD700; margin: 0;'>🥇 1st Place</p>", unsafe_allow_html=True)

        t4, t5, t6 = st.columns(3)
        with t4:
            with st.container(border=True):
                st.markdown(f"<h2 style='text-align: center; margin: 0;'>{second_place}x</h2>", unsafe_allow_html=True)
                st.markdown("<p style='text-align: center; color: #C0C0C0; margin: 0;'>🥈 2nd Place</p>", unsafe_allow_html=True)
        with t5:
            with st.container(border=True):
                st.markdown(f"<h2 style='text-align: center; margin: 0;'>{third_place}x</h2>", unsafe_allow_html=True)
                st.markdown("<p style='text-align: center; color: #CD7F32; margin: 0;'>🥉 3rd Place</p>", unsafe_allow_html=True)
        with t6:
            with st.container(border=True):
                st.markdown(f"<h2 style='text-align: center; margin: 0;'>{fourth_place}x</h2>", unsafe_allow_html=True)
                st.markdown("<p style='text-align: center; color: gray; margin: 0;'>4th Place</p>", unsafe_allow_html=True)

        t7, t8, _ = st.columns(3)
        with t7:
            with st.container(border=True):
                st.markdown(f"<h2 style='text-align: center; margin: 0;'>{top_8_place}x</h2>", unsafe_allow_html=True)
                st.markdown("<p style='text-align: center; color: gray; margin: 0;'>Top 8 (5th-8th)</p>", unsafe_allow_html=True)
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
        df_matchups = pd.DataFrame(p_data.get('matchups', []))
        
        if not df_matchups.empty:
            df_matchups['Losses'] = df_matchups['Games'] - df_matchups['Wins']
            df_matchups['Win Rate %'] = (df_matchups['Wins'] / df_matchups['Games']) * 100
            df_matchups = df_matchups[['Opponent', 'Games', 'Wins', 'Losses', 'Win Rate %', 'Win Likelihood (Elo)']]
            
            df_matchups.index += 1
            df_matchups.index.name = "#"
            
            st.dataframe(
                df_matchups, 
                use_container_width=True,
                column_config={
                    "Win Rate %": st.column_config.ProgressColumn(
                        "Win Rate %",
                        help="Barra visual da percentagem de vitórias",
                        format="%.1f %%",
                        min_value=0,
                        max_value=100,
                    )
                }
            )
        else:
            st.dataframe(df_matchups, use_container_width=True)

        st.divider()

        st.subheader("📖 Raw Match History")
        df_history = pd.DataFrame(p_data.get('raw_matches', []))
        if not df_history.empty:
            df_history.index += 1
            df_history.index.name = "#"
        st.dataframe(df_history, use_container_width=True)

        st.divider()
        st.subheader("📋 Audit Log: Torneios Analisados")
        st.markdown("Estes são os torneios provenientes do ficheiro `my_tournaments_global_versus.txt` usados para esta análise.")
        
        global_audit = db['global_versus'].get('audit_log', [])
        if global_audit:
            df_global_audit = pd.DataFrame(global_audit)
            if not df_global_audit.empty:
                df_global_audit.index += 1
                df_global_audit.index.name = "#"
            st.dataframe(df_global_audit, use_container_width=True)
        else:
            st.warning("⚠️ O Log de Torneios ainda não foi exportado para a base de dados global.")

elif page == "Contactos & Equipa":
    st.title("📞 Contactos & Organização")
    
    st.subheader("🌐 Comunidade e Redes Sociais")
    
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
    
    conteudo_org = load_communications("organizacao.txt")
    if conteudo_org:
        seccoes = conteudo_org.split("===")
        
        for seccao in seccoes:
            if seccao.strip():
                with st.container(border=True):
                    st.markdown(seccao.strip())
    else:
        st.info("Cria o ficheiro `organizacao.txt` no teu GitHub e usa `===` para separar as secções da tua equipa.")

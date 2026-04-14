import streamlit as st
import pandas as pd
import json
import base64
import os
from datetime import datetime

# ==========================================
# 0. SIMULADORES DE BASE DE DADOS E EVENTOS
# ==========================================
MOCK_DB = {
    "OneZarolho": ["Dran Sword 3-60 F", "Knight Shield 4-80 N", "Wizard Arrow 4-60 B", "Shark Edge 3-80 LF"],
    "Paparapas": ["Phoenix Wing 9-60 GF", "Cobalt Drake 4-60 B", "Leon Claw 5-60 P", "Viper Tail 5-80 O"],
    "Dexter": ["Hell Scythe 4-60 T", "Dagger 3-80 F", "Rhino Horn 5-60 O", "Phoenix Wing 9-60 R"],
    "Velos77": ["Dranzer S 3-80 T", "Leon Crest 7-60 O", "Unicorn Sting 5-60 P", "Tyranno Beat 4-70 Q"]
}

MOCK_EVENTS = {
    "Torneio de Lançamento BX": {"deck_check": False, "matching_open": True},
    "Liga Nacional - Etapa 1": {"deck_check": True, "matching_open": True},
    "Torneio de Inverno (Terminado)": {"deck_check": False, "matching_open": False}
}

DB_FILE = 'logger_db.json'

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_db(data):
    with open(DB_FILE, 'w') as f:
        json.dump(data, f, indent=4)

# ==========================================
# 1. TODAS AS FUNÇÕES 
# ==========================================
def auto_save_battle():
    db = load_db()
    b_id = st.session_state.battle_id
    snapshot = {
        "Event_Name": st.session_state.active_event, # Associa automaticamente ao evento do Lobby
        "Status": "Em Curso" if st.session_state.phase != 'match_over' else "Terminada",
        "P1_Name": st.session_state.p1_name,
        "P2_Name": st.session_state.p2_name,
        "P1_Score": st.session_state.p1_score,
        "P2_Score": st.session_state.p2_score,
        "Limit": st.session_state.limit,
        "Phase": st.session_state.phase,
        "Current_Round": st.session_state.current_round,
        "Match_Log": st.session_state.match_log,
        "P1_Active_Deck": st.session_state.get('p1_active_deck', []),
        "P2_Active_Deck": st.session_state.get('p2_active_deck', []),
        "P1_Deck_Pool": st.session_state.p1_deck_pool,
        "P2_Deck_Pool": st.session_state.p2_deck_pool
    }
    db[b_id] = snapshot
    save_db(db)

def load_battle_into_memory(b_id, data):
    st.session_state.battle_id = b_id
    for key, value in data.items():
        st.session_state[key.lower()] = value
    st.session_state.phase = data["Phase"]

def register_result(winner_name, finish_type, points, bey_winner, bey_loser):
    st.session_state.history.append({
        'p1_score': st.session_state.p1_score, 'p2_score': st.session_state.p2_score,
        'current_round': st.session_state.current_round, 'phase': st.session_state.phase, 'log_len': len(st.session_state.match_log)
    })

    if winner_name == st.session_state.p1_name: st.session_state.p1_score += points
    else: st.session_state.p2_score += points
        
    st.session_state.match_log.append(f"⚔️ {winner_name} ({bey_winner}) venceu por {finish_type} (+{points}) contra {bey_loser}")

    if st.session_state.p1_score >= st.session_state.limit or st.session_state.p2_score >= st.session_state.limit:
        st.session_state.phase = 'match_over'
    else:
        st.session_state.current_round += 1
        if st.session_state.current_round > 2:
            st.session_state.phase = 'ordering'
            
    auto_save_battle()

def undo_last_action():
    if st.session_state.history:
        last = st.session_state.history.pop()
        st.session_state.p1_score = last['p1_score']
        st.session_state.p2_score = last['p2_score']
        st.session_state.current_round = last['current_round']
        st.session_state.phase = last['phase']
        st.session_state.match_log = st.session_state.match_log[:last['log_len']]
        auto_save_battle()

def auto_fill_p1():
    pool, s1, s2, s3 = st.session_state.p1_deck_pool, st.session_state.p1_1, st.session_state.p1_2, st.session_state.p1_3
    selected = [s for s in [s1, s2, s3] if s is not None]
    if len(selected) == 2 and len(set(selected)) == 2:
        rem = [c for c in pool if c not in selected][0]
        if s1 is None: st.session_state.p1_1 = rem
        if s2 is None: st.session_state.p1_2 = rem
        if s3 is None: st.session_state.p1_3 = rem

def auto_fill_p2():
    pool, s1, s2, s3 = st.session_state.p2_deck_pool, st.session_state.p2_1, st.session_state.p2_2, st.session_state.p2_3
    selected = [s for s in [s1, s2, s3] if s is not None]
    if len(selected) == 2 and len(set(selected)) == 2:
        rem = [c for c in pool if c not in selected][0]
        if s1 is None: st.session_state.p2_1 = rem
        if s2 is None: st.session_state.p2_2 = rem
        if s3 is None: st.session_state.p2_3 = rem

def archive_match_to_gsheets(event_name, b_id, p1, p2, p1_score, p2_score, log):
    data_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_formatado = " | ".join(log)
    st.success(f"✅ Partida do evento '{event_name}' arquivada no Google Sheets com sucesso!")

# ==========================================
# 2. INICIALIZAÇÃO
# ==========================================
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.phase = 'login'

if 'active_event' not in st.session_state:
    st.session_state.active_event = None

if 'history' not in st.session_state:
    st.session_state.history = []

# ==========================================
# CABEÇALHO COM LOGO DA BBPT (MÉTODO HTML)
# ==========================================
logo_path = "logo.png" if os.path.exists("logo.png") else "../logo.png"

if os.path.exists(logo_path):
    # Lemos a imagem e convertemos para base64
    with open(logo_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode()
    
    # Injetamos HTML para colar a imagem ao texto (margin-right controla a distância)
    st.markdown(
        f"""
        <div style="display: flex; align-items: center; margin-bottom: 20px;">
            <img src="data:image/png;base64,{encoded_string}" width="45" style="margin-right: 15px;">
            <h1 style="margin: 0; padding: 0; font-size: 2.2rem;">BBPT Admin - Battle Logger</h1>
        </div>
        """, 
        unsafe_allow_html=True
    )
else:
    # Plano B caso ele não encontre a imagem
    st.title("🛡️ BBPT Admin - Battle Logger")

# ==========================================
# FASE 0: LOGIN
# ==========================================
if st.session_state.phase == 'login':
    st.markdown("### Área Restrita de Organização")
    pwd = st.text_input("Password de Acesso:", type="password")
    
    if st.button("Entrar", type="primary"):
        if pwd == "admin123":
            st.session_state.logged_in = True
            st.session_state.phase = 'event_selection' # Agora vai para o seletor de eventos primeiro!
            st.rerun()
        else:
            st.error("Password Incorreta.")

# ==========================================
# FASE 0.25: SELEÇÃO DE EVENTO (NOVO)
# ==========================================
elif st.session_state.phase == 'event_selection' and st.session_state.logged_in:
    st.markdown("### 📅 Selecionar Evento Ativo")
    st.info("Escolhe o evento que estás a organizar. Todas as batalhas serão indexadas a ele.")
    
    eventos_abertos = [evt for evt, dados in MOCK_EVENTS.items() if dados.get("matching_open", False)]
    
    if not eventos_abertos:
        st.warning("Não há eventos abertos para Matching de momento.")
    else:
        event_name = st.selectbox("📍 Evento:", options=eventos_abertos, index=None, placeholder="Escolhe um evento...")
        if st.button("Entrar no Lobby do Evento", type="primary", use_container_width=True):
            if event_name:
                st.session_state.active_event = event_name
                st.session_state.phase = 'lobby'
                st.rerun()
            else:
                st.error("⚠️ Seleciona um evento para continuar!")

# ==========================================
# FASE 0.5: O LOBBY (AGORA FOCADO NO EVENTO)
# ==========================================
elif st.session_state.phase == 'lobby' and st.session_state.logged_in:
    
    # Cabeçalho do Evento com botão de troca
    col_t1, col_t2 = st.columns([3, 1])
    with col_t1:
        st.markdown(f"### 🏟️ Lobby: **{st.session_state.active_event}**")
    with col_t2:
        if st.button("🔄 Mudar Evento", use_container_width=True):
            st.session_state.active_event = None
            st.session_state.phase = 'event_selection'
            st.rerun()
            
    st.write("")

    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.info("Queres iniciar um novo jogo?")
        if st.button("➕ Criar Nova Batalha", use_container_width=True, type="primary"):
            st.session_state.phase = 'setup'
            st.rerun()
            
    with col2:
        st.warning("Retomar batalha pendente:")
        db = load_db()
        # Filtra SÓ as batalhas em curso DESTE evento
        batalhas_ativas = {k: v for k, v in db.items() if v["Status"] == "Em Curso" and v.get("Event_Name") == st.session_state.active_event}
        
        if batalhas_ativas:
            opcoes = {k: f"{v['P1_Name']} vs {v['P2_Name']} (Score: {v['P1_Score']}-{v['P2_Score']})" for k, v in batalhas_ativas.items()}
            escolha = st.selectbox("Selecionar Batalha em Curso:", options=list(opcoes.keys()), format_func=lambda x: opcoes[x])
            
            if st.button("▶️ Retomar Batalha Selecionada", use_container_width=True):
                load_battle_into_memory(escolha, db[escolha])
                st.rerun()
        else:
            st.success("Nenhuma batalha ativa neste evento.")

    # LISTA DE BATALHAS CONCLUÍDAS DESTE EVENTO
    st.divider()
    st.markdown("### 🏆 Batalhas Concluídas (Arquivo Local)")
    
    # Filtra SÓ as batalhas terminadas DESTE evento
    batalhas_concluidas = {k: v for k, v in db.items() if v["Status"] == "Terminada" and v.get("Event_Name") == st.session_state.active_event}
    
    if batalhas_concluidas:
        for b_id, b_data in batalhas_concluidas.items():
            c_info, c_del, c_space = st.columns([4, 2, 4])
            with c_info:
                st.markdown(f"#### 👤 {b_data['P1_Name']} vs {b_data['P2_Name']}")
                st.caption(f"Placar Final: **{b_data['P1_Score']} - {b_data['P2_Score']}**") # A tag do evento saiu porque o evento já é óbvio
            with c_del:
                st.write("") 
                if st.session_state.get(f"confirm_del_{b_id}"):
                    c_yes, c_no = st.columns(2)
                    if c_yes.button("✔️", key=f"yes_{b_id}", help="Confirmar Eliminação"):
                        del db[b_id]
                        save_db(db)
                        st.session_state[f"confirm_del_{b_id}"] = False
                        st.rerun()
                    if c_no.button("❌", key=f"no_{b_id}", help="Cancelar"):
                        st.session_state[f"confirm_del_{b_id}"] = False
                        st.rerun()
                else:
                    if st.button("🗑️ Eliminar", key=f"del_{b_id}", use_container_width=True):
                        st.session_state[f"confirm_del_{b_id}"] = True
                        st.rerun()
            st.write("") 
    else:
        st.info(f"Ainda não há resultados finais para '{st.session_state.active_event}'.")

# ==========================================
# FASE 1: SETUP E DRAFTING (DIRETO PARA JOGADORES)
# ==========================================
elif st.session_state.phase == 'setup':
    st.markdown(f"### 1. Configuração da Partida")
    st.caption(f"A indexar a: **{st.session_state.active_event}**")
    st.write("")
    
    lista_jogadores = list(MOCK_DB.keys())
    
    c1, c2 = st.columns(2)
    with c1:
        p1_name = st.selectbox("Jogador 1:", options=lista_jogadores, index=None)
        p1_pool = MOCK_DB.get(p1_name, []) if p1_name else []
        p1_draft = st.multiselect(f"Combos P1:", p1_pool, max_selections=3, disabled=not p1_name)

    with c2:
        p2_name = st.selectbox("Jogador 2:", options=lista_jogadores, index=None)
        p2_pool = MOCK_DB.get(p2_name, []) if p2_name else []
        p2_draft = st.multiselect(f"Combos P2:", p2_pool, max_selections=3, disabled=not p2_name)

    limit = st.radio("Limite de Pontos:", [4, 5, 7], horizontal=True)

    if st.button("▶️ Iniciar Batalha", use_container_width=True, type="primary"):
        if p1_name and p2_name and p1_name == p2_name:
            st.error("⚠️ Um jogador não pode batalhar contra si próprio!")
        elif p1_name and p2_name and len(p1_draft) == 3 and len(p2_draft) == 3:
            st.session_state.p1_name = p1_name
            st.session_state.p2_name = p2_name
            st.session_state.p1_deck_pool = p1_draft
            st.session_state.p2_deck_pool = p2_draft
            st.session_state.limit = limit
            st.session_state.p1_score = 0
            st.session_state.p2_score = 0
            st.session_state.current_round = 0
            st.session_state.match_log = []
            
            timestamp = datetime.now().strftime("%H%M%S")
            st.session_state.battle_id = f"{p1_name}_{p2_name}_{timestamp}"
            
            st.session_state.phase = 'ordering'
            auto_save_battle() 
            st.rerun()
        else:
            st.warning("⚠️ Seleciona os dois jogadores e exatamente 3 combos para cada um!")

# ==========================================
# FASE 2: ORDERING / RESHUFFLE
# ==========================================
elif st.session_state.phase == 'ordering':
    st.markdown(f"### 🔄 Seleção de Ordem")
    st.info("💡 Dica: Ao escolheres 2 combos, o 3º preenche automaticamente.")
    
    if st.session_state.history:
        st.button("↩️ OOPS! Desfazer Última Ação", use_container_width=True, on_click=undo_last_action)
    
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"### 🟢 {st.session_state.p1_name}")
        p1_1 = st.selectbox("1º Beyblade (P1)", st.session_state.p1_deck_pool, index=None, key="p1_1", on_change=auto_fill_p1)
        p1_2 = st.selectbox("2º Beyblade (P1)", st.session_state.p1_deck_pool, index=None, key="p1_2", on_change=auto_fill_p1)
        p1_3 = st.selectbox("3º Beyblade (P1)", st.session_state.p1_deck_pool, index=None, key="p1_3", on_change=auto_fill_p1)
        
    with c2:
        st.markdown(f"### 🔴 {st.session_state.p2_name}")
        p2_1 = st.selectbox("1º Beyblade (P2)", st.session_state.p2_deck_pool, index=None, key="p2_1", on_change=auto_fill_p2)
        p2_2 = st.selectbox("2º Beyblade (P2)", st.session_state.p2_deck_pool, index=None, key="p2_2", on_change=auto_fill_p2)
        p2_3 = st.selectbox("3º Beyblade (P2)", st.session_state.p2_deck_pool, index=None, key="p2_3", on_change=auto_fill_p2)

    st.write("")
    if st.button("⚔️ Entrar na Arena!", use_container_width=True, type="primary"):
        p1_choices = [p1_1, p1_2, p1_3]
        p2_choices = [p2_1, p2_2, p2_3]
        
        if None in p1_choices or None in p2_choices:
            st.error("⚠️ Preenche os 3 lugares!")
        elif len(set(p1_choices)) == 3 and len(set(p2_choices)) == 3:
            st.session_state.p1_active_deck = p1_choices
            st.session_state.p2_active_deck = p2_choices
            st.session_state.current_round = 0 
            st.session_state.phase = 'battle'
            
            for k in ['p1_1', 'p1_2', 'p1_3', 'p2_1', 'p2_2', 'p2_3']: del st.session_state[k]
            auto_save_battle() 
            st.rerun()
        else:
            st.error("⚠️ Encontrámos Beys repetidos!")

# ==========================================
# FASE 3: BATTLE LOOP
# ==========================================
elif st.session_state.phase == 'battle':
    st.markdown("""<style>div.stButton > button {height: 90px !important; font-size: 24px !important; font-weight: 800 !important; border-radius: 12px !important; white-space: normal !important; margin-bottom: 5px !important;} div.stButton > button p {font-size: 22px !important;}</style>""", unsafe_allow_html=True)

    r_idx = st.session_state.current_round
    bey_p1 = st.session_state.p1_active_deck[r_idx]
    bey_p2 = st.session_state.p2_active_deck[r_idx]
    
    c1, c2, c3 = st.columns([4, 1, 4])
    with c1:
        st.markdown(f"<h1 style='text-align: center; font-size: 3rem;'>{st.session_state.p1_name}</h1>", unsafe_allow_html=True)
        st.markdown(f"<h1 style='text-align: center; font-size: 6rem; color: #4CAF50; line-height: 1.0;'>{st.session_state.p1_score}</h1>", unsafe_allow_html=True)
        st.markdown(f"<h3 style='text-align: center; color: gray;'>🛡️ {bey_p1}</h3>", unsafe_allow_html=True)
    with c2:
        st.write(""); st.write(""); st.write("")
        st.markdown("<h1 style='text-align: center; font-size: 2rem; color: gray;'>VS</h1>", unsafe_allow_html=True)
    with c3:
        st.markdown(f"<h1 style='text-align: center; font-size: 3rem;'>{st.session_state.p2_name}</h1>", unsafe_allow_html=True)
        st.markdown(f"<h1 style='text-align: center; font-size: 6rem; color: #FF4B4B; line-height: 1.0;'>{st.session_state.p2_score}</h1>", unsafe_allow_html=True)
        st.markdown(f"<h3 style='text-align: center; color: gray;'>🛡️ {bey_p2}</h3>", unsafe_allow_html=True)

    st.divider()
    
    btn_col1, empty_col, btn_col2 = st.columns([4, 1, 4])
    with btn_col1:
        st.button("🌀 Spin (+1)", key="p1_spin", use_container_width=True, on_click=register_result, args=(st.session_state.p1_name, "Spin Finish", 1, bey_p1, bey_p2))
        st.button("💨 Over (+2)", key="p1_over", use_container_width=True, on_click=register_result, args=(st.session_state.p1_name, "Over Finish", 2, bey_p1, bey_p2))
        st.button("💥 Burst (+2)", key="p1_burst", use_container_width=True, on_click=register_result, args=(st.session_state.p1_name, "Burst Finish", 2, bey_p1, bey_p2))
        st.button("⚡ X-Treme (+3)", key="p1_extreme", use_container_width=True, type="primary", on_click=register_result, args=(st.session_state.p1_name, "X-Treme Finish", 3, bey_p1, bey_p2))

    with btn_col2:
        st.button("🌀 Spin (+1)", key="p2_spin", use_container_width=True, on_click=register_result, args=(st.session_state.p2_name, "Spin Finish", 1, bey_p2, bey_p1))
        st.button("💨 Over (+2)", key="p2_over", use_container_width=True, on_click=register_result, args=(st.session_state.p2_name, "Over Finish", 2, bey_p2, bey_p1))
        st.button("💥 Burst (+2)", key="p2_burst", use_container_width=True, on_click=register_result, args=(st.session_state.p2_name, "Burst Finish", 2, bey_p2, bey_p1))
        st.button("⚡ X-Treme (+3)", key="p2_extreme", use_container_width=True, type="primary", on_click=register_result, args=(st.session_state.p2_name, "X-Treme Finish", 3, bey_p2, bey_p1))
        
    st.write("")
    aux_col1, aux_col2, aux_col3 = st.columns([1, 2, 1])
    with aux_col2:
        if st.session_state.history:
            st.button("↩️ OOPS! Desfazer Última Ação", use_container_width=True, on_click=undo_last_action)

# ==========================================
# FASE 4: MATCH OVER
# ==========================================
elif st.session_state.phase == 'match_over':
    st.balloons()
    st.success("🏆 BATALHA TERMINADA!")
    st.markdown(f"<h1 style='text-align: center; font-size: 5rem;'>{st.session_state.p1_score} - {st.session_state.p2_score}</h1>", unsafe_allow_html=True)
    
    if st.session_state.p1_score > st.session_state.p2_score:
        st.markdown(f"<h2 style='text-align: center;'>Vencedor: 👑 {st.session_state.p1_name}</h2>", unsafe_allow_html=True)
    else:
        st.markdown(f"<h2 style='text-align: center;'>Vencedor: 👑 {st.session_state.p2_name}</h2>", unsafe_allow_html=True)
        
    st.write("")
    
    if 'arquivado' not in st.session_state:
        archive_match_to_gsheets(
            st.session_state.active_event,
            st.session_state.battle_id,
            st.session_state.p1_name, 
            st.session_state.p2_name,
            st.session_state.p1_score,
            st.session_state.p2_score,
            st.session_state.match_log
        )
        st.session_state.arquivado = True
        
        db = load_db()
        if st.session_state.battle_id in db:
            db[st.session_state.battle_id]["Status"] = "Terminada" 
            save_db(db)

    col_undo, col_new = st.columns(2)
    with col_undo:
        if st.session_state.history:
            if st.button("↩️ Desfazer Último Ponto", use_container_width=True):
                del st.session_state['arquivado']
                undo_last_action()
                st.rerun()
            
    with col_new:
        if st.button("🔄 Voltar ao Lobby do Evento", use_container_width=True, type="primary"):
            # 1. Guarda o nome do evento ANTES de limpar a memória!
            evento_atual = st.session_state.active_event
            
            # 2. Agora sim, limpa tudo para não haver lixo
            st.session_state.clear()
            
            # 3. Restaura apenas o essencial para voltar ao Lobby
            st.session_state.logged_in = True
            st.session_state.active_event = evento_atual
            st.session_state.phase = 'lobby'
            st.rerun()
            
    st.divider()
    st.markdown("### Match Log Oficial:")
    df_log = pd.DataFrame(st.session_state.match_log, columns=["Ação Registada"])
    st.dataframe(df_log, use_container_width=True)
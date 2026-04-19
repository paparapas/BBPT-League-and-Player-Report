import streamlit as st
import pandas as pd
import json
import base64
import os
import time
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

# 🛑 1. FORÇAR O MODO "WIDE" E REMOVER ESPAÇOS BRANCOS GIGANTES 🛑
st.set_page_config(page_title="Battle Logger", layout="wide", initial_sidebar_state="collapsed")

# 👇 COLOCA AQUI PARA TESTAR 👇
st.write("Teste de Atualização")

st.markdown("""
<style>
    /* 1. ELIMINAR A BARRA SUPERIOR DO STREAMLIT */
    header[data-testid="stHeader"] {
        display: none !important;
    }
    
    /* 2. Ajustar a margem para o conteúdo não bater na "notch"/bateria do telemóvel */
    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 0.5rem !important;
        max-width: 100% !important;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 0. LIGAÇÃO REAL AO GOOGLE SHEETS E BASE DE DADOS
# ==========================================
DB_FILE = 'logger_db.json'

def get_gspread_client():
    """Lê os secrets do Streamlit e autentica no Google."""
    scopes = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]
    creds_dict = dict(st.secrets["GCP_CREDENTIALS"])
    creds = Credentials.from_service_account_info(
        creds_dict, 
        scopes=scopes
    )
    return gspread.authorize(creds)

@st.cache_data(ttl=30) 
def get_all_events_info():
    """Lê a aba Config para o evento atual e a Folha1 para o histórico."""
    try:
        client = get_gspread_client()
        
        # 1. Ler o Evento Atual da aba Config
        config_sheet = client.open_by_url(st.secrets["SHEET_URL"]).worksheet("Config")
        config_records = config_sheet.get_all_records()
        
        current_event_name = None
        deck_check_is_open = True
        
        if config_records:
            row = config_records[0] # A Config só tem 1 linha
            current_event_name = str(row.get("event_name", "")).strip()
            raw_val = row.get("is_open", "")
            if isinstance(raw_val, bool):
                deck_check_is_open = raw_val
            else:
                deck_check_is_open = str(raw_val).strip().upper() in ["TRUE", "VERDADEIRO", "1", "SIM", "YES"]
                
        events = {}
        
        # Se o Deck Check está ABERTO, as batalhas estão FECHADAS (e vice-versa)
        if current_event_name:
            events[current_event_name] = {
                "matching_open": not deck_check_is_open, 
                "is_current": True,
                "deck_check_status": deck_check_is_open
            }
            
        # 2. Ler a Folha1 para encontrar todos os eventos antigos (Histórico)
        folha1_sheet = client.open_by_url(st.secrets["SHEET_URL"]).worksheet("Folha1")
        folha1_records = folha1_sheet.get_all_records()
        
        for row in folha1_records:
            ev_name = str(row.get("Event_Name", "")).strip()
            if ev_name and ev_name not in events:
                # Eventos antigos entram na lista, mas com batalhas fechadas por defeito
                events[ev_name] = {
                    "matching_open": False, 
                    "is_current": False,
                    "deck_check_status": False
                }
                
        return events
    except Exception as e:
        st.error(f"⚠️ Erro ao carregar Eventos do Google Sheets: {e}")
        return {}

@st.cache_data(ttl=30)
def get_real_players_and_combos(active_event_name):
    try:
        client = get_gspread_client()
        sheet = client.open_by_url(st.secrets["SHEET_URL"]).worksheet("Folha1")
        records = sheet.get_all_records()
        
        db = {}
        for row in records:
            if str(row.get("Event_Name", "")).strip() == active_event_name:
                player = str(row.get("Player", "")).strip()
                if player:
                    combos = [
                        str(row.get("Combo_1", "")).strip(),
                        str(row.get("Combo_2", "")).strip(),
                        str(row.get("Combo_3", "")).strip(),
                        str(row.get("Combo_4", "")).strip()
                    ]
                    db[player] = [c for c in combos if c]
        return db
    except Exception as e:
        st.error(f"⚠️ Erro ao carregar os Deck Checks (Folha1): {e}")
        return {}

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_db(data):
    with open(DB_FILE, 'w') as f:
        json.dump(data, f, indent=4)

# ==========================================
# 1. TODAS AS FUNÇÕES DE GESTÃO DA PARTIDA
# ==========================================
def auto_save_battle():
    db = load_db()
    b_id = st.session_state.battle_id
    snapshot = {
        "Event_Name": st.session_state.active_event,
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

# --- ARQUIVO REAL NO GOOGLE SHEETS ---
def archive_match_to_gsheets(event_name, b_id, p1, p2, p1_score, p2_score, log):
    try:
        client = get_gspread_client()
        sheet = client.open_by_url(st.secrets["SHEET_URL"]).worksheet("Battle_Logs")
        
        data_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_formatado = " | ".join(log)
        placar = f"{p1_score}-{p2_score}"
        
        sheet.append_row([
            data_hora, event_name, b_id, p1, p2, placar, log_formatado
        ])
        st.success(f"✅ Partida do evento '{event_name}' arquivada no Google Sheets com sucesso!")
    except Exception as e:
        st.error(f"❌ Erro ao comunicar com a Base de Dados na Nuvem: {e}")

# 👇 NOVA FUNÇÃO: Puxar do Google Sheets e atualizar o JSON local 👇
def sync_from_gsheets(event_name):
    try:
        client = get_gspread_client()
        sheet = client.open_by_url(st.secrets["SHEET_URL"]).worksheet("Battle_Logs")
        values = sheet.get_all_values()
        
        db = load_db()
        
        # 1. Limpar TODAS as batalhas "Terminada" para este evento no ficheiro local
        keys_to_delete = [k for k, v in db.items() if v.get("Event_Name") == event_name and v.get("Status") == "Terminada"]
        for k in keys_to_delete:
            del db[k]
            
        count = 0
        if len(values) > 1:
            for row in values[1:]:
                if len(row) >= 7 and str(row[1]).strip() == event_name:
                    b_id = str(row[2]).strip()
                    if not b_id: b_id = f"sync_{datetime.now().timestamp()}_{count}"
                    
                    placar = str(row[5]).strip().split('-')
                    p1_s = int(placar[0]) if len(placar) == 2 and placar[0].strip().isdigit() else 0
                    p2_s = int(placar[1]) if len(placar) == 2 and placar[1].strip().isdigit() else 0
                    
                    log_raw = str(row[6])
                    match_log = log_raw.split(" | ") if log_raw else []
                    
                    db[b_id] = {
                        "Event_Name": event_name,
                        "Status": "Terminada",
                        "P1_Name": str(row[3]).strip(),
                        "P2_Name": str(row[4]).strip(),
                        "P1_Score": p1_s,
                        "P2_Score": p2_s,
                        "Match_Log": match_log,
                        "Phase": "match_over"
                    }
                    count += 1
        
        save_db(db)
        return True, count
    except Exception as e:
        return False, str(e)

# ==========================================
# 2. INICIALIZAÇÃO E CABEÇALHO
# ==========================================
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.phase = 'login'

if 'active_event' not in st.session_state:
    st.session_state.active_event = None

if 'history' not in st.session_state:
    st.session_state.history = []

logo_path = "logo.png" if os.path.exists("logo.png") else "../logo.png"

if os.path.exists(logo_path):
    with open(logo_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode()
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
            st.session_state.phase = 'event_selection'
            st.rerun()
        else:
            st.error("Password Incorreta.")

# ==========================================
# FASE 0.25: SELEÇÃO DE EVENTO 
# ==========================================
elif st.session_state.phase == 'event_selection' and st.session_state.logged_in:
    st.markdown("### 📅 Selecionar Evento Ativo")
    st.info("Escolhe o evento atual ou consulta o histórico de eventos anteriores.")
    
    all_events = get_all_events_info()
    
    if not all_events:
        st.warning("Não há eventos na folha 'Config' nem histórico na 'Folha1'.")
    else:
        lista_eventos = list(all_events.keys())
        event_name = st.selectbox("📍 Evento:", options=lista_eventos, index=None, placeholder="Escolhe um evento...")
        
        if st.button("Entrar no Lobby do Evento", type="primary", use_container_width=True):
            if event_name:
                st.session_state.active_event = event_name
                st.session_state.phase = 'lobby'
                st.rerun()
            else:
                st.error("⚠️ Seleciona um evento para continuar!")

# ==========================================
# FASE 0.5: O LOBBY
# ==========================================
elif st.session_state.phase == 'lobby' and st.session_state.logged_in:
    
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
        all_events = get_all_events_info()
        event_data = all_events.get(st.session_state.active_event, {})
        
        is_matching_open = event_data.get("matching_open", False)
        is_current = event_data.get("is_current", False)
        
        if is_matching_open:
            st.info("O Deck Check fechou. Podes iniciar batalhas!")
            if st.button("➕ Criar Nova Batalha", use_container_width=True, type="primary"):
                st.session_state.phase = 'setup'
                st.rerun()
        else:
            if is_current:
                st.warning("🔒 Batalhas Bloqueadas")
                st.caption("O Deck Check ainda está ABERTO. Para iniciar batalhas, o organizador tem de ir à folha 'Config' e mudar a coluna is_open para FALSE.")
            else:
                st.warning("🗄️ Evento Arquivado")
                st.caption("Este torneio já terminou. Estás em modo de consulta do histórico.")
            
    with col2:
        st.warning("Retomar batalha pendente:")
        db = load_db()
        batalhas_ativas = {k: v for k, v in db.items() if v["Status"] == "Em Curso" and v.get("Event_Name") == st.session_state.active_event}
        
        if batalhas_ativas:
            opcoes = {k: f"{v['P1_Name']} vs {v['P2_Name']} (Score: {v['P1_Score']}-{v['P2_Score']})" for k, v in batalhas_ativas.items()}
            escolha = st.selectbox("Selecionar Batalha em Curso:", options=list(opcoes.keys()), format_func=lambda x: opcoes[x])
            
            if st.button("▶️ Retomar Batalha Selecionada", use_container_width=True):
                load_battle_into_memory(escolha, db[escolha])
                st.rerun()
        else:
            st.success("Nenhuma batalha ativa neste evento.")

    st.divider()
    st.markdown("### 🏆 Batalhas Concluídas (Arquivo Local)")
    
    # 👇 O BOTÃO DE RECUPERAÇÃO ESTÁ AQUI 👇
    if st.button("☁️ Recuperar Histórico do Google Sheets", help="Clica aqui para repor as batalhas concluídas puxando a informação da nuvem.", use_container_width=True):
        with st.spinner("A procurar na nuvem e a reescrever o ficheiro local..."):
            success, msg = sync_from_gsheets(st.session_state.active_event)
            if success:
                st.success(f"✅ Sincronização perfeita! Foram recuperadas {msg} batalhas para o lobby.")
                time.sleep(1.5)
                st.rerun()
            else:
                st.error(f"❌ Erro ao sincronizar: {msg}")
    
    db = load_db() 
    batalhas_concluidas = {k: v for k, v in db.items() if v["Status"] == "Terminada" and v.get("Event_Name") == st.session_state.active_event}
    
    if batalhas_concluidas:
        for b_id, b_data in batalhas_concluidas.items():
            c_info, c_del, c_space = st.columns([4, 2, 4])
            with c_info:
                st.markdown(f"#### 👤 {b_data['P1_Name']} vs {b_data['P2_Name']}")
                st.caption(f"Placar Final: **{b_data['P1_Score']} - {b_data['P2_Score']}**")
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
# FASE 1: SETUP E DRAFTING
# ==========================================
elif st.session_state.phase == 'setup':
    st.markdown(f"### 1. Configuração da Partida")
    st.caption(f"A indexar a: **{st.session_state.active_event}**")
    st.write("")
    
    current_db = get_real_players_and_combos(st.session_state.active_event)
    lista_jogadores = list(current_db.keys())
    
    if not lista_jogadores:
        st.warning(f"Ainda não há jogadores inscritos no evento '{st.session_state.active_event}' na Folha1.")
        if st.button("Voltar ao Lobby"):
            st.session_state.phase = 'lobby'
            st.rerun()
    else:
        c1, c2 = st.columns(2)
        with c1:
            p1_name = st.selectbox("Jogador 1:", options=lista_jogadores, index=None)
            p1_pool = current_db.get(p1_name, []) if p1_name else []
            st.markdown("**Ordem Inicial (Escolhe 3 de 4):**")
            p1_1 = st.selectbox("1º Beyblade (P1)", p1_pool, index=None, key="setup_p1_1", disabled=not p1_name)
            p1_2 = st.selectbox("2º Beyblade (P1)", p1_pool, index=None, key="setup_p1_2", disabled=not p1_name)
            p1_3 = st.selectbox("3º Beyblade (P1)", p1_pool, index=None, key="setup_p1_3", disabled=not p1_name)
            p1_draft = [p1_1, p1_2, p1_3]

        with c2:
            p2_name = st.selectbox("Jogador 2:", options=lista_jogadores, index=None)
            p2_pool = current_db.get(p2_name, []) if p2_name else []
            st.markdown("**Ordem Inicial (Escolhe 3 de 4):**")
            p2_1 = st.selectbox("1º Beyblade (P2)", p2_pool, index=None, key="setup_p2_1", disabled=not p2_name)
            p2_2 = st.selectbox("2º Beyblade (P2)", p2_pool, index=None, key="setup_p2_2", disabled=not p2_name)
            p2_3 = st.selectbox("3º Beyblade (P2)", p2_pool, index=None, key="setup_p2_3", disabled=not p2_name)
            p2_draft = [p2_1, p2_2, p2_3]

        limit = st.radio("Limite de Pontos:", [4, 5, 7], horizontal=True)

        st.write("")
        col_back, col
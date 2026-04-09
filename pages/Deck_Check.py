import streamlit as st
import pandas as pd
import json
import os
import re
import difflib
from datetime import datetime
import logging
import requests
import base64
import gspread
from google.oauth2.service_account import Credentials
from st_keyup import st_keyup

# ==========================================
# CONFIGURAÇÃO DE LOGS E PÁGINA
# ==========================================
logging.basicConfig(level=logging.ERROR, format='%(asctime)s [%(levelname)s] %(message)s')

DATASET_PARTS = "Dataset_BeybladeParts.xlsx"
DB_MASTER = "bbpt_master_db.json"
ADMIN_PASSWORD = "bbpt-paparapas" 

# ==========================================
# INTEGRAÇÃO CLOUD: GOOGLE SHEETS E IMGBB
# ==========================================
@st.cache_resource
def get_gsheet_client():
    scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    creds_dict = dict(st.secrets["GCP_CREDENTIALS"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    return gspread.authorize(creds)

def get_sheet_id():
    url = st.secrets["SHEET_URL"]
    return url.split("/d/")[1].split("/")[0] if "/d/" in url else url

# --- LEITURA COM CACHE ---
@st.cache_data(ttl=15)
def get_event_status_cached():
    try:
        client = get_gsheet_client()
        sheet = client.open_by_key(get_sheet_id())
        try: ws_cfg = sheet.worksheet("Config")
        except gspread.exceptions.WorksheetNotFound:
            ws_cfg = sheet.add_worksheet(title="Config", rows="2", cols="2")
            ws_cfg.update(range_name="A1:B2", values=[["is_open", "event_name"], ["FALSE", ""]])
        vals = ws_cfg.get_all_values()
        if len(vals) > 1: return {"is_open": vals[1][0] == "TRUE", "event_name": vals[1][1]}
        return {"is_open": False, "event_name": ""}
    except: return {"is_open": False, "event_name": ""}

@st.cache_data(ttl=30)
def get_all_records_cached(event_name):
    try:
        client = get_gsheet_client()
        sheet = client.open_by_key(get_sheet_id())
        try: ws = sheet.worksheet("Página1")
        except:
            try: ws = sheet.worksheet("Sheet1")
            except: ws = sheet.get_worksheet(0)
        return [r for r in ws.get_all_records() if r.get("Event_Name") == event_name]
    except: return []

@st.cache_data(ttl=60)
def get_past_events_list():
    try:
        client = get_gsheet_client()
        sheet = client.open_by_key(get_sheet_id())
        try: ws = sheet.worksheet("Página1")
        except:
            try: ws = sheet.worksheet("Sheet1")
            except: ws = sheet.get_worksheet(0)
        col_events = ws.col_values(2)[1:]
        return sorted(list(set([e for e in col_events if e.strip()])))
    except: return []

# --- ESCRITA ---
def set_event_status(is_open, event_name=""):
    client = get_gsheet_client()
    sheet = client.open_by_key(get_sheet_id())
    try: ws_cfg = sheet.worksheet("Config")
    except: ws_cfg = sheet.add_worksheet(title="Config", rows="2", cols="2")
    status_str = "TRUE" if is_open else "FALSE"
    ws_cfg.update(range_name="A2:B2", values=[[status_str, event_name]])
    st.cache_data.clear()

def upload_to_imgbb(image_file):
    url = "https://api.imgbb.com/1/upload"
    res = requests.post(url, data={"key": st.secrets["IMGBB_API_KEY"], "image": base64.b64encode(image_file.getvalue()).decode("utf-8")})
    if res.status_code == 200: return res.json()["data"]["url"]
    raise Exception("Erro ImgBB")

def save_submission_cloud(player_name, combos, img_file, event_name):
    img_url = upload_to_imgbb(img_file)
    c_strs = []
    for c in combos:
        if c['type'] == 'Standard (BX / UX)': c_strs.append(f"{c.get('main_blade')} | {c.get('ratchet')} | {c.get('bit')}")
        elif c['type'] == 'CX': c_strs.append(f"{c.get('lock_chip')} | {c.get('main_blade')} | {c.get('assist_blade')} | {c.get('ratchet')} | {c.get('bit')}")
        else: c_strs.append(f"{c.get('lock_chip')} | {c.get('over_blade')} | {c.get('metal_blade')} | {c.get('assist_blade')} | {c.get('ratchet')} | {c.get('bit')}")
    while len(c_strs) < 4: c_strs.append("")
    client = get_gsheet_client()
    sheet = client.open_by_key(get_sheet_id())
    try: ws = sheet.worksheet("Página1")
    except:
        try: ws = sheet.worksheet("Sheet1")
        except: ws = sheet.get_worksheet(0)
    ws.append_row([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), event_name, player_name, c_strs[0], c_strs[1], c_strs[2], c_strs[3], img_url])
    st.cache_data.clear()

# ==========================================
# LÓGICA DE PEÇAS E ALGORITMOS
# ==========================================
if "num_combos" not in st.session_state: st.session_state.num_combos = 3
if "smart_val" not in st.session_state: st.session_state.smart_val = ""
if "keyup_key" not in st.session_state: st.session_state.keyup_key = 0

for i in range(4):
    for k in ["type", "main_blade", "ratchet", "bit", "lock_chip", "assist_blade", "metal_blade", "over_blade"]:
        if f"c_{i}_{k}" not in st.session_state: st.session_state[f"c_{i}_{k}"] = "Standard (BX / UX)" if k == "type" else "--"

@st.cache_data
def load_parts():
    try:
        xls = pd.read_excel(DATASET_PARTS, sheet_name=None)
        alias_map = {}
        def get_clean_list(sheet_name):
            if sheet_name not in xls: return []
            df = xls[sheet_name]
            if sheet_name == 'Bits' and len(df.columns) > 1:
                main_vals = []
                if "Unnamed" not in str(df.columns[0]): main_vals.append(str(df.columns[0]))
                main_vals.extend(df.iloc[:, 0].tolist())
                for _, row in df.iterrows():
                    main_p = str(row.iloc[0]).strip()
                    if pd.isna(main_p) or main_p in ['-', '', 'nan']: continue
                    for val in row.iloc[1:]:
                        if pd.notna(val):
                            for sub in str(val).split(','):
                                if sub.strip(): alias_map[sub.strip().lower()] = main_p
                return sorted(list(set([str(x).strip() for x in main_vals if pd.notna(x) and str(x).strip() not in ['-', '', 'nan']])))
            all_v = [col for col in df.columns if "Unnamed" not in str(col)] + df.values.flatten().tolist()
            return sorted(list(set([str(x).strip() for x in all_v if pd.notna(x) and str(x).strip() not in ['-', '', 'nan']])))
        return {
            "bx_ux_blades": get_clean_list('Blades BX-UX'),  # <-- Nova lista separada
            "cx_blades": get_clean_list('Blades CX'),        # <-- Nova lista separada
            "ratchets": get_clean_list('Ratchets'),
            "bits": get_clean_list('Bits'), 
            "assist_blades": get_clean_list('Assist Blades'),
            "metal_blades": get_clean_list('Metal Blades'), 
            "over_blades": get_clean_list('Over Blades'),
            "lock_chips": get_clean_list('Lock Chips')
        }, alias_map
    except: return {k: [] for k in ["bx_ux_blades", "cx_blades", "ratchets", "bits", "assist_blades", "metal_blades", "over_blades", "lock_chips"]}, {}

@st.cache_data(ttl=300)
def get_dynamic_player_list():
    jogadores_oficiais = []
    try:
        import json
        with open("bbpt_master_db.json", "r", encoding="utf-8") as f:
            db = json.load(f)
            profiles = db.get("global_versus", {}).get("profiles", [])
            for p in profiles:
                if isinstance(p, dict) and "name" in p: jogadores_oficiais.append(p["name"])
                elif isinstance(p, str): jogadores_oficiais.append(p)
    except: pass

    jogadores_novos = []
    try:
        sheet_jogadores = client.open_by_key(get_sheet_id()).worksheet("Jogadores")
        jogadores_novos = sheet_jogadores.col_values(1)[1:]
    except: pass

    todos = list(set(jogadores_oficiais + jogadores_novos))
    return sorted([j.strip() for j in todos if j and j.strip() != ""])

def load_players():
    players = ["-- Selecionar Jogador --", "Outro (Novo Jogador)"]
    if os.path.exists(DB_MASTER):
        try:
            with open(DB_MASTER, 'r', encoding='utf-8') as f:
                players = ["-- Selecionar Jogador --"] + sorted(list(json.load(f)['global_versus']['profiles'].keys())) + ["Outro (Novo Jogador)"]
        except: pass
    return players

def parse_smart_combo(text, parts_dict, alias_map):
    parsed = {"type": "Standard (BX / UX)", "main_blade": "--", "over_blade": "--", "metal_blade": "--", "assist_blade": "--", "lock_chip": "--", "ratchet": "--", "bit": "--"}
    words = text.split()
    words_cl = [re.sub(r'[^a-zA-Z0-9]', '', w).lower() for w in words]
    text_cl = "".join(words_cl)
    
    # Cria uma lista temporária que junta todas as main blades para procurar
    temp_dict = parts_dict.copy()
    temp_dict["all_main_blades"] = parts_dict.get("bx_ux_blades", []) + parts_dict.get("cx_blades", [])
    
    cats = [("over_blades", "over_blade"), ("metal_blades", "metal_blade"), ("all_main_blades", "main_blade"), ("assist_blades", "assist_blade"), ("ratchets", "ratchet"), ("bits", "bit"), ("lock_chips", "lock_chip")]
    
    for cat, key in cats:
        best, r_max = "--", 0
        if cat == "bits":
            for al, mp in sorted(alias_map.items(), key=lambda x: len(x[0]), reverse=True):
                if re.sub(r'[^a-zA-Z0-9]', '', al).lower() in words_cl:
                    best = mp; break
            if best != "--": parsed[key] = best; continue
            
        for p in sorted(temp_dict.get(cat, []), key=len, reverse=True):
            p_cl = re.sub(r'[^a-zA-Z0-9]', '', p).lower()
            if p_cl and p_cl in text_cl: 
                best = p; break 
                
            p_words = re.sub(r'[^a-zA-Z0-9\s]', '', p).lower().split()
            if not p_words: continue
            
            match_score = 0
            for pw in p_words:
                best_w_score = 0
                for w in words_cl:
                    score = difflib.SequenceMatcher(None, pw, w).ratio()
                    if score > best_w_score: best_w_score = score
                match_score += best_w_score
                
            avg_score = match_score / len(p_words)
            if avg_score > 0.85 and avg_score > r_max:
                r_max = avg_score; best = p
                
        parsed[key] = best

    # Inteligência de Inferência de Formato:
    if parsed["over_blade"] != "--" or parsed["metal_blade"] != "--": 
        parsed["type"] = "CX Expanded"
    elif parsed["assist_blade"] != "--" or parsed["main_blade"] in parts_dict.get("cx_blades", []): 
        parsed["type"] = "CX" # Se a main blade for do Excel CX, muda sozinho!
    else: 
        parsed["type"] = "Standard (BX / UX)"
    
    if parsed["type"] in ["CX", "CX Expanded"] and parsed["lock_chip"] == "--" and words:
        parsed["lock_chip"] = words[0].capitalize()
        
    return parsed

def apply_smart_combo(slot, data):
    st.session_state[f"c_{slot}_type"] = data.get("type")
    for k in ["lock_chip", "main_blade", "over_blade", "metal_blade", "assist_blade", "ratchet", "bit"]: st.session_state[f"c_{slot}_{k}"] = data.get(k, "--")
    if 'smart_match' in st.session_state: del st.session_state.smart_match
    st.session_state.smart_val = ""
    st.session_state.keyup_key += 1

def cancel_smart_combo():
    if 'smart_match' in st.session_state: del st.session_state.smart_match
    st.session_state.smart_val = ""
    st.session_state.keyup_key += 1

def append_suggestion(sug_text):
    words = st.session_state.smart_val.split()
    if words:
        words[-1] = sug_text
        st.session_state.smart_val = " ".join(words) + " "
        st.session_state.keyup_key += 1

# ==========================================
# INTERFACE
# ==========================================
st.sidebar.title("🛡️ BBPT App")
menu = st.sidebar.radio("Navegação:", ["📝 Formulário Público", "⚙️ Painel de Organização"])
event_status = get_event_status_cached()

if menu == "📝 Formulário Público":
    st.title("📝 BBPT League - Deck Check")
    
    if not event_status["is_open"]:
        st.warning("🔒 Check-in Fechado.")
        st.stop()
    
    # --- NOVA LINHA: Mostrar o nome do evento com destaque ---
    st.info(f"🏆 **A submeter para o evento:** {event_status['event_name']}")
    
    recs_list = get_all_records_cached(event_status["event_name"])
    st.metric("Decks Submetidos", len(recs_list))
    
    recs_list = get_all_records_cached(event_status["event_name"])
    st.metric("Decks Submetidos", len(recs_list))
    parts, alias_map = load_parts()
    player_list = load_players()
    
    all_available_parts = []
    for cat_parts in parts.values(): all_available_parts.extend(cat_parts)
    all_available_parts = list(set(all_available_parts))

    lista_dinamica = get_dynamic_player_list()
    opcoes_blader = ["-- Selecionar --"] + lista_dinamica + ["Outro (Novo Jogador)"]

    with st.container(border=True):
        c_id1, c_id2 = st.columns([1, 2])
        selected_player = c_id1.selectbox("Blader:", opcoes_blader)
        custom_player = c_id2.text_input("Novo Blader:") if selected_player == "Outro (Novo Jogador)" else ""
        
    with st.container(border=True):
        st.subheader("⚡ Quick Add (Autocomplete Ativo)")
        c1, c2 = st.columns([3, 1])
        
        with c1:
            current_text = st_keyup("Escreve ou cola o teu combo:", value=st.session_state.smart_val, key=f"sk_{st.session_state.keyup_key}", placeholder="Ex: Flat 1-60 Dran Buster")
            if current_text is not None: st.session_state.smart_val = current_text
            
            if st.session_state.smart_val and not st.session_state.smart_val.endswith(" "):
                last_word = st.session_state.smart_val.split()[-1]
                if len(last_word) >= 2:
                    sugestoes = [p for p in all_available_parts if last_word.lower() in p.lower() and p.lower() != last_word.lower()][:5]
                    if sugestoes:
                        st.caption("✨ Sugestões (clica para completar):")
                        cols = st.columns(len(sugestoes))
                        for idx, s in enumerate(sugestoes): cols[idx].button(s, key=f"btn_{s}_{idx}", on_click=append_suggestion, args=(s,))

        if c2.button("Analisar 🔍", use_container_width=True):
            if st.session_state.smart_val.strip(): st.session_state.smart_match = parse_smart_combo(st.session_state.smart_val, parts, alias_map)
                
        if "smart_match" in st.session_state:
            m = st.session_state.smart_match
            
            # Construir o texto de visualização consoante o tipo de combo
            if m["type"] == "Standard (BX / UX)":
                display_text = f"{m.get('main_blade')} | {m.get('ratchet')} | {m.get('bit')}"
            elif m["type"] == "CX":
                display_text = f"{m.get('lock_chip')} | {m.get('main_blade')} | {m.get('assist_blade')} | {m.get('ratchet')} | {m.get('bit')}"
            else: # CX Expanded
                display_text = f"{m.get('lock_chip')} | {m.get('over_blade')} | {m.get('metal_blade')} | {m.get('assist_blade')} | {m.get('ratchet')} | {m.get('bit')}"
                
            st.info(f"🧩 Detetado ({m['type']}): {display_text}")
            
            idx = st.selectbox("Slot:", [f"Combo {i+1}" for i in range(st.session_state.num_combos)])
            idx_n = int(idx.split(" ")[1]) - 1
            cb1, cb2 = st.columns(2)
            cb1.button("Aplicar", on_click=apply_smart_combo, args=(idx_n, m))
            cb2.button("Cancelar", on_click=cancel_smart_combo)
            
    st.radio("Nº Beyblades:", options=[3, 4], horizontal=True, key="num_combos")
    for i in range(st.session_state.num_combos):
        with st.container(border=True):
            t1, t2 = st.columns([1, 3]); t1.markdown(f"#### Combo {i+1}")
            ct = t2.selectbox("Tipo", ["Standard (BX / UX)", "CX", "CX Expanded"], key=f"c_{i}_type", label_visibility="collapsed")
            
            if ct == "Standard (BX / UX)":
                c1, c2, c3 = st.columns([2, 1, 1])
                # APENAS AS LÂMINAS BX/UX
                c1.selectbox("Blade", ["--"]+parts["bx_ux_blades"], key=f"c_{i}_main_blade")
                c2.selectbox("Ratchet", ["--"]+parts["ratchets"], key=f"c_{i}_ratchet")
                c3.selectbox("Bit", ["--"]+parts["bits"], key=f"c_{i}_bit")
            elif ct == "CX":
                c1, c2, c3, c4, c5 = st.columns([1.5, 2, 2, 1.2, 1.2])
                if parts["lock_chips"]: c1.selectbox("Chip", ["--"]+parts["lock_chips"], key=f"c_{i}_lock_chip")
                else: c1.text_input("Chip", key=f"c_{i}_lock_chip")
                # APENAS AS LÂMINAS CX
                c2.selectbox("Main", ["--"]+parts["cx_blades"], key=f"c_{i}_main_blade")
                c3.selectbox("Assist", ["--"]+parts["assist_blades"], key=f"c_{i}_assist_blade")
                c4.selectbox("Ratchet", ["--"]+parts["ratchets"], key=f"c_{i}_ratchet")
                c5.selectbox("Bit", ["--"]+parts["bits"], key=f"c_{i}_bit")
            else:
                c1, c2, c3, c4, c5, c6 = st.columns([1.5, 2, 2, 2, 1.2, 1.2])
                if parts["lock_chips"]: c1.selectbox("Chip", ["--"]+parts["lock_chips"], key=f"c_{i}_lock_chip")
                else: c1.text_input("Chip", key=f"c_{i}_lock_chip")
                c2.selectbox("Over", ["--"]+parts["over_blades"], key=f"c_{i}_over_blade")
                c3.selectbox("Metal", ["--"]+parts["metal_blades"], key=f"c_{i}_metal_blade")
                c4.selectbox("Assist", ["--"]+parts["assist_blades"], key=f"c_{i}_assist_blade")
                c5.selectbox("Ratchet", ["--"]+parts["ratchets"], key=f"c_{i}_ratchet")
                c6.selectbox("Bit", ["--"]+parts["bits"], key=f"c_{i}_bit")
                
    with st.container(border=True):
        up = st.file_uploader("Foto:", type=['png', 'jpg', 'jpeg'])
        if up: st.image(up, width=300)
        
    if st.button("Submeter Deck 🚀", use_container_width=True, type="primary"):
        name = custom_player if selected_player == "Outro (Novo Jogador)" else selected_player
        combos, missing_parts = [], False
        
        # Variáveis de Repetição (Restauradas)
        has_duplicates = False
        dup_error_msg = ""
        used_blades, used_ratchets, used_bits, used_chips, used_assist, used_metal = set(), set(), set(), set(), set(), set()
        
        for i in range(st.session_state.num_combos):
            ct = st.session_state[f"c_{i}_type"]; cd = {"type": ct, "combo_number": i+1}
            ks = ["main_blade", "ratchet", "bit"] if ct == "Standard (BX / UX)" else ["lock_chip", "main_blade", "assist_blade", "ratchet", "bit"] if ct == "CX" else ["lock_chip", "over_blade", "metal_blade", "assist_blade", "ratchet", "bit"]
            
            for k in ks:
                v = st.session_state.get(f"c_{i}_{k}", "--")
                cd[k] = v
                if v == "--" or not str(v).strip(): missing_parts = True
            combos.append(cd)

            # Validações Detalhadas de Duplicados (Restauradas)
            if not missing_parts and not has_duplicates:
                b = cd.get('over_blade', cd.get('main_blade', '--'))
                if b != '--':
                    base = re.sub(r'\s*\(.*?\)\s*', '', str(b)).strip().lower()
                    if base in used_blades: has_duplicates = True; dup_error_msg = f"A Blade '{b}' (ou remake) está repetida!"
                    used_blades.add(base)
                    
                r = cd.get('ratchet', '--')
                if r != '--':
                    if r in used_ratchets: has_duplicates = True; dup_error_msg = f"A Ratchet '{r}' está repetida!"
                    used_ratchets.add(r)
                    
                bt = cd.get('bit', '--')
                if bt != '--':
                    if bt in used_bits: has_duplicates = True; dup_error_msg = f"A Bit '{bt}' está repetida!"
                    used_bits.add(bt)
                    
                if 'assist_blade' in cd and cd['assist_blade'] != '--':
                    if cd['assist_blade'] in used_assist: has_duplicates = True; dup_error_msg = f"A Assist Blade '{cd['assist_blade']}' está repetida!"
                    used_assist.add(cd['assist_blade'])

                if 'metal_blade' in cd and cd['metal_blade'] != '--':
                    if cd['metal_blade'] in used_metal: has_duplicates = True; dup_error_msg = f"A Metal Blade '{cd['metal_blade']}' está repetida!"
                    used_metal.add(cd['metal_blade'])

                if 'lock_chip' in cd and cd['lock_chip'] != '--' and cd['lock_chip'].strip() != '':
                    chip = cd['lock_chip'].strip().lower()
                    if chip in used_chips: has_duplicates = True; dup_error_msg = f"O Lock Chip '{cd['lock_chip']}' está repetido!"
                    used_chips.add(chip)

        if name == "-- Selecionar Jogador --" or not name.strip(): st.error("⚠️ Por favor, identifica-te.")
        elif missing_parts: st.error("⚠️ Faltam peças! Preenche todas as opções do teu deck.")
        elif has_duplicates: st.error(f"⚠️ **Regra de Deck Check:** {dup_error_msg}")
        elif not up: st.error("⚠️ Faltou anexar a prova fotográfica do deck!")
        else:
            with st.spinner("A gravar submissão..."):
                save_submission_cloud(name, combos, up, event_status["event_name"])
                
                # --- NOVO BLOCO: Registo do Novo Jogador na aba "Jogadores" ---
                if selected_player == "Outro (Novo Jogador)" and custom_player.strip() != "":
                    try:
                        client_g = get_gsheet_client()
                        sheet_jogadores = client_g.open_by_key(get_sheet_id()).worksheet("Jogadores")
                        nomes_existentes = sheet_jogadores.col_values(1)
                        if custom_player.strip() not in nomes_existentes:
                            sheet_jogadores.append_row([custom_player.strip()])
                    except: 
                        pass
                # --------------------------------------------------------------
            
            st.success("✅ O teu Deck foi submetido na base de dados oficial!")
            
            # Restaurado o Painel Markdown do Discord
            st.markdown("---")
            st.markdown(f"### 🔍 Resumo de Check-in: **{name}**")
            
            discord_text = f"🛡️ **Deck Oficial - {name}**\n"
            for c in combos:
                if c['type'] == 'Standard (BX / UX)': discord_text += f"🔹 **Combo {c['combo_number']}:** {c['main_blade']} | {c['ratchet']} | {c['bit']}\n"
                elif c['type'] == 'CX': discord_text += f"🔹 **Combo {c['combo_number']} (CX):** {c['lock_chip']} | {c['main_blade']} | {c['assist_blade']} | {c['ratchet']} | {c['bit']}\n"
                elif c['type'] == 'CX Expanded': discord_text += f"🔹 **Combo {c['combo_number']} (CX Exp):** {c['lock_chip']} | {c['over_blade']} | {c['metal_blade']} | {c['assist_blade']} | {c['ratchet']} | {c['bit']}\n"
            
            sum_c1, sum_c2 = st.columns([3, 2])
            with sum_c1:
                st.info("Para partilhares no Discord, clica no botão de copiar no topo direito da caixa abaixo.")
                st.code(discord_text, language="markdown")
                st.markdown("""
                💡 **Como colocar no Discord com a foto num único post:**
                1. Clica no ícone 📋 no canto superior direito da caixa preta acima.
                2. Clica na tua foto ao lado com o botão direito do rato e escolhe **"Copiar imagem"**.
                3. Vai ao Discord e faz **Colar (Ctrl+V)** na caixa de mensagens!
                """)
            with sum_c2:
                st.image(up, caption="Fotografia do Deck", use_container_width=True)

elif menu == "⚙️ Painel de Organização":
    st.title("🛡️ Admin")
    
    # 1. Criar a memória de autenticação (se não existir)
    if "admin_auth" not in st.session_state:
        st.session_state.admin_auth = False

    # 2. Mostrar o Formulário de Login se não estiver autenticado
    if not st.session_state.admin_auth:
        with st.form("login_form"):
            pwd = st.text_input("Password:", type="password")
            submit = st.form_submit_button("Entrar no Painel 🔑")
            
            if submit:
                # O .strip() garante que espaços acidentais não estragam a password
                if pwd.strip() == ADMIN_PASSWORD:
                    st.session_state.admin_auth = True
                    st.rerun() # Força a página a recarregar já autenticada
                else:
                    st.error("❌ Palavra-passe incorreta!")

    # 3. Mostrar o Painel de Gestão se estiver autenticado
    if st.session_state.admin_auth:
        # Botão prático para sair e trancar o painel novamente
        if st.button("Sair (Logout) 🔒"):
            st.session_state.admin_auth = False
            st.rerun()
            
        st.subheader("📢 Gestão de Eventos")
        past_events = get_past_events_list()
        if past_events:
            with st.expander("📂 Histórico de Eventos (Reabrir)", expanded=False):
                sel_past = st.selectbox("Selecionar evento antigo:", ["-- Escolher --"] + past_events)
                if sel_past != "-- Escolher --":
                    if st.button(f"Ativar '{sel_past}'"): set_event_status(True, sel_past); st.rerun()
        st.divider()
        col1, col2 = st.columns(2)
        ev_n = col1.text_input("Novo Evento:", value=event_status["event_name"])
        if event_status["is_open"]:
            if col1.button("FECHAR EVENTO", type="primary"): set_event_status(False, event_status["event_name"]); st.rerun()
        else:
            if col1.button("ABRIR EVENTO"): set_event_status(True, ev_n); st.rerun()
        if col2.button("Limpar Cache 🔄"): st.cache_data.clear(); st.rerun()
        st.divider()
        recs_admin = get_all_records_cached(event_status["event_name"])
        st.metric(f"Total em '{event_status['event_name']}'", len(recs_admin))
        for d in recs_admin:
            with st.expander(f"👤 {d['Player']}"):
                c1, c2 = st.columns([2, 1])
                with c1:
                    for i in range(1, 5):
                        if d.get(f'Combo_{i}'): st.write(f"**Combo {i}:** {d[f'Combo_{i}']}")
                c2.image(d['Image_URL'])

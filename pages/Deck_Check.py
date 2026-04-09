import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import requests
import base64
import json
import os
import difflib
import re
from st_keyup import st_keyup

# ==========================================
# CONFIGURAÇÕES INICIAIS E CONSTANTES
# ==========================================
st.set_page_config(page_title="Deck Check - BBPT", page_icon="📝", layout="wide")

ADMIN_PASSWORD = "bbpt"
DATASET_PARTS = "Dataset_BeybladeParts.xlsx"

# Caminho absoluto para a imagem (Evita o MediaFileStorageError)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # Sobe uma pasta (de pages para a raiz)
logo_path = os.path.join(BASE_DIR, "logo.png")

# ==========================================
# LIGAÇÃO ÀS APIS (GOOGLE & IMGBB)
# ==========================================
@st.cache_resource
def get_google_client():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds_dict = dict(st.secrets["GCP_CREDENTIALS"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    return gspread.authorize(creds)

def get_sheet_id():
    url = st.secrets["SHEET_URL"]
    return url.split("/d/")[1].split("/")[0]

client = get_google_client()

def upload_to_imgbb(image_bytes):
    url = "https://api.imgbb.com/1/upload"
    payload = {
        "key": st.secrets["IMGBB_API_KEY"],
        "image": base64.b64encode(image_bytes).decode("utf-8")
    }
    response = requests.post(url, data=payload)
    if response.status_code == 200:
        return response.json()["data"]["url"]
    return None

# ==========================================
# LEITURA DE DADOS E MEMÓRIA
# ==========================================
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
            "bx_ux_blades": get_clean_list('Blades BX-UX'),
            "cx_blades": get_clean_list('Blades CX'),
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

# ==========================================
# GESTÃO DO EVENTO (USANDO ABA "Config")
# ==========================================
def get_event_status():
    try:
        sheet = client.open_by_key(get_sheet_id())
        try: config_ws = sheet.worksheet("Config")
        except: 
            config_ws = sheet.add_worksheet(title="Config", rows="10", cols="2")
            config_ws.update('A1:B2', [['is_open', 'event_name'], ['TRUE', 'Novo Evento BBPT']])
        
        data = config_ws.get_all_records()
        if data:
            return {"is_open": str(data[0].get("is_open", "TRUE")).upper() == "TRUE", "event_name": str(data[0].get("event_name", "Evento"))}
    except: pass
    return {"is_open": False, "event_name": "Erro a carregar"}

def set_event_status(is_open, event_name):
    try:
        config_ws = client.open_by_key(get_sheet_id()).worksheet("Config")
        config_ws.update('A2:B2', [[str(is_open).upper(), event_name]])
    except: pass

@st.cache_data(ttl=60)
def get_all_records_cached(event_name_filter=None):
    try:
        ws = client.open_by_key(get_sheet_id()).sheet1
        recs = ws.get_all_records()
        if event_name_filter:
            recs = [r for r in recs if str(r.get("Event_Name", "")) == event_name_filter]
        return recs
    except: return []

# ==========================================
# MOTOR SMART INPUT E VALIDAÇÃO
# ==========================================
def parse_smart_combo(text, parts_dict, alias_map):
    parsed = {"type": "Standard (BX / UX)", "main_blade": "--", "over_blade": "--", "metal_blade": "--", "assist_blade": "--", "lock_chip": "--", "ratchet": "--", "bit": "--"}
    words = text.split()
    words_cl = [re.sub(r'[^a-zA-Z0-9]', '', w).lower() for w in words]
    text_cl = "".join(words_cl)
    
    temp_dict = parts_dict.copy()
    temp_dict["all_main_blades"] = parts_dict.get("bx_ux_blades", []) + parts_dict.get("cx_blades", [])
    cats = [("over_blades", "over_blade"), ("metal_blades", "metal_blade"), ("all_main_blades", "main_blade"), ("assist_blades", "assist_blade"), ("ratchets", "ratchet"), ("bits", "bit"), ("lock_chips", "lock_chip")]
    
    for cat, key in cats:
        best, r_max = "--", 0
        if cat == "bits":
            for al, mp in sorted(alias_map.items(), key=lambda x: len(x[0]), reverse=True):
                if re.sub(r'[^a-zA-Z0-9]', '', al).lower() in words_cl: best = mp; break
            if best != "--": parsed[key] = best; continue
            
        for p in sorted(temp_dict.get(cat, []), key=len, reverse=True):
            p_cl = re.sub(r'[^a-zA-Z0-9]', '', p).lower()
            if p_cl and p_cl in text_cl: best = p; break 
            p_words = re.sub(r'[^a-zA-Z0-9\s]', '', p).lower().split()
            if not p_words: continue
            match_score = sum(max([difflib.SequenceMatcher(None, pw, w).ratio() for w in words_cl] + [0]) for pw in p_words)
            avg_score = match_score / len(p_words)
            if avg_score > 0.85 and avg_score > r_max: r_max = avg_score; best = p
        parsed[key] = best

    if parsed["over_blade"] != "--" or parsed["metal_blade"] != "--": parsed["type"] = "CX Expanded"
    elif parsed["assist_blade"] != "--" or parsed["main_blade"] in parts_dict.get("cx_blades", []): parsed["type"] = "CX"
    else: parsed["type"] = "Standard (BX / UX)"
    
    if parsed["type"] in ["CX", "CX Expanded"] and parsed["lock_chip"] == "--" and words: parsed["lock_chip"] = words[0].capitalize()
    return parsed

def check_duplicates(combos):
    used = set()
    for combo in combos:
        parts = [p.strip() for p in combo.split('|') if p.strip() and p.strip() != "--"]
        for p in parts:
            if p in used: return True, p
            used.add(p)
    return False, ""

# ==========================================
# INTERFACE PRINCIPAL
# ==========================================
parts, alias = load_parts()
event_status = get_event_status()

if os.path.exists(logo_path):
    st.sidebar.image(logo_path, use_container_width=True)
else:
    st.sidebar.markdown("### BBPT App")

menu = st.sidebar.radio("Navegação:", ["📝 Formulário Público", "⚙️ Painel de Organização"])

if menu == "📝 Formulário Público":
    st.title("📝 BBPT League - Deck Check")
    
    if not event_status["is_open"]:
        st.warning("🔒 Check-in Fechado. Aguarda a abertura por parte da organização.")
        st.stop()
        
    st.info(f"🏆 **A submeter para o evento:** {event_status['event_name']}")
    recs_list = get_all_records_cached(event_status["event_name"])
    st.metric("Decks Submetidos", len(recs_list))
    st.divider()

    lista_dinamica = get_dynamic_player_list()
    player_sel = st.selectbox("Blader", ["-- Selecionar --"] + lista_dinamica + ["Outro (Novo Jogador)"])
    novo_jogador_nome = ""
    if player_sel == "Outro (Novo Jogador)":
        novo_jogador_nome = st.text_input("Escreve o teu nome:")

    if "num_combos" not in st.session_state: st.session_state.num_combos = 3
    st.session_state.num_combos = st.radio("Formato do Deck:", [1, 3, 4], index=1, horizontal=True)

    with st.expander("✨ Smart Input (Colar do Discord/Notas)", expanded=False):
        smart_txt = st_keyup("Cola aqui o teu deck completo...")
        if smart_txt:
            linhas = [l for l in smart_txt.split('\n') if l.strip()]
            for i, linha in enumerate(linhas[:st.session_state.num_combos]):
                st.session_state[f"smart_res_{i}"] = parse_smart_combo(linha, parts, alias)

    combos_finais = []
    for i in range(st.session_state.num_combos):
        st.markdown(f"### Combo {i+1}")
        smart_data = st.session_state.get(f"smart_res_{i}", {"type": "Standard (BX / UX)", "main_blade": "--", "over_blade": "--", "metal_blade": "--", "assist_blade": "--", "lock_chip": "--", "ratchet": "--", "bit": "--"})
        
        ct = st.selectbox("Formato", ["Standard (BX / UX)", "CX", "CX Expanded"], key=f"c_{i}_type", index=["Standard (BX / UX)", "CX", "CX Expanded"].index(smart_data["type"]))
        
        if ct == "Standard (BX / UX)":
            c1, c2, c3 = st.columns([2, 1, 1])
            b = c1.selectbox("Blade", ["--"]+parts["bx_ux_blades"], key=f"c_{i}_mb", index=0 if smart_data["main_blade"] not in parts["bx_ux_blades"] else parts["bx_ux_blades"].index(smart_data["main_blade"])+1)
            r = c2.selectbox("Ratchet", ["--"]+parts["ratchets"], key=f"c_{i}_r", index=0 if smart_data["ratchet"] not in parts["ratchets"] else parts["ratchets"].index(smart_data["ratchet"])+1)
            bt = c3.selectbox("Bit", ["--"]+parts["bits"], key=f"c_{i}_b", index=0 if smart_data["bit"] not in parts["bits"] else parts["bits"].index(smart_data["bit"])+1)
            combos_finais.append(f"{b} | {r} | {bt}")
            
        elif ct == "CX":
            c1, c2, c3, c4, c5 = st.columns([1.5, 2, 2, 1.2, 1.2])
            lc = c1.text_input("Chip", value=smart_data["lock_chip"] if smart_data["lock_chip"]!="--" else "", key=f"c_{i}_lc")
            mb = c2.selectbox("Main", ["--"]+parts["cx_blades"], key=f"c_{i}_m", index=0 if smart_data["main_blade"] not in parts["cx_blades"] else parts["cx_blades"].index(smart_data["main_blade"])+1)
            ab = c3.selectbox("Assist", ["--"]+parts["assist_blades"], key=f"c_{i}_a", index=0 if smart_data["assist_blade"] not in parts["assist_blades"] else parts["assist_blades"].index(smart_data["assist_blade"])+1)
            r = c4.selectbox("Ratchet", ["--"]+parts["ratchets"], key=f"c_{i}_r", index=0 if smart_data["ratchet"] not in parts["ratchets"] else parts["ratchets"].index(smart_data["ratchet"])+1)
            bt = c5.selectbox("Bit", ["--"]+parts["bits"], key=f"c_{i}_b", index=0 if smart_data["bit"] not in parts["bits"] else parts["bits"].index(smart_data["bit"])+1)
            combos_finais.append(f"{lc} | {mb} | {ab} | {r} | {bt}")
            
        elif ct == "CX Expanded":
            c1, c2, c3, c4, c5, c6 = st.columns(6)
            lc = c1.text_input("Chip", value=smart_data["lock_chip"] if smart_data["lock_chip"]!="--" else "", key=f"c_{i}_lc")
            ob = c2.selectbox("Over", ["--"]+parts["over_blades"], key=f"c_{i}_o", index=0 if smart_data["over_blade"] not in parts["over_blades"] else parts["over_blades"].index(smart_data["over_blade"])+1)
            meb = c3.selectbox("Metal", ["--"]+parts["metal_blades"], key=f"c_{i}_me", index=0 if smart_data["metal_blade"] not in parts["metal_blades"] else parts["metal_blades"].index(smart_data["metal_blade"])+1)
            ab = c4.selectbox("Assist", ["--"]+parts["assist_blades"], key=f"c_{i}_a", index=0 if smart_data["assist_blade"] not in parts["assist_blades"] else parts["assist_blades"].index(smart_data["assist_blade"])+1)
            r = c5.selectbox("Ratchet", ["--"]+parts["ratchets"], key=f"c_{i}_r", index=0 if smart_data["ratchet"] not in parts["ratchets"] else parts["ratchets"].index(smart_data["ratchet"])+1)
            bt = c6.selectbox("Bit", ["--"]+parts["bits"], key=f"c_{i}_b", index=0 if smart_data["bit"] not in parts["bits"] else parts["bits"].index(smart_data["bit"])+1)
            combos_finais.append(f"{lc} | {ob} | {meb} | {ab} | {r} | {bt}")

    st.markdown("### 📸 Fotografia do Deck")
    img_file = st.file_uploader("Anexar foto", type=["jpg", "jpeg", "png"])
    
    if st.button("🚀 Submeter Deck", type="primary", use_container_width=True):
        final_name = novo_jogador_nome if player_sel == "Outro (Novo Jogador)" else player_sel
        if not final_name or final_name == "-- Selecionar --":
            st.error("Identifica o Blader!")
            st.stop()
            
        for idx, c in enumerate(combos_finais):
            if "--" in c or " |  |" in c or c.startswith(" |"):
                st.error(f"Faltam peças no Combo {idx+1}!")
                st.stop()
                
        has_dup, p_dup = check_duplicates(combos_finais)
        if has_dup:
            st.error(f"❌ Peça duplicada detetada: **{p_dup}**. As regras impedem repetições.")
            st.stop()
            
        if not img_file:
            st.error("A fotografia é obrigatória!")
            st.stop()
            
        with st.spinner("A enviar para a base de dados..."):
            img_url = upload_to_imgbb(img_file.getvalue())
            if not img_url:
                st.error("Erro ao alojar a imagem.")
                st.stop()
                
            row_data = [
                pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
                event_status["event_name"],
                final_name,
                combos_finais[0] if len(combos_finais) > 0 else "",
                combos_finais[1] if len(combos_finais) > 1 else "",
                combos_finais[2] if len(combos_finais) > 2 else "",
                combos_finais[3] if len(combos_finais) > 3 else "",
                img_url
            ]
            
            try:
                sheet1 = client.open_by_key(get_sheet_id()).sheet1
                sheet1.append_row(row_data)
                
                # Registo do Novo Jogador na aba "Jogadores"
                if player_sel == "Outro (Novo Jogador)" and novo_jogador_nome.strip() != "":
                    try:
                        sheet_jogadores = client.open_by_key(get_sheet_id()).worksheet("Jogadores")
                        nomes_existentes = sheet_jogadores.col_values(1)
                        if novo_jogador_nome.strip() not in nomes_existentes:
                            sheet_jogadores.append_row([novo_jogador_nome.strip()])
                    except: pass
                
                st.success("✅ Deck submetido com sucesso!")
                
                md = f"**{final_name}**\n"
                for i, c in enumerate(combos_finais):
                    md += f"Combo {i+1}: {c}\n"
                md += f"Imagem: {img_url}"
                st.code(md, language="markdown")
                
                st.cache_data.clear()
            except Exception as e:
                st.error(f"Erro ao ligar ao Google Sheets: {e}")

# ==========================================
# PAINEL DE ADMINISTRAÇÃO
# ==========================================
elif menu == "⚙️ Painel de Organização":
    st.title("🛡️ Admin")
    
    if "admin_auth" not in st.session_state: st.session_state.admin_auth = False

    if not st.session_state.admin_auth:
        with st.form("login_form"):
            pwd = st.text_input("Password:", type="password")
            submit = st.form_submit_button("Entrar no Painel 🔑")
            if submit:
                if pwd.strip() == ADMIN_PASSWORD:
                    st.session_state.admin_auth = True
                    st.rerun()
                else: st.error("❌ Palavra-passe incorreta!")

    if st.session_state.admin_auth:
        if st.button("Sair (Logout) 🔒"):
            st.session_state.admin_auth = False
            st.rerun()
            
        st.subheader("📢 Gestão de Eventos")
        col1, col2 = st.columns(2)
        ev_n = col1.text_input("Nome do Evento:", value=event_status["event_name"])
        
        if event_status["is_open"]:
            if col1.button("FECHAR EVENTO", type="primary"):
                set_event_status(False, ev_n)
                st.cache_data.clear()
                st.rerun()
        else:
            if col1.button("ABRIR EVENTO"):
                set_event_status(True, ev_n)
                st.cache_data.clear()
                st.rerun()
                
        if col2.button("Limpar Cache 🔄"):
            st.cache_data.clear()
            st.rerun()
            
        st.divider()
        recs_admin = get_all_records_cached(event_status["event_name"])
        st.metric(f"Total de submissões em '{event_status['event_name']}'", len(recs_admin))
        for d in recs_admin:
            with st.expander(f"👤 {d.get('Player', 'Sem Nome')}"):
                c1, c2 = st.columns([2, 1])
                with c1:
                    for i in range(1, 5):
                        if d.get(f'Combo_{i}'): st.write(f"**Combo {i}:** {d[f'Combo_{i}']}")
                c2.image(d.get('Image_URL', ''))

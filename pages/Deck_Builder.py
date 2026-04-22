import streamlit as st
import pandas as pd
import random
import re
import base64
import os
import gspread
from google.oauth2.service_account import Credentials
import json
import hashlib

# ==========================================
# CONFIGURAÇÃO DE PÁGINA E CSS
# ==========================================
st.set_page_config(page_title="BBPT Deck Builder", layout="wide")

st.markdown("""
<style>
    .block-container { padding-top: 2rem !important; }
    .part-card { text-align: center; padding: 10px; background-color: #f8f9fa; border-radius: 8px; margin-bottom: 10px; color: black;}
    .part-card img { max-width: 100%; height: 80px; object-fit: contain; margin-bottom: 5px; }
    .part-name { font-size: 0.8rem; font-weight: bold; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .part-category { font-size: 0.65rem; color: #666; text-transform: uppercase; }
    
    .light-backdrop-icon {
        background-color: rgba(255, 255, 255, 0.85);
        padding: 3px 6px;
        border-radius: 6px;
    }
    
    .deck-summary-box {
        background-color: #0f111a;
        border-radius: 12px;
        padding: 30px;
        margin-top: 20px;
        color: white;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        box-shadow: 0px 8px 16px rgba(0,0,0,0.4);
    }
    .deck-summary-title {
        text-align: center;
        font-size: 32px;
        font-weight: 900;
        letter-spacing: 2px;
        margin-bottom: 30px;
        text-transform: uppercase;
        color: #ffffff;
    }
    .combo-row {
        display: flex;
        align-items: center;
        padding: 15px 0;
        border-bottom: 1px solid #1f2333;
    }
    .combo-row:last-child {
        border-bottom: none;
    }
    /* ---- AJUSTE DE IMAGENS BX/UX ---- */
        .combo-blade-img {
            width: 110px;
            height: 110px;
            flex-shrink: 0; /* Impede que a imagem encolha no telemóvel */
            object-fit: contain;
            margin-right: 20px;
            filter: drop-shadow(0px 4px 6px rgba(0,0,0,0.5));
        }
        
        /* ---- AJUSTE DE IMAGENS CX E CX EXPANDED ---- */
        .composite-blade-container {
            position: relative;
            width: 110px; /* Tem de ser exatamente igual ao da .combo-blade-img */
            height: 110px; /* Tem de ser exatamente igual ao da .combo-blade-img */
            flex-shrink: 0; /* Impede que o contentor encolha no telemóvel */
            margin-right: 20px;
        }
        .composite-layer {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            object-fit: contain;
        }
        
        /* As lâminas ocupam 100% do contentor, escalando perfeitamente */
        .layer-metal, .layer-main { 
            width: 100%; 
            height: 100%; 
            filter: drop-shadow(0px 4px 6px rgba(0,0,0,0.5)); 
        }
        
        .layer-metal { z-index: 1; }
        .layer-main { z-index: 2; }
        
        /* O Lock Chip ocupa ~42% da imagem. Proporção perfeita e responsiva! */
        .layer-chip { 
            width: 42%; 
            height: 42%; 
            z-index: 3; 
        }

    .combo-info {
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    .combo-top-line {
        display: flex;
        align-items: center;
        margin-bottom: 8px;
    }
    .combo-line-img {
        height: 32px;
        margin-right: 15px;
        object-fit: contain;
    }
    .combo-bottom-line {
        display: flex;
        align-items: center;
    }
    .combo-icon {
        height: 30px;
        margin-right: 12px;
    }
    .combo-text {
        font-size: 22px;
        font-weight: 700;
        color: #f1f1f1;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# LIGAÇÃO À BASE DE DADOS (GOOGLE SHEETS)
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

# ==========================================
# CONVERSOR DE IMAGENS LOCAIS PARA BASE64
# ==========================================
@st.cache_data
def get_local_image_as_base64(file_name):
    paths_to_try = [file_name, os.path.join("..", file_name)]
    for path in paths_to_try:
        if os.path.exists(path):
            with open(path, "rb") as f:
                encoded = base64.b64encode(f.read()).decode()
            return f"data:image/png;base64,{encoded}"
    return "https://via.placeholder.com/150"

ICONS = {
    "Right Spin": get_local_image_as_base64("Right-Spin_logo_Beyblade_X.png"),
    "Left Spin": get_local_image_as_base64("Left-Spin_logo_Beyblade_X.png"),
    "Attack": get_local_image_as_base64("Attack_logo_Beyblade_X.png"),
    "Defense": get_local_image_as_base64("Defense_logo_Beyblade_X.png"),
    "Stamina": get_local_image_as_base64("Stamina_logo_Beyblade_X.png"),
    "Balance": get_local_image_as_base64("Balance_logo_Beyblade_X.png")
}

LINE_LOGOS = {
    "Basic (BX)": get_local_image_as_base64("Basic_Line_Logo - Copy.png"),
    "Unique (UX)": get_local_image_as_base64("Unique_Line_Logo - Copy.png"),
    "Custom (CX)": get_local_image_as_base64("Custom_Line.png"),
    "Expand (CXE)": get_local_image_as_base64("Expand_Infinity.png")
}

# ==========================================
# LEITURA DO EXCEL
# ==========================================
DATASET_PARTS = "Dataset_BeybladeParts_Final_Images.xlsx"

@st.cache_data
def load_builder_data():
    parts_dict = {}
    images_dict = {}
    bx_list = []
    ux_list = []
    
    try:
        xls = pd.read_excel(DATASET_PARTS, sheet_name=None)
        for sheet_name, df in xls.items():
            clean_list = []
            df.columns = [str(c).strip() for c in df.columns]
            for _, row in df.iterrows():
                name = str(row.iloc[0]).strip()
                if pd.isna(name) or name in ['-', '', 'nan'] or "Unnamed" in name: 
                    continue
                clean_list.append(name)
                if sheet_name == 'Blades BX-UX':
                    linhagem = ""
                    if 'Linhagem' in df.columns:
                        linhagem = str(row['Linhagem']).strip().upper()
                    if 'UX' in linhagem:
                        ux_list.append(name)
                    else:
                        bx_list.append(name)
                for val in row.iloc[1:]:
                    val_str = str(val).strip()
                    if val_str.startswith("http"):
                        images_dict[name] = val_str
                        break
            parts_dict[sheet_name] = sorted(list(set(clean_list)))
            
        return {
            "bx_blades": sorted(list(set(bx_list))),
            "ux_blades": sorted(list(set(ux_list))),
            "cx_blades": parts_dict.get('Blades CX', []),
            "ratchets": parts_dict.get('Ratchets', []),
            "bits": parts_dict.get('Bits', []), 
            "assist_blades": parts_dict.get('Assist Blades', []),
            "metal_blades": parts_dict.get('Metal Blades', []), 
            "over_blades": parts_dict.get('Over Blades', []),
            "lock_chips": parts_dict.get('Lock Chips', [])
        }, images_dict
    except Exception as e:
        st.error(f"Erro ao carregar ficheiro Excel: {e}")
        return {k: [] for k in ["bx_blades", "ux_blades", "cx_blades", "ratchets", "bits", "assist_blades", "metal_blades", "over_blades", "lock_chips"]}, {}

parts, images_map = load_builder_data()

# ==========================================
# GESTOR DE ESTADO E LOGIN (SIDEBAR)
# ==========================================
if "deck_size" not in st.session_state: st.session_state.deck_size = 3
if "logged_in_user" not in st.session_state: st.session_state.logged_in_user = None

for i in range(4):
    if f"b_c_{i}_type" not in st.session_state: st.session_state[f"b_c_{i}_type"] = "Basic (BX)"
    if f"b_c_{i}_spin" not in st.session_state: st.session_state[f"b_c_{i}_spin"] = "Right Spin"
    if f"b_c_{i}_bt" not in st.session_state: st.session_state[f"b_c_{i}_bt"] = "Attack"
    
    for k in ["main_blade", "ratchet", "bit", "lock_chip", "assist_blade", "metal_blade", "over_blade"]:
        if f"b_c_{i}_{k}" not in st.session_state:
            st.session_state[f"b_c_{i}_{k}"] = "--"

st.sidebar.title("🔐 Área Pessoal")

if st.session_state.logged_in_user is None:
    with st.sidebar.form("login_form"):
        st.write("Acede aos teus Decks Gravados:")
        user_input = st.text_input("Blader (Nome):")
        pass_input = st.text_input("Password:", type="password")
        if st.form_submit_button("Entrar"):
            pass_hash = hashlib.md5(pass_input.encode()).hexdigest()
            try:
                client = get_gsheet_client()
                sheet_contas = client.open_by_key(get_sheet_id()).worksheet("Contas")
                records = sheet_contas.get_all_records()
                user_found = False
                for row in records:
                    if str(row["Nome"]).strip().lower() == user_input.strip().lower():
                        user_found = True
                        if str(row["Password"]).strip() == pass_hash:
                            st.session_state.logged_in_user = row["Nome"]
                            st.rerun()
                        else:
                            st.error("❌ Password incorreta!")
                if not user_found:
                    st.error("❌ Utilizador não encontrado.")
            except Exception as e: 
                st.error("⚠️ Erro de ligação à BD:{e}")
else:
    st.sidebar.success(f"Bem-vindo, {st.session_state.logged_in_user}!")
    if st.sidebar.button("Sair"):
        st.session_state.logged_in_user = None
        st.rerun()

    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🗄️ Meus Decks")
    slot_choice = st.sidebar.selectbox("Escolher Slot:", ["Slot_1", "Slot_2", "Slot_3", "Slot_4", "Slot_5"])
    
    # --- COLUNAS PARA GRAVAR E CARREGAR ---
    col_save, col_load = st.sidebar.columns(2)
    
    if col_save.button("💾 Gravar", use_container_width=True, type="primary"):
        deck_to_save = {"size": st.session_state.deck_size, "combos": []}
        for i in range(st.session_state.deck_size):
            combo = {
                "type": st.session_state[f"b_c_{i}_type"],
                "spin": st.session_state.get(f"b_c_{i}_spin", "Right Spin"),
                "bt": st.session_state.get(f"b_c_{i}_bt", "Attack"),
                "main_blade": st.session_state.get(f"b_c_{i}_main_blade", "--"),
                "ratchet": st.session_state.get(f"b_c_{i}_ratchet", "--"),
                "bit": st.session_state.get(f"b_c_{i}_bit", "--"),
                "lock_chip": st.session_state.get(f"b_c_{i}_lock_chip", "--"),
                "assist_blade": st.session_state.get(f"b_c_{i}_assist_blade", "--"),
                "metal_blade": st.session_state.get(f"b_c_{i}_metal_blade", "--"),
                "over_blade": st.session_state.get(f"b_c_{i}_over_blade", "--")
            }
            deck_to_save["combos"].append(combo)
        json_string = json.dumps(deck_to_save)
        with st.spinner("A gravar..."):
            try:
                client = get_gsheet_client()
                sheet_contas = client.open_by_key(get_sheet_id()).worksheet("Contas")
                cell = sheet_contas.find(st.session_state.logged_in_user, in_column=1)
                col_index = ["Slot_1", "Slot_2", "Slot_3", "Slot_4", "Slot_5"].index(slot_choice) + 3
                sheet_contas.update_cell(cell.row, col_index, json_string)
                st.sidebar.success(f"Gravado!")
            except:
                st.sidebar.error("Erro!")

    if col_load.button("📥 Carregar", use_container_width=True):
        with st.spinner("A carregar..."):
            try:
                client = get_gsheet_client()
                sheet_contas = client.open_by_key(get_sheet_id()).worksheet("Contas")
                cell = sheet_contas.find(st.session_state.logged_in_user, in_column=1)
                col_index = ["Slot_1", "Slot_2", "Slot_3", "Slot_4", "Slot_5"].index(slot_choice) + 3
                raw_data = sheet_contas.cell(cell.row, col_index).value
                
                if raw_data and raw_data.startswith("{"):
                    loaded_deck = json.loads(raw_data)
                    st.session_state.deck_size = loaded_deck.get("size", 3)
                    for i, c in enumerate(loaded_deck["combos"]):
                        st.session_state[f"b_c_{i}_type"] = c.get("type", "Basic (BX)")
                        st.session_state[f"b_c_{i}_spin"] = c.get("spin", "Right Spin")
                        st.session_state[f"b_c_{i}_bt"] = c.get("bt", "Attack")
                        st.session_state[f"b_c_{i}_main_blade"] = c.get("main_blade", "--")
                        st.session_state[f"b_c_{i}_ratchet"] = c.get("ratchet", "--")
                        st.session_state[f"b_c_{i}_bit"] = c.get("bit", "--")
                        st.session_state[f"b_c_{i}_lock_chip"] = c.get("lock_chip", "--")
                        st.session_state[f"b_c_{i}_assist_blade"] = c.get("assist_blade", "--")
                        st.session_state[f"b_c_{i}_metal_blade"] = c.get("metal_blade", "--")
                        st.session_state[f"b_c_{i}_over_blade"] = c.get("over_blade", "--")
                    st.rerun()
                else:
                    st.sidebar.warning("Slot vazio!")
            except:
                st.sidebar.error("Erro!")

# ==========================================
# RANDOMIZER E UTILIDADES
# ==========================================
def clear_deck():
    for i in range(4):
        st.session_state[f"b_c_{i}_type"] = "Basic (BX)"
        st.session_state[f"b_c_{i}_spin"] = "Right Spin"
        st.session_state[f"b_c_{i}_bt"] = "Attack"
        for k in ["main_blade", "ratchet", "bit", "lock_chip", "assist_blade", "metal_blade", "over_blade"]:
            st.session_state[f"b_c_{i}_{k}"] = "--"

def randomize_deck():
    st.session_state.deck_size = 3
    used_blades, used_ratchets, used_bits, used_chips, used_assist, used_metal = set(), set(), set(), set(), set(), set()
    types = ["Basic (BX)", "Unique (UX)", "Custom (CX)", "Expand (CXE)"]
    spins = ["Right Spin", "Left Spin"]
    b_types = ["Attack", "Defense", "Stamina", "Balance"]
    
    def pick_unique(pool, used_set):
        available = [p for p in pool if p not in used_set]
        if not available: return "--"
        choice = random.choice(available)
        used_set.add(re.sub(r'\s*\(.*?\)\s*', '', choice).strip().lower())
        return choice

    for i in range(st.session_state.deck_size):
        ctype = random.choice(types)
        st.session_state[f"b_c_{i}_type"] = ctype
        st.session_state[f"b_c_{i}_spin"] = random.choice(spins)
        st.session_state[f"b_c_{i}_bt"] = random.choice(b_types)
        for k in ["main_blade", "ratchet", "bit", "lock_chip", "assist_blade", "metal_blade", "over_blade"]:
            st.session_state[f"b_c_{i}_{k}"] = "--"
            
        if ctype == "Basic (BX)":
            st.session_state[f"b_c_{i}_main_blade"] = pick_unique(parts["bx_blades"], used_blades)
            st.session_state[f"b_c_{i}_ratchet"] = pick_unique(parts["ratchets"], used_ratchets)
            st.session_state[f"b_c_{i}_bit"] = pick_unique(parts["bits"], used_bits)
        elif ctype == "Unique (UX)":
            st.session_state[f"b_c_{i}_main_blade"] = pick_unique(parts["ux_blades"], used_blades)
            st.session_state[f"b_c_{i}_ratchet"] = pick_unique(parts["ratchets"], used_ratchets)
            st.session_state[f"b_c_{i}_bit"] = pick_unique(parts["bits"], used_bits)
        elif ctype == "Custom (CX)":
            st.session_state[f"b_c_{i}_lock_chip"] = pick_unique(parts["lock_chips"], used_chips)
            st.session_state[f"b_c_{i}_main_blade"] = pick_unique(parts["cx_blades"], used_blades)
            st.session_state[f"b_c_{i}_assist_blade"] = pick_unique(parts["assist_blades"], used_assist)
            st.session_state[f"b_c_{i}_ratchet"] = pick_unique(parts["ratchets"], used_ratchets)
            st.session_state[f"b_c_{i}_bit"] = pick_unique(parts["bits"], used_bits)
        else:
            st.session_state[f"b_c_{i}_lock_chip"] = pick_unique(parts["lock_chips"], used_chips)
            st.session_state[f"b_c_{i}_metal_blade"] = pick_unique(parts["metal_blades"], used_metal)
            st.session_state[f"b_c_{i}_over_blade"] = pick_unique(parts["over_blades"], used_blades)
            st.session_state[f"b_c_{i}_assist_blade"] = pick_unique(parts["assist_blades"], used_assist)
            st.session_state[f"b_c_{i}_ratchet"] = pick_unique(parts["ratchets"], used_ratchets)
            st.session_state[f"b_c_{i}_bit"] = pick_unique(parts["bits"], used_bits)

# ==========================================
# TÍTULO E INTERFACE PRINCIPAL
# ==========================================
st.title("🛠️ Custom Deck Builder")
st.markdown("Constrói, testa e exporta os teus decks. Validação automática de regras BBPT ativada.")

col_size, col_clear, col_rand = st.columns([2, 1, 1])
with col_size:
    st.radio("Tamanho do Deck:", options=[3, 4], horizontal=True, key="deck_size")
with col_clear:
    st.button("🧹 Limpar Deck", use_container_width=True, on_click=clear_deck)
with col_rand:
    st.button("🎲 Gerar Aleatório", use_container_width=True, on_click=randomize_deck)

st.divider()

def render_part_card(part_name, category):
    if part_name == "--":
        st.markdown(f'<div class="part-card" style="opacity: 0.4;"><div style="height: 80px; display: flex; align-items: center; justify-content: center; color: #999;">?</div><div class="part-category">{category}</div><div class="part-name">---</div></div>', unsafe_allow_html=True)
        return
    img_url = images_map.get(part_name, "https://via.placeholder.com/150?text=No+Image")
    st.markdown(f'<div class="part-card"><img src="{img_url}" alt="{part_name}" referrerpolicy="no-referrer"><div class="part-category">{category}</div><div class="part-name" title="{part_name}">{part_name}</div></div>', unsafe_allow_html=True)

# ==========================================
# CONSTRUTOR DE COMBOS
# ==========================================
for i in range(st.session_state.deck_size):
    with st.container(border=True):
        c_title, c_type, c_spin, c_bt = st.columns([1.2, 2, 1, 1])
        with c_title:
            st.markdown(f"#### 🌀 Combo {i+1}")
        with c_type:
            ct = st.selectbox("Linha", ["Basic (BX)", "Unique (UX)", "Custom (CX)", "Expand (CXE)"], key=f"b_c_{i}_type", label_visibility="collapsed")
            if ct == "Expand (CXE)":
                st.markdown(f"<img src='{LINE_LOGOS['Custom (CX)']}' style='height: 24px; margin-top: 5px; margin-right: 5px;'><img src='{LINE_LOGOS['Expand (CXE)']}' style='height: 24px; margin-top: 5px;'>", unsafe_allow_html=True)
            else:
                st.markdown(f"<img src='{LINE_LOGOS[ct]}' style='height: 24px; margin-top: 5px;'>", unsafe_allow_html=True)
        with c_spin:
            sp = st.selectbox("Rotação", ["Right Spin", "Left Spin"], key=f"b_c_{i}_spin", label_visibility="collapsed")
            st.markdown(f"<img src='{ICONS[sp]}' class='light-backdrop-icon' style='height: 24px; margin-top: 5px;'>", unsafe_allow_html=True)
        with c_bt:
            bt = st.selectbox("Tipo", ["Attack", "Defense", "Stamina", "Balance"], key=f"b_c_{i}_bt", label_visibility="collapsed")
            st.markdown(f"<img src='{ICONS[bt]}' style='height: 24px; margin-top: 5px;'>", unsafe_allow_html=True)
            
        st.write("") 
        
        if ct in ["Basic (BX)", "Unique (UX)"]:
            blade_list = parts["bx_blades"] if ct == "Basic (BX)" else parts["ux_blades"]
            c1, c2, c3 = st.columns([2, 1, 1])
            c1.selectbox("Blade", ["--"]+blade_list, key=f"b_c_{i}_main_blade")
            c2.selectbox("Ratchet", ["--"]+parts["ratchets"], key=f"b_c_{i}_ratchet")
            c3.selectbox("Bit", ["--"]+parts["bits"], key=f"b_c_{i}_bit")
            g1, g2, g3 = st.columns(3)
            with g1: render_part_card(st.session_state[f"b_c_{i}_main_blade"], "Blade")
            with g2: render_part_card(st.session_state[f"b_c_{i}_ratchet"], "Ratchet")
            with g3: render_part_card(st.session_state[f"b_c_{i}_bit"], "Bit")
            
        elif ct == "Custom (CX)":
            c1, c2, c3, c4, c5 = st.columns([1.5, 2, 2, 1.2, 1.2])
            c1.selectbox("Chip", ["--"]+parts["lock_chips"], key=f"b_c_{i}_lock_chip")
            c2.selectbox("Main", ["--"]+parts["cx_blades"], key=f"b_c_{i}_main_blade")
            c3.selectbox("Assist", ["--"]+parts["assist_blades"], key=f"b_c_{i}_assist_blade")
            c4.selectbox("Ratchet", ["--"]+parts["ratchets"], key=f"b_c_{i}_ratchet")
            c5.selectbox("Bit", ["--"]+parts["bits"], key=f"b_c_{i}_bit")
            g1, g2, g3, g4, g5 = st.columns(5)
            with g1: render_part_card(st.session_state[f"b_c_{i}_lock_chip"], "Lock Chip")
            with g2: render_part_card(st.session_state[f"b_c_{i}_main_blade"], "Main Blade")
            with g3: render_part_card(st.session_state[f"b_c_{i}_assist_blade"], "Assist Blade")
            with g4: render_part_card(st.session_state[f"b_c_{i}_ratchet"], "Ratchet")
            with g5: render_part_card(st.session_state[f"b_c_{i}_bit"], "Bit")
            
        else: # Expand (CXE)
            c1, c2, c3, c4, c5, c6 = st.columns([1.5, 2, 2, 2, 1.2, 1.2])
            c1.selectbox("Chip", ["--"]+parts["lock_chips"], key=f"b_c_{i}_lock_chip")
            c2.selectbox("Metal", ["--"]+parts["metal_blades"], key=f"b_c_{i}_metal_blade")
            c3.selectbox("Over", ["--"]+parts["over_blades"], key=f"b_c_{i}_over_blade")
            c4.selectbox("Assist", ["--"]+parts["assist_blades"], key=f"b_c_{i}_assist_blade")
            c5.selectbox("Ratchet", ["--"]+parts["ratchets"], key=f"b_c_{i}_ratchet")
            c6.selectbox("Bit", ["--"]+parts["bits"], key=f"b_c_{i}_bit")
            g1, g2, g3, g4, g5, g6 = st.columns(6)
            with g1: render_part_card(st.session_state[f"b_c_{i}_lock_chip"], "Lock Chip")
            with g2: render_part_card(st.session_state[f"b_c_{i}_metal_blade"], "Metal Blade")
            with g3: render_part_card(st.session_state[f"b_c_{i}_over_blade"], "Over Blade")
            with g4: render_part_card(st.session_state[f"b_c_{i}_assist_blade"], "Assist Blade")
            with g5: render_part_card(st.session_state[f"b_c_{i}_ratchet"], "Ratchet")
            with g6: render_part_card(st.session_state[f"b_c_{i}_bit"], "Bit")

st.divider()

has_duplicates = False
dup_error_msg = ""
missing_parts = False

used_blades, used_ratchets, used_bits, used_chips, used_assist, used_metal = set(), set(), set(), set(), set(), set()
deck_text_export = "🛡️ **O Meu Deck BBPT**\n"
combo_data_for_visual = []

for i in range(st.session_state.deck_size):
    ct = st.session_state[f"b_c_{i}_type"]
    sp = st.session_state[f"b_c_{i}_spin"]
    bt = st.session_state[f"b_c_{i}_bt"]
    
    ks = ["main_blade", "ratchet", "bit"] if ct in ["Basic (BX)", "Unique (UX)"] else ["lock_chip", "main_blade", "assist_blade", "ratchet", "bit"] if ct == "Custom (CX)" else ["lock_chip", "metal_blade" , "over_blade" , "assist_blade", "ratchet", "bit"]
    
    combo_str_parts = []
    for k in ks:
        v = st.session_state[f"b_c_{i}_{k}"]
        combo_str_parts.append(v)
        if v == "--": missing_parts = True
        
    deck_text_export += f"🔹 **Combo {i+1}:** [{sp}] [{bt}] {' | '.join(combo_str_parts)}\n"

    if not missing_parts and not has_duplicates:
        b = st.session_state[f"b_c_{i}_over_blade"] if "Expand" in ct else st.session_state.get(f"b_c_{i}_main_blade", "--")
        if b != '--':
            base = re.sub(r'\s*\(.*?\)\s*', '', str(b)).strip().lower()
            if base in used_blades: has_duplicates = True; dup_error_msg = f"A Blade '{b}' está repetida!"
            used_blades.add(base)
        r = st.session_state.get(f"b_c_{i}_ratchet", '--')
        if r != '--':
            if r in used_ratchets: has_duplicates = True; dup_error_msg = f"A Ratchet '{r}' está repetida!"
            used_ratchets.add(r)
        bt_val = st.session_state.get(f"b_c_{i}_bit", '--')
        if bt_val != '--':
            if bt_val in used_bits: has_duplicates = True; dup_error_msg = f"A Bit '{bt_val}' está repetida!"
            used_bits.add(bt_val)
        a = st.session_state.get(f"b_c_{i}_assist_blade", '--')
        if a != '--':
            if a in used_assist: has_duplicates = True; dup_error_msg = f"A Assist Blade '{a}' está repetida!"
            used_assist.add(a)
        m = st.session_state.get(f"b_c_{i}_metal_blade", '--')
        if m != '--':
            if m in used_metal: has_duplicates = True; dup_error_msg = f"A Metal Blade '{m}' está repetida!"
            used_metal.add(m)
        c = st.session_state.get(f"b_c_{i}_lock_chip", '--')
        if c != '--':
            c_low = c.strip().lower()
            if c_low in used_chips: has_duplicates = True; dup_error_msg = f"O Lock Chip '{c}' está repetido!"
            used_chips.add(c_low)

        img_html = ""
        if ct in ["Basic (BX)", "Unique (UX)"]:
            hero_blade = st.session_state[f"b_c_{i}_main_blade"]
            url_blade = images_map.get(hero_blade, "https://via.placeholder.com/150")
            img_html = f'<img class="combo-blade-img" src="{url_blade}" alt="Blade" referrerpolicy="no-referrer">'
        elif ct == "Custom (CX)":
            m_blade = st.session_state[f"b_c_{i}_main_blade"]
            l_chip = st.session_state[f"b_c_{i}_lock_chip"]
            url_main = images_map.get(m_blade, "https://via.placeholder.com/150")
            url_chip = images_map.get(l_chip, "https://via.placeholder.com/150")
            img_html = f'<div class="composite-blade-container"><img class="composite-layer layer-main" src="{url_main}" alt="Main" referrerpolicy="no-referrer"><img class="composite-layer layer-chip" src="{url_chip}" alt="Chip" referrerpolicy="no-referrer"></div>'
        else: # Expand (CXE)
            o_blade = st.session_state[f"b_c_{i}_over_blade"]
            mt_blade = st.session_state[f"b_c_{i}_metal_blade"]
            l_chip = st.session_state[f"b_c_{i}_lock_chip"]
            url_over = images_map.get(o_blade, "https://via.placeholder.com/150")
            url_metal = images_map.get(mt_blade, "https://via.placeholder.com/150")
            url_chip = images_map.get(l_chip, "https://via.placeholder.com/150")
            img_html = f'<div class="composite-blade-container"><img class="composite-layer layer-metal" src="{url_metal}" alt="Metal" referrerpolicy="no-referrer"><img class="composite-layer layer-main" src="{url_over}" alt="Over" referrerpolicy="no-referrer"><img class="composite-layer layer-chip" src="{url_chip}" alt="Chip" referrerpolicy="no-referrer"></div>'

        logos_html = ""
        if "Basic" in ct: logos_html += f'<img class="combo-line-img" src="{LINE_LOGOS["Basic (BX)"]}" alt="Basic">'
        if "Unique" in ct: logos_html += f'<img class="combo-line-img" src="{LINE_LOGOS["Unique (UX)"]}" alt="Unique">'
        if "Custom" in ct: logos_html += f'<img class="combo-line-img" src="{LINE_LOGOS["Custom (CX)"]}" alt="Custom">'
        if "Expand" in ct: logos_html += f'<img class="combo-line-img" src="{LINE_LOGOS["Custom (CX)"]}" alt="Custom"><img class="combo-line-img" src="{LINE_LOGOS["Expand (CXE)"]}" alt="Expand">'

        combo_data_for_visual.append({
            "image_html": img_html,
            "logos_html": logos_html,
            "spin": ICONS[sp],
            "type": ICONS[bt],
            "name": " ".join(combo_str_parts).replace("--", "")
        })

col_status, col_export = st.columns([2, 1])

with col_status:
    if missing_parts:
        st.warning("⚠️ O Deck está incompleto. Seleciona todas as peças para validar.")
    elif has_duplicates:
        st.error(f"❌ **Deck Ilegal:** {dup_error_msg}")
    else:
        st.success("✅ **Deck Legal e Válido para Torneios!**")

with col_export:
    st.info("Copia o texto abaixo ou tira um Print Screen do Cartão Visual!")
    st.code(deck_text_export, language="markdown")

if not missing_parts and not has_duplicates:
    html_rows = ""
    for c in combo_data_for_visual:
        html_rows += f'<div class="combo-row">{c["image_html"]}<div class="combo-info"><div class="combo-top-line">{c["logos_html"]}<img class="combo-icon light-backdrop-icon" src="{c["spin"]}" alt="Spin"></div><div class="combo-bottom-line"><img class="combo-icon" src="{c["type"]}" alt="Type"><span class="combo-text">{c["name"]}</span></div></div></div>'
    
    visual_report_html = f'<div class="deck-summary-box"><div class="deck-summary-title">DECK SUMMARY</div>{html_rows}</div>'
    st.markdown(visual_report_html, unsafe_allow_html=True)

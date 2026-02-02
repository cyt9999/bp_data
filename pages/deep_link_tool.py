import streamlit as st
import sys
import os

try:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(current_dir)
    if root_dir not in sys.path:
        sys.path.insert(0, root_dir)
except:
    pass

from bp_data import render_global_sidebar, get_blueprint_data, parse_blueprint_for_deeplink, find_tab_index_by_name

st.set_page_config(page_title="Deep Link Generator", page_icon="🔗", layout="wide")
render_global_sidebar()

st.title("🔗 Deep Link Generator (Smart)")

blueprint_data = get_blueprint_data()
if not blueprint_data:
    st.warning("⚠️ 請先上傳 Blueprint 以啟用智慧搜尋功能。")

# 解析目前藍圖
known_pages, param_defs = parse_blueprint_for_deeplink(blueprint_data)

# 初始化 State
if 'dl_uuids' not in st.session_state: st.session_state['dl_uuids'] = ["20000001"]
if 'dl_params' not in st.session_state: st.session_state['dl_params'] = {"int-main_tab_index": "0"}

# --- 1. 情境選擇 (智慧核心) ---
st.subheader("1. 快速情境")
st.caption("點擊情境後，系統會自動在藍圖中搜尋對應的 Tab Index 與 UUID。")

presets = {
    "Custom": "自訂 / 重置",
    "Club Board": "社團看板 (Club Board)",
    "Club Article": "社團文章 (Club Article)",
    "Content Article": "內容專區文章 (Article)",
    "Content Video": "內容專區影音 (Video)",
    "Stock": "個股頁 (Stock)",
    "Purchase": "內購頁 (Purchase)",
}

# 讓按鈕排成一列 (Pills or Radio horizontal)
scenario = st.radio("選擇情境", options=list(presets.keys()), format_func=lambda x: presets[x], horizontal=True, label_visibility="collapsed")

# === 智慧邏輯執行區 ===
# 只有當情境改變時，才觸發更新
if 'last_scenario' not in st.session_state: st.session_state['last_scenario'] = "Custom"

if scenario != st.session_state['last_scenario']:
    st.session_state['last_scenario'] = scenario
    
    # 預設重置
    new_params = {"int-main_tab_index": "0"}
    new_uuids = ["20000001"]
    
    if scenario == "Custom":
        pass # 重置為 Root
        
    elif "Club" in scenario:
        # 1. 自動找 Main Tab 中的 "社團"
        idx, club_tab_uuid = find_tab_index_by_name(blueprint_data, ["社團", "Club"])
        new_params["int-main_tab_index"] = idx
        st.toast(f"已自動定位「社團」分頁於 Index: {idx}")
        
        # 2. 自動找社團內部的 "看板" (通常預設為 0)
        new_params["int-boardIndex"] = "0"
        
        if scenario == "Club Board":
            # 社團看板 ID
            new_params["long-stateBoardId"] = "" # 留空給用戶填
            
        elif scenario == "Club Article":
            # 社團文章需要文章 ID
            new_uuids.append("8765433712") # Base Club Article UUID
            new_params["long-stateArticleId"] = ""
    
    elif "Content" in scenario:
        # 1. 自動找 "內容" 或 "Content"
        idx, content_tab_uuid = find_tab_index_by_name(blueprint_data, ["內容", "Content"])
        new_params["int-main_tab_index"] = idx
        st.toast(f"已自動定位「內容專區」分頁於 Index: {idx}")
        
        # 2. 判斷是文章還是影音
        if scenario == "Content Article":
            new_uuids.append("21247d60-59bb-11ee-aaed-3771d04b38f6") # Base Article Internal
            new_params["int-contentSectionIndex"] = "0" # 文章
            new_params["int-notesContentTabIndex"] = "0"
            new_params["string-stateDetailPageParam"] = ""
            
        elif scenario == "Content Video":
            new_uuids.append("288e87d1-59bb-11ee-aaed-3771d04b38f6") # Base Video Internal
            new_params["int-contentSectionIndex"] = "1" # 影音
            new_params["string-stateDetailPageParam"] = ""

    elif scenario == "Stock":
        # 1. 找 "選股" 或 "行情" 或 "自選"
        idx, stock_tab_uuid = find_tab_index_by_name(blueprint_data, ["選股", "行情", "Stock", "Quote"])
        new_params["int-main_tab_index"] = idx
        st.toast(f"已自動定位「個股」分頁於 Index: {idx}")
        
        new_uuids.append("40000001")
        new_params["string-stateCommKey"] = "2330" # 預設台積電

    elif scenario == "Purchase":
        new_uuids.append("888770000001")

    st.session_state['dl_uuids'] = new_uuids
    st.session_state['dl_uuids'] = new_uuids
    st.session_state['dl_params'] = new_params
    
    # 3. 強制刷新 Widget State
    # 當我們改變 params 時，如果不清除對應的 widget key，Streamlit 還是會顯示舊的 widget value (Pre 2.0 behavior assumption but safer)
    # 這裡我們主動清除 ui 綁定的 key，讓它重新讀取 params 的值
    keys_to_clear = []
    for k in list(st.session_state.keys()):
        if k.startswith("in_"):
            keys_to_clear.append(k)
    for k in keys_to_clear:
        del st.session_state[k]

    st.rerun()

# --- 2. 介面顯示 ---
col1, col2 = st.columns(2)

with col1:
    with st.container(border=True):
        st.subheader("2. 頁面堆疊 (UUIDs)")
        for i, u in enumerate(st.session_state['dl_uuids']):
            p_name = known_pages.get(u, {}).get('name', 'Unknown')
            st.code(f"{i+1}. {p_name}\n({u})")
        
        all_opts = {k: v['name'] for k, v in known_pages.items() if k != "20000001"}
        add_u = st.selectbox("新增頁面", [""] + list(all_opts.keys()), format_func=lambda x: all_opts.get(x, "") if x else "選擇...")
        if st.button("➕ 加入堆疊") and add_u:
            st.session_state['dl_uuids'].append(add_u)
            st.rerun()

with col2:
    with st.container(border=True):
        st.subheader("3. 參數設定")
        
        # 優先顯示與目前情境相關的參數
        priority_keys = ["int-main_tab_index", "int-boardIndex", "long-stateBoardId", "int-contentSectionIndex", "string-stateCommKey", "string-stateDetailPageParam", "long-stateArticleId"]
        
        def render_param_input(key, label_override=None):
            def_data = param_defs.get(key, {})
            label = label_override or def_data.get('label', key)
            current_val = st.session_state['dl_params'].get(key, "0")
            
            # Check if options exist
            opts = def_data.get('options')
            if opts and isinstance(opts, dict) and len(opts) > 0:
                # Dropdown
                # Ensure current value is in options, otherwise add it temporarily or reset? 
                # Usually we trust the options. If current_val not in options, we might want to sanitize it.
                # But for simplicity, we just list keys.
                opt_keys = list(opts.keys())
                
                # If current value is not in options (e.g. custom input), we might default to first option
                if current_val not in opt_keys:
                    # Try to match by value? Or just reset? 
                    # Let's just pick the first one if not found.
                    if opt_keys:
                         current_val = opt_keys[0]

                idx = opt_keys.index(current_val) if current_val in opt_keys else 0
                
                selected = st.selectbox(
                    f"{label} ({key})", 
                    options=opt_keys, 
                    index=idx,
                    format_func=lambda x: f"{opts[x]} ({x})",
                    key=f"in_{key}_select"
                )
                
                if selected != st.session_state['dl_params'].get(key):
                    st.session_state['dl_params'][key] = selected
                    st.rerun()
            else:
                # Text Input
                val = st.text_input(f"{label} ({key})", value=current_val, key=f"in_{key}")
                if val != st.session_state['dl_params'].get(key):
                    st.session_state['dl_params'][key] = val
                    st.rerun()

        # 顯示 Main Tab
        render_param_input("int-main_tab_index", "Main Tab Index")

        # 顯示其他活躍參數
        current_keys = list(st.session_state['dl_params'].keys())
        for key in priority_keys:
            if key in current_keys and key != "int-main_tab_index":
                render_param_input(key)
        
        # 顯示剩餘參數
        for key in current_keys:
            if key not in priority_keys:
                 render_param_input(key)

# --- 3. 結果 ---
st.markdown("---")
st.subheader("🚀 Result Link")
uuids_str = ",".join(st.session_state['dl_uuids'])
params_list = [f"{k}={v}" for k, v in st.session_state['dl_params'].items() if v]
final_url = f"https://www.cmoney.tw/app?uuids={uuids_str}"
if params_list:
    final_url += "&" + "&".join(params_list)

st.code(final_url)
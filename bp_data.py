import json
import os
import zipfile
import re
import streamlit as st
from collections import defaultdict

# ==========================================
#  1. 檔案處理與 Session State
# ==========================================
def init_session_state():
    if 'blueprint_data' not in st.session_state:
        st.session_state['blueprint_data'] = None
    if 'current_file_name' not in st.session_state:
        st.session_state['current_file_name'] = "尚未上傳"
    
    # Auto-load blueprint.json if exists and data is empty
    if st.session_state['blueprint_data'] is None:
        try:
            default_path = os.path.join(os.path.dirname(__file__), "blueprint.json")
            if os.path.exists(default_path):
                 with open(default_path, "r", encoding='utf-8') as f:
                     st.session_state['blueprint_data'] = json.load(f)
                 st.session_state['current_file_name'] = "Default (blueprint.json)"
        except Exception as e:
            print(f"Failed to load default blueprint: {e}")

def render_global_sidebar():
    init_session_state()
    with st.sidebar:
        st.header("📂 全域檔案管理")
        file_name = st.session_state.get('current_file_name', '尚未上傳')
        
        if st.session_state['blueprint_data']:
            st.success(f"✅ 已載入: {file_name}")
        else:
            st.info(f"ℹ️ 目前狀態: {file_name}")

        uploaded_file = st.file_uploader("更換 Blueprint (Zip/JSON)", type=['json', 'zip'], key="global_uploader")
        
        if uploaded_file:
            if uploaded_file.name != st.session_state.get('last_uploaded_name'):
                with st.spinner("檔案解析中..."):
                    data = _process_uploaded_file(uploaded_file)
                    if data:
                        st.session_state['blueprint_data'] = data
                        st.session_state['current_file_name'] = uploaded_file.name
                        st.session_state['last_uploaded_name'] = uploaded_file.name
                        st.rerun()

def _process_uploaded_file(uploaded_file):
    try:
        filename = uploaded_file.name
        if filename.endswith('.zip'):
            with zipfile.ZipFile(uploaded_file) as z:
                # 搜尋所有檔案，不分大小寫，只要檔名是 blueprint.json 即可
                target = None
                for f in z.namelist():
                     if os.path.basename(f).lower() == 'blueprint.json':
                         target = f
                         break
                
                if target:
                    with z.open(target) as f:
                        return json.load(f)
                else:
                    st.error("❌ ZIP 檔中未找到 `blueprint.json`，請確認檔案結構。")
        elif filename.endswith('.json'):
            uploaded_file.seek(0)
            return json.load(uploaded_file)
    except Exception as e:
        st.sidebar.error(f"讀取失敗: {e}")
    return None

def get_blueprint_data():
    return st.session_state.get('blueprint_data')

# ==========================================
#  2. 共用工具函式
# ==========================================
def clean_title(title):
    if not title: return ""
    return title.replace('{{', '').replace('}}', '')

def get_node_info(comp):
    uuid = comp.get("uuid", str(hash(str(comp))))
    name = comp.get("name", "Unknown")
    raw_title = comp.get("parameters", {}).get("title")
    if not raw_title: raw_title = comp.get("title")
    title = clean_title(raw_title)
    event_id = comp.get("eventId")
    label = title if title else name
    return {"uuid": uuid, "name": name, "title": title, "label": label, "eventId": event_id}

def find_root_component(components, target_uuid="20000001"):
    for comp in components:
        if comp.get("uuid") == target_uuid: return comp
        if "subComponents" in comp:
            found = find_root_component(comp["subComponents"], target_uuid)
            if found: return found
    return None

# ==========================================
#  3. Deep Link 智慧邏輯 (簡化版)
# ==========================================
# (保留您的 deep link 邏輯，此處不變)
def get_base_known_pages():
    return {
        "20000001": {"name": "Tab Page (首頁/Tab)", "params": ["int-main_tab_index"], "is_base": True},
        "40000001": {"name": "Stock Page (個股頁)", "params": ["int-single_stock_pager_index", "string-stateCommKey"], "is_base": True},
        "21247d60-59bb-11ee-aaed-3771d04b38f6": {"name": "Article Internal (內容專區文章)", "params": ["int-notesContentTabIndex", "string-stateDetailPageParam"], "is_base": True},
        "288e87d1-59bb-11ee-aaed-3771d04b38f6": {"name": "Video Internal (影音內頁)", "params": ["int-videoContentTabIndex", "string-stateDetailPageParam"], "is_base": True},
        "8765433712": {"name": "Club Article (社團文章全文)", "params": ["long-stateArticleId"], "is_base": True},
        "888770000001": {"name": "Purchase Page (內購頁)", "params": [], "is_base": True},
        "50000002": {"name": "Strategy Page", "params": ["int-strategy_index"], "is_base": True}
    }
def get_default_param_defs():
    return {
        "int-main_tab_index": {"label": "Main Tab", "options": {"0": "預設"}, "defaultValue": "0"},
        "int-contentSectionIndex": {"label": "Content Tab", "options": {"0": "文章", "1": "影音"}, "defaultValue": "0"},
        "int-boardIndex": {"label": "Club Tab", "options": {"0": "動態牆", "1": "VIP"}, "defaultValue": "0"},
        "long-stateBoardId": {"label": "Board ID", "type": "text", "placeholder": "e.g. 10919"},
        "int-notesContentTabIndex": {"label": "Article Type", "options": {"0": "全部", "1": "免費"}, "defaultValue": "0"},
        "int-videoContentTabIndex": {"label": "Video Type", "options": {"0": "全部", "1": "免費"}, "defaultValue": "0"},
        "int-single_stock_pager_index": {"label": "Stock Tab", "options": {"0": "即時", "1": "K線"}, "defaultValue": "0"},
        "string-stateCommKey": {"label": "Stock ID", "type": "text", "placeholder": "e.g. AAPL"},
        "string-stateDetailPageParam": {"label": "Content ID", "type": "text", "placeholder": "e.g. 1049030"},
        "long-stateArticleId": {"label": "Article ID", "type": "text", "placeholder": "e.g. 175155047"}
    }
def find_tab_index_by_name(blueprint_data, keyword_list, parent_uuid="20000001"):
    # (邏輯同前，省略以節省篇幅，請保留完整程式碼)
    if not blueprint_data: return "0", None
    parent_node = None
    if blueprint_data.get('uuid') == parent_uuid: parent_node = blueprint_data
    else:
        def _find(node):
            if node.get('uuid') == parent_uuid: return node
            for child in node.get('subComponents', []) + node.get('pages', []):
                res = _find(child)
                if res: return res
            return None
        parent_node = _find(blueprint_data)
    if not parent_node or 'subComponents' not in parent_node: return "0", None
    for idx, comp in enumerate(parent_node['subComponents']):
        name = comp.get('name', '')
        title = clean_title(comp.get('parameters', {}).get('title', ''))
        if not title: title = clean_title(comp.get('title', ''))
        
        # Case-insensitive check
        check_name = name.lower()
        check_title = title.lower()
        
        for kw in keyword_list:
            k_lower = kw.lower()
            if k_lower in check_title or k_lower in check_name: return str(idx), comp.get('uuid')
    return "0", None
def parse_blueprint_for_deeplink(data):
    # (邏輯同前，請保留)
    known_pages = get_base_known_pages()
    param_defs = get_default_param_defs()
    if not data: return known_pages, param_defs
    
    # 搜尋 Root Node logic
    root_node = None
    target_uuid = "20000001"
    
    if data.get('uuid') == target_uuid:
        root_node = data
    else:
        def _find_root(node):
            if node.get('uuid') == target_uuid: return node
            # Search in subComponents AND pages
            children = (node.get('subComponents') or []) + (node.get('pages') or [])
            for child in children:
                if isinstance(child, dict):
                    res = _find_root(child)
                    if res: return res
            return None
        root_node = _find_root(data)

    if root_node and 'subComponents' in root_node:
        main_tab_opts = {}
        for idx, comp in enumerate(root_node['subComponents']):
            raw_title = comp.get('title') or (comp.get('parameters') or {}).get('title') or comp.get('name')
            # 這裡的邏輯是過濾掉純容器且無意義標題的節點，但必須確保 Key (idx) 對應到真實的陣列索引
            if raw_title and "靜態容器" not in raw_title and "分頁容器" not in raw_title:
                clean = re.sub(r'{{|}}', '', raw_title).strip()
                if clean:
                    main_tab_opts[str(idx)] = clean
                    if comp.get('uuid') and comp['uuid'] != "20000001": known_pages[comp['uuid']] = {"name": f"Tab {idx}: {clean}", "params": [], "is_base": False, "dynamic": True}
        if main_tab_opts: param_defs['int-main_tab_index']['options'] = main_tab_opts
        
        # --- Content Tab Special Parsing ---
        # Find Content Tab (index 4 usually)
        content_tab_idx, content_tab_uuid = find_tab_index_by_name(data, ["內容", "Content"], "20000001")
        if content_tab_uuid:
            # Find the Pager Container inside Content Tab (Layer 2, usually index 2)
            # We need to find the node first
            def _find_node(node, t_uuid):
                if node.get('uuid') == t_uuid: return node
                children = (node.get('subComponents') or []) + (node.get('pages') or [])
                for child in children:
                    res = _find_node(child, t_uuid)
                    if res: return res
                return None
            
            content_node = _find_node(root_node, content_tab_uuid)
            if content_node and 'subComponents' in content_node:
                # Based on debug: [0] Nav, [1] Nav, [2] Pager Container
                # We look for a component that has subComponents which are Tab Pagers
                pager_node = None
                for child in content_node['subComponents']:
                    if child.get('name') == "分頁容器":
                        pager_node = child
                        break
                
                if pager_node and 'subComponents' in pager_node:
                    # define contentSectionIndex options
                    param_defs['int-contentSectionIndex'] = {
                        "label": "Content Section",
                        "options": {"0": "文章 (Article)", "1": "影音 (Video)"},
                        "defaultValue": "0"
                    }
                    
                    # Parse Article Tabs (Index 0)
                    if len(pager_node['subComponents']) > 0:
                        article_container = pager_node['subComponents'][0]
                        if 'subComponents' in article_container:
                            art_opts = {}
                            for i, sub in enumerate(article_container['subComponents']):
                                title = clean_title(sub.get('parameters', {}).get('title', ''))
                                if title: art_opts[str(i)] = title
                            if art_opts:
                                param_defs['int-notesContentTabIndex']['options'] = art_opts

                    # Parse Video Tabs (Index 1)
                    if len(pager_node['subComponents']) > 1:
                        video_container = pager_node['subComponents'][1]
                        if 'subComponents' in video_container:
                            vid_opts = {}
                            for i, sub in enumerate(video_container['subComponents']):
                                title = clean_title(sub.get('parameters', {}).get('title', ''))
                                if title: vid_opts[str(i)] = title
                            if vid_opts:
                                param_defs['int-videoContentTabIndex']['options'] = vid_opts
    def recursive_find_pages(node):
        if not isinstance(node, dict): return
        uuid = node.get('uuid')
        if uuid and uuid != "20000001" and uuid not in known_pages:
            raw_name = node.get('title') or node.get('name')
            if raw_name and isinstance(raw_name, str):
                clean = re.sub(r'{{|}}', '', raw_name).strip()
                if len(clean) > 1 and "靜態容器" not in clean and "分頁容器" not in clean:
                    known_pages[uuid] = {"name": f"藍圖 - {clean}", "params": [], "is_base": False, "dynamic": True}
        for child in node.get('subComponents', []) + node.get('pages', []): recursive_find_pages(child)
    def recursive_find_params(node):
        if not isinstance(node, dict): return
        params = node.get('parameters', {})
        target_keys = []
        if 'stateTabIndex' in params: target_keys.append(f"int-{params['stateTabIndex']}")
        if 'statePageIndex' in params: target_keys.append(f"int-{params['statePageIndex']}")
        if target_keys and 'titles' in params and isinstance(params['titles'], list):
            for key in target_keys:
                if key not in param_defs: param_defs[key] = {"label": key, "options": {}, "defaultValue": "0"}
                new_options = {}
                for idx, title in enumerate(params['titles']):
                    clean_title = re.sub(r'{{|}}', '', title).strip() or f"索引 {idx}"
                    new_options[str(idx)] = clean_title
                if new_options: param_defs[key]['options'] = new_options
        for child in node.get('subComponents', []) + node.get('pages', []): recursive_find_params(child)
    recursive_find_pages(data)
    recursive_find_params(data)
    return known_pages, param_defs

# ==========================================
#  4. App 架構 - ECharts 專用轉換 (New!)
# ==========================================

def get_echarts_tree_data(data, root_uuid="20000001", show_event_id=True, initial_depth=2):
    """
    將 Blueprint 轉換為 ECharts 遞迴 JSON 格式。
    - name: 顯示名稱
    - value: Event ID (用於 tooltip)
    - children: 子節點列表
    - collapsed: 是否收合 (根據深度決定)
    """

    def _find_node(node, target_uuid):
        if node.get('uuid') == target_uuid: return node
        children = (node.get('subComponents') or []) + (node.get('pages') or [])
        for child in children:
            if isinstance(child, dict):
                res = _find_node(child, target_uuid)
                if res: return res
        return None

    start_node = _find_node(data, root_uuid)
    if not start_node: return None

    def _transform(component, current_depth):
        info = get_node_info(component)
        my_id = info["uuid"]
        
        # 顯示名稱處理
        display_label = info["label"]
        # 如果太長，截斷 (ECharts 顯示優化)
        if len(display_label) > 15:
            display_label = display_label[:12] + "..."
            
        is_layout = info["name"] in ["靜態容器", "垂直捲動容器", "水平捲動容器", "底部分頁容器", "分頁容器", "頁籤分頁容器"]
        should_hide = is_layout and (not info["title"]) and (not info["eventId"])
        if my_id == root_uuid: should_hide = False

        # 如果此節點要隱藏，則直接回傳其「子節點的轉換結果」
        # 但 ECharts 是樹狀結構，如果父節點消失，子節點要掛在哪？
        # 策略：如果隱藏，則將其子節點提昇 (Flatten)
        # 但這會讓遞迴邏輯變複雜。
        # 簡化策略：不隱藏節點，但將 Layout 節點樣式變淡/變小，或者我們只在 display_label 做區隔。
        # 為了結構清晰，我們還是做「穿透」處理：回傳 list of children nodes
        
        children_nodes = []
        raw_children = (component.get('subComponents') or []) + (component.get('pages') or [])
        
        # 遞迴處理子節點
        next_depth = current_depth + 1 if not should_hide else current_depth
        for child in raw_children:
            if isinstance(child, dict):
                res = _transform(child, next_depth)
                if isinstance(res, list): # 子節點是隱藏節點，回傳了它的孩子們
                    children_nodes.extend(res)
                elif res: # 正常節點
                    children_nodes.append(res)
        
        # 如果當前節點要隱藏，直接回傳孩子們 (穿透)
        if should_hide:
            return children_nodes

        # 樣式設定
        item_style = {
            "color": "#fff", # 白底
            "borderColor": "#555",
            "borderWidth": 1,
            "borderRadius": 5 # 圓角
        }
        
        # 根據類型上色 (邊框或背景)
        if my_id == root_uuid:
            item_style["borderColor"] = "#FFD700" # 金色
            item_style["borderWidth"] = 3
        elif info["eventId"]:
            item_style["borderColor"] = "#2E7D32" # 綠色 (有埋點)
            item_style["borderWidth"] = 2
            item_style["color"] = "#E8F5E9" # 淺綠底
        
        node_data = {
            "name": display_label,
            "value": info["eventId"] if info["eventId"] else "No Event ID", # Tooltip 用
            "uuid": my_id, # 自訂欄位
            "itemStyle": item_style,
            "symbolSize": [120, 30] if len(display_label) < 8 else [160, 30], # 矩形大小
            "symbol": "roundRect", # 圓角矩形
            "collapsed": current_depth >= initial_depth # 初始展開深度
        }
        
        if children_nodes:
            node_data["children"] = children_nodes
            
        return node_data

    # 開始轉換
    return _transform(start_node, 0)

# ==========================================
#  5. 資料源分析 (For bp_analyzer.py)
# ==========================================
def analyze_blueprint_content(json_content_or_dict):
    results = []
    count = 0
    
    if not json_content_or_dict:
        return results, count

    # Helper to traverse and extract info
    def _traverse_subtree(node, context_group, breadcrumbs=None):
        if breadcrumbs is None: breadcrumbs = []
        nonlocal count
        count += 1
        
        # Determine if this node adds to the context (Title)
        # We only care about explicit titles (usually user-defined sub-pages or sections)
        current_crumbs = list(breadcrumbs)
        
        raw_t = node.get('title') or (node.get('parameters') or {}).get('title')
        if raw_t:
            clean = re.sub(r'{{|}}', '', raw_t).strip()
            # Filter out likely layout internal names if necessary, but usually 'title' param is significant.
            # We skip 'Root' or empty strings
            if clean:
                current_crumbs.append(clean)
        
        if isinstance(node, dict):
            # Check for data sources
            params = node.get('parameters', {})
            sources = params.get('source')
            
            if sources and isinstance(sources, list):
                info = get_node_info(node)
                comp_self_label = info.get('label', 'Unknown')
                
                # Construct Layout Context String
                # User wants "Mother Layer", e.g. "Live Replay", "Bonds"
                # We join the breadcrumbs.
                # If breadcrumbs exist, use them. If the last crumb is same as self label, maybe distinct?
                # E.g. Crumb: ["Stock", "Watchlist"], Self: "Watchlist Table" -> "Watchlist > Watchlist Table"
                
                # If crumbs are empty, use self label.
                # If crumbs exist, we assume they provide the path.
                # We exclude the 'Main Tab' name from crumbs if it's redundant with Group Name, 
                # but 'context_group' is passed separately.
                
                # Filter out crumbs that strictly match the group name to avoid "Stock > Stock > Sub"
                filtered_crumbs = [c for c in current_crumbs if c != context_group]
                
                if filtered_crumbs:
                    # e.g. "Live Replay"
                    context_str = " > ".join(filtered_crumbs)
                    # Append self label for precision? User said "Show the mother layer corresponding table"
                    # Maybe just "Mother Layer" is enough? But multiple tables might exist.
                    # Let's do: "Mother Layer (Component Name)"
                    display_name = f"{context_str} ({comp_self_label})"
                else:
                    display_name = comp_self_label

                for src in sources:
                    src_type = src.get('name', 'Unknown')
                    src_params = src.get('sourceParameters', {})
                    
                    src_id = "N/A"
                    if src_type == "GoogleSheet":
                        src_id = f"{src_params.get('sheetName', 'Unknown')} ({src_params.get('sheetId', '')})"
                    elif src_type == "dtno":
                        src_id = src_params.get('dtnoNum', 'Unknown')
                    elif src_type == "AddInfoDtno":
                         src_id = src_params.get('dtnoNum', 'Unknown')
                    
                    fields = []
                    has_explicit = False
                    if 'columns' in src_params and isinstance(src_params['columns'], list):
                        fields = src_params['columns']
                        has_explicit = True
                    
                    results.append({
                        "group": context_group,
                        "display_name": display_name,
                        "source_type": src_type,
                        "source_id": src_id,
                        "has_explicit_columns": has_explicit,
                        "fields_info": fields
                    })

            # Recurse
            children = (node.get('subComponents') or []) + (node.get('pages') or [])
            for child in children:
                _traverse_subtree(child, context_group, current_crumbs)

    # 1. Find Root (Bottom Tab Container)
    root_node = None
    target_uuid = "20000001"
    
    if json_content_or_dict.get('uuid') == target_uuid:
        root_node = json_content_or_dict
    else:
        def _find_root(node):
            if node.get('uuid') == target_uuid: return node
            children = (node.get('subComponents') or []) + (node.get('pages') or [])
            for child in children:
                if isinstance(child, dict):
                    res = _find_root(child)
                    if res: return res
            return None
        root_node = _find_root(json_content_or_dict)

    if root_node and 'subComponents' in root_node:
        # 2. Iterate Main Tabs
        for idx, tab in enumerate(root_node['subComponents']):
            # Determine Group Name (Tab Name)
            raw_t = tab.get('title') or (tab.get('parameters') or {}).get('title') or tab.get('name')
            group_name = f"Tab {idx}"
            if raw_t:
                clean = re.sub(r'{{|}}', '', raw_t).strip()
                if clean: group_name = clean
            
            # Traverse this tab's subtree
            # We don't verify 'breadcrumbs' here because the Tab Name is the Group Name.
            # We start crumbs empty so subs will capture their own titles.
            _traverse_subtree(tab, group_name, [])
    else:
        # Fallback
        _traverse_subtree(json_content_or_dict, "Global (No Tabs Found)")
        
    return results, count
    return results, count

# ==========================================
#  6. 主程式 (Dashboard Rendering)
# ==========================================
if __name__ == "__main__":
    st.set_page_config(page_title="Blueprint 萬能工具箱", layout="wide", page_icon="🛠️")
    render_global_sidebar()
    
    st.title("� Blueprint 萬能工具箱")
    # ==========================================
    #  Main Portal UI
    # ==========================================
    data = st.session_state.get('blueprint_data')
    
    # 1. Upload Warning
    if not data:
        st.warning("⚠️ 請先於左側 sidebar 上傳 `blueprint.json` 或 zip 檔以啟用所有功能。")
    
    st.markdown("### 🛠️ 工具模組")
    st.divider()

    # 2. Tool Grid (2x2)
    col1, col2 = st.columns(2)
    
    # Row 1
    with col1:
        with st.container(border=True):
            st.subheader("🔗 Deep Link 生成器")
            st.markdown("快速生成並測試 App 跳轉連結 (Deep Link)。")
            if data:
                st.page_link("pages/deep_link_tool.py", label="開啟工具", icon="➡️", use_container_width=True)
            else:
                 st.button("請先上傳檔案", disabled=True, key="btn_dl_disabled")

        with st.container(border=True):
             st.subheader("🗺️ App Sitemap Structure")
             st.markdown("可視化檢視 App 頁面結構與導航層級。")
             if data:
                st.page_link("pages/app_structure.py", label="開啟工具", icon="➡️", use_container_width=True)
             else:
                 st.button("請先上傳檔案", disabled=True, key="btn_map_disabled")

    with col2:
        with st.container(border=True):
            st.subheader("📊 資料源分析儀")
            st.markdown("解析 Blueprint 資料來源 (GoogleSheet/DTNO)。")
            if data:
                st.page_link("pages/bp_analyzer.py", label="開啟工具", icon="➡️", use_container_width=True)
            else:
                 st.button("請先上傳檔案", disabled=True, key="btn_ana_disabled")

        with st.container(border=True):
            st.subheader("📈 埋點管理 (Data Mining)")
            st.markdown("檢視與管理 App 事件埋點 (Click/View)。")
            if data:
                st.page_link("pages/data_mining.py", label="開啟工具", icon="➡️", use_container_width=True)
            else:
                 st.button("請先上傳檔案", disabled=True, key="btn_dm_disabled")

    st.markdown("---")

    # 3. Status Footer
    if data:
        fname = st.session_state.get('current_file_name', 'Unknown')
        pname = data.get('name', 'Unknown')
        pver = data.get('version', 'Unknown')
        st.success(f"📌 當前載入: **{fname}** (專案: {pname} v{pver})")
    else:
        st.info("ℹ️ 等待檔案上傳中...")

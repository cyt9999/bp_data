import streamlit as st
import json
import pandas as pd
from collections import defaultdict
import re

# --- 核心分析函式 ---

def clean_title(title):
    """移除 {{ }} 並清理標題"""
    if not title:
        return None
    return title.replace('{{', '').replace('}}', '')

def get_field_style_map(component):
    """
    從組件中提取欄位及其對應的樣式名稱。
    Returns: dict { 'column_key': 'StyleName' }
    """
    field_styles = {}
    comp_params = component.get("parameters", {})
    
    # 1. 針對「資訊展示板」
    if "contentSetting" in comp_params:
        for content in comp_params["contentSetting"].get("contents", []):
            # 數線型
            if "numberLineNumberParams" in content:
                k = content["numberLineNumberParams"].get("columnKey")
                if k: field_styles[k] = "數線數值 (NumberLine)"
            if "numberLineImageParams" in content:
                k = content["numberLineImageParams"].get("columnKey")
                if k: field_styles[k] = "數線圖片 (NumberLineImage)"

    # 2. 針對「表格類」
    if "tableSetting" in comp_params:
        for col in comp_params["tableSetting"].get("columns", []):
            content_type = col.get("content", {}).get("name", "Unknown")
            
            # 嘗試抓取各種可能的 key
            p = col.get("content", {}).get("parameters", {})
            
            keys_to_check = [
                p.get("text"),              # PureText
                p.get("columnKey"),         # NumberLine
                p.get("showingNumber"),     # ConditionFromBase
                p.get("target"),            # ConditionFromBase / StringToImage
                p.get("change"),            # StockChange
                p.get("quoteChange"),       # StockChange
                p.get("close"),             # StockPrice
                p.get("commKey")            # StockName
            ]
            
            for k in keys_to_check:
                if k and isinstance(k, str) and k not in ["名稱", "PureText", "ConditionalText"]:
                    # 如果已經有紀錄，用逗號串接樣式 (同一個欄位可能用多種樣式)
                    if k in field_styles:
                        if content_type not in field_styles[k]:
                            field_styles[k] += f", {content_type}"
                    else:
                        field_styles[k] = content_type

    return field_styles

def extract_data_sources(component, context, results, stats):
    """
    遞迴遍歷組件
    context: {
        'current_group': str,       # Tab 分頁 (如: 宏觀)
        'parent_name': str,         # 父層容器標題 (如: 美股大盤)
        'inside_main': bool,        # 是否在主容器內
        'just_entered_main': bool   # 標記剛進入主容器
    }
    """
    if not isinstance(component, dict): return

    stats['count'] += 1

    # --- 1. 上下文與命名邏輯更新 ---
    uuid = component.get("uuid", "")
    comp_params = component.get("parameters") or {}
    raw_title = comp_params.get("title")
    title = clean_title(raw_title)
    component_name = component.get("name", "Unknown")

    new_context = context.copy()

    # (A) 處理分組 (Group) - 宏觀/選股 etc.
    if uuid == "20000001":
        new_context["inside_main"] = True
    
    if context.get("inside_main") and context.get("just_entered_main"):
        if title: new_context["current_group"] = title
        new_context["just_entered_main"] = False 
    elif uuid == "20000001":
        new_context["just_entered_main"] = True

    # (B) 處理父層名稱 (Parent Name) - 美股大盤/總經數據 etc.
    # 如果當前容器有標題，且不是最底層的 UI 組件(如資訊展示板)，它就是 Parent
    # 我們排除一些純粹結構用的容器名稱
    is_structural_container = component_name in ["底部分頁容器", "分頁容器", "頁籤分頁容器", "垂直捲動容器"]
    
    if title and not is_structural_container:
        # 如果這是個有意義的標題容器，它就成為下一層的 Parent
        new_context["parent_name"] = title
    
    # 如果當前組件就是「資訊展示板」或「合併表格」，保留當前的 component_name 作為 Child
    # 但如果它自己有 title (很少見)，也可以用 title
    display_component_name = title if title else component_name

    # --- 2. 提取欄位樣式對照表 ---
    field_style_map = get_field_style_map(component)
    all_used_fields = set(field_style_map.keys())

    # --- 3. 提取資料來源 ---
    src_root = component.get("source") or []
    src_params = comp_params.get("source") or []
    read_src_root = component.get("readSources") or []
    read_src_params = comp_params.get("readSources") or []
    
    all_sources_list = []
    if isinstance(src_root, list): all_sources_list.extend(src_root)
    if isinstance(src_params, list): all_sources_list.extend(src_params)
    if isinstance(read_src_root, list): all_sources_list.extend(read_src_root)
    if isinstance(read_src_params, list): all_sources_list.extend(read_src_params)

    # --- 4. 處理並儲存結果 ---
    if all_sources_list:
        parent_display = new_context.get("parent_name", "通用")
        # 如果 Parent 和 Component 名字一樣，或 Component 是技術名稱，做一些修飾
        if display_component_name == "資訊展示板":
            final_name = f"{parent_display} / 資訊展示板"
        elif display_component_name == "合併表格":
            final_name = f"{parent_display} / 表格"
        elif display_component_name == parent_display:
            final_name = parent_display
        else:
            final_name = f"{parent_display} / {display_component_name}"

        for source in all_sources_list:
            if not isinstance(source, dict): continue
            
            source_name = source.get("name")
            params = source.get("sourceParameters", {})
            
            # ID 處理
            source_id_display = "Unknown"
            if source_name in ["dtno", "AddInfoDtno"]:
                source_id_display = params.get("dtnoNum", "N/A")
            elif "GoogleSheet" in str(source_name):
                s_name = params.get('sheetName', 'NoName')
                s_id = params.get('sheetId', 'NoID')
                source_id_display = f"{s_name} ({s_id})"
            elif source_name in ["USCommodity", "USStockCalculation", "CustomGroupRiskCalculator"]:
                source_id_display = "System/Calc"

            # 欄位過濾邏輯 (精確對應)
            source_defined_columns = params.get("columns", [])
            
            final_fields_display = []
            
            if source_defined_columns:
                # 情況 A: Source 有定義 columns (如 GoogleSheet, AddInfoDtno)
                # 我們只列出「Source 有定義」且「組件有用到」的交集，或者直接列出 Source 定義的
                # 通常以 Source 定義的為主，因為這是它提供的資料
                for col in source_defined_columns:
                    style = field_style_map.get(col, "Raw Data")
                    final_fields_display.append(f"{col} ({style})")
            else:
                # 情況 B: Source 沒定義 columns (如 dtno)
                # 這是最難的部分，因為我們不知道這個 dtno 到底吐什麼
                # 策略：顯示該組件用到的「所有」欄位，但在 UI 上標註 "Implied"
                for col in all_used_fields:
                    style = field_style_map.get(col, "Unknown")
                    final_fields_display.append(f"{col} ({style})")
                
                if not final_fields_display:
                    final_fields_display = ["(未偵測到明確欄位使用)"]

            results.append({
                "group": new_context.get("current_group", "其他"),
                "display_name": final_name,
                "source_type": source_name,
                "source_id": source_id_display,
                "fields_info": final_fields_display,
                "has_explicit_columns": bool(source_defined_columns)
            })

    # --- 5. 遞迴 ---
    if "subComponents" in component:
        for sub in component["subComponents"]:
            extract_data_sources(sub, new_context, results, stats)

def analyze_blueprint_content(json_content):
    try:
        data = json.loads(json_content)
    except json.JSONDecodeError:
        return [], 0

    results = []
    stats = {'count': 0}
    initial_context = {
        "current_group": "其他",
        "parent_name": None,
        "inside_main": False,
        "just_entered_main": False
    }
    
    for page in data.get("pages", []):
        extract_data_sources(page, initial_context, results, stats)

    return results, stats['count']

# --- Streamlit UI ---

st.set_page_config(page_title="Blueprint 分析器", layout="wide")

st.markdown("""
<style>
    .source-header { font-size: 14px; font-weight: bold; color: #555; }
    .source-id { font-family: monospace; color: #d63384; background-color: #f0f2f6; padding: 2px 4px; border-radius: 4px;}
    .field-tag { display: inline-block; background: #e0e0e0; color: #333; padding: 2px 6px; margin: 2px; border-radius: 4px; font-size: 12px; }
    .card-box { border: 1px solid #ddd; padding: 10px; border-radius: 8px; margin-bottom: 10px; background-color: #ffffff; }
</style>
""", unsafe_allow_html=True)

st.title("📊 Blueprint 資料源深度分析")

uploaded_file = st.file_uploader("上傳 blueprint.json", type="json")

if uploaded_file:
    bytes_data = uploaded_file.read()
    string_data = bytes_data.decode('utf-8')
    
    results, count = analyze_blueprint_content(string_data)
    
    if not results:
        st.error("無資料來源")
    else:
        st.info(f"掃描 {count} 組件，提取 {len(results)} 個資料節點")
        st.divider()

        # Grouping logic
        grouped_data = defaultdict(lambda: defaultdict(list))
        group_order = []
        
        for item in results:
            g = item['group']
            name = item['display_name']
            if g not in group_order: group_order.append(g)
            grouped_data[g][name].append(item)

        if "其他" in group_order:
            group_order.remove("其他")
            group_order.append("其他")

        # UI Rendering
        for group in group_order:
            with st.expander(f"📂 {group}", expanded=True):
                cards = grouped_data[group]
                
                # 桌面版 Grid Layout: 每行 3 個 Card
                cols = st.columns(3)
                card_items = list(cards.items())
                
                for idx, (card_name, sources) in enumerate(card_items):
                    with cols[idx % 3]:
                        with st.container():
                            # 卡片外框 (CSS hack not easy in pure Streamlit, using container)
                            st.markdown(f"#### {card_name}")
                            
                            for src in sources:
                                s_type = src['source_type']
                                s_id = src['source_id']
                                fields = src['fields_info']
                                
                                # Icon logic
                                icon = "📄"
                                if "dtno" in str(s_type): icon = "📈"
                                elif "Google" in str(s_type): icon = "☁️"
                                
                                # Summary string logic (for closed toggle)
                                summary_fields = fields[0].split('(')[0] if fields else ""
                                if len(fields) > 1: summary_fields += f"... (+{len(fields)-1})"
                                
                                label = f"{icon} **{s_type}**"
                                
                                with st.expander(label):
                                    st.markdown(f"**ID:** `{s_id}`")
                                    
                                    if not src['has_explicit_columns']:
                                        st.caption("⚠️ 此來源未定義 Columns，以下顯示組件用到的所有欄位：")
                                    
                                    # Render fields nicely
                                    for f in fields:
                                        # split name and style
                                        if "(" in f and ")" in f:
                                            fname = f.split(" (")[0]
                                            fstyle = f.split(" (")[1].replace(")", "")
                                            st.markdown(f"- **{fname}** <span style='color:gray; font-size:0.8em'>[{fstyle}]</span>", unsafe_allow_html=True)
                                        else:
                                            st.markdown(f"- {f}")

                            st.markdown("---")
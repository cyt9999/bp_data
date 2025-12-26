import json
import re
from collections import defaultdict

# ==========================================
#  共用工具函式 (Shared Utils)
# ==========================================

def clean_title(title):
    """移除 {{ }} 並清理標題"""
    if not title:
        return None
    return title.replace('{{', '').replace('}}', '')

def get_node_info(comp):
    """提取節點基本資訊，包含 Event ID"""
    uuid = comp.get("uuid", str(hash(str(comp))))
    name = comp.get("name", "Unknown")
    params = comp.get("parameters", {})
    title = clean_title(params.get("title"))
    event_id = comp.get("eventId")
    
    label = title if title else name
    
    return {
        "uuid": uuid,
        "name": name,
        "title": title,
        "label": label,
        "eventId": event_id
    }

def find_root_component(components, target_uuid="20000001"):
    """深度優先搜尋 (DFS) 尋找指定 UUID 的組件 (用於架構圖)"""
    for comp in components:
        if comp.get("uuid") == target_uuid:
            return comp
        if "subComponents" in comp:
            found = find_root_component(comp["subComponents"], target_uuid)
            if found:
                return found
    return None

# ==========================================
#  功能 A: 資料源分析 (For Data Source Analyzer)
# ==========================================

def get_field_style_map(component):
    """建立欄位與顯示樣式的對照表"""
    field_styles = {}
    comp_params = component.get("parameters", {})
    
    # 資訊展示板
    if "contentSetting" in comp_params:
        for content in comp_params["contentSetting"].get("contents", []):
            if "numberLineNumberParams" in content:
                k = content["numberLineNumberParams"].get("columnKey")
                if k: field_styles[k] = "數線數值 (NumberLine)"
            if "numberLineImageParams" in content:
                k = content["numberLineImageParams"].get("columnKey")
                if k: field_styles[k] = "數線圖片 (NumberLineImage)"

    # 表格類
    if "tableSetting" in comp_params:
        for col in comp_params["tableSetting"].get("columns", []):
            content_type = col.get("content", {}).get("name", "Unknown")
            p = col.get("content", {}).get("parameters", {})
            
            keys_to_check = [
                p.get("text"), p.get("columnKey"), p.get("showingNumber"), 
                p.get("target"), p.get("change"), p.get("quoteChange"), 
                p.get("close"), p.get("commKey")
            ]
            
            for k in keys_to_check:
                if k and isinstance(k, str) and k not in ["名稱", "PureText", "ConditionalText"]:
                    if k in field_styles and content_type not in field_styles[k]:
                        field_styles[k] += f", {content_type}"
                    else:
                        field_styles[k] = content_type
    return field_styles

def extract_data_sources_recursive(component, context, results, stats):
    """遞迴分析核心 (資料源)"""
    if not isinstance(component, dict): return
    stats['count'] += 1

    uuid = component.get("uuid", "")
    comp_params = component.get("parameters") or {}
    raw_title = comp_params.get("title")
    title = clean_title(raw_title)
    component_name = component.get("name", "Unknown")

    new_context = context.copy()

    # 處理分組
    if uuid == "20000001":
        new_context["inside_main"] = True
    
    if context.get("inside_main") and context.get("just_entered_main"):
        if title: new_context["current_group"] = title
        new_context["just_entered_main"] = False 
    elif uuid == "20000001":
        new_context["just_entered_main"] = True

    # 處理父層名稱
    is_structural = component_name in ["底部分頁容器", "分頁容器", "頁籤分頁容器", "垂直捲動容器"]
    if title and not is_structural:
        new_context["parent_name"] = title
    
    display_component_name = title if title else component_name

    # 提取資料
    field_style_map = get_field_style_map(component)
    all_used_fields = set(field_style_map.keys())

    src_root = component.get("source") or []
    src_params = comp_params.get("source") or []
    read_src_root = component.get("readSources") or []
    read_src_params = comp_params.get("readSources") or []
    
    all_sources = []
    if isinstance(src_root, list): all_sources.extend(src_root)
    if isinstance(src_params, list): all_sources.extend(src_params)
    if isinstance(read_src_root, list): all_sources.extend(read_src_root)
    if isinstance(read_src_params, list): all_sources.extend(read_src_params)

    if all_sources:
        parent_display = new_context.get("parent_name", "通用")
        if display_component_name == "資訊展示板":
            final_name = f"{parent_display} / 資訊展示板"
        elif display_component_name == "合併表格":
            final_name = f"{parent_display} / 表格"
        elif display_component_name == parent_display:
            final_name = parent_display
        else:
            final_name = f"{parent_display} / {display_component_name}"

        for source in all_sources:
            if not isinstance(source, dict): continue
            
            s_name = source.get("name")
            params = source.get("sourceParameters", {})
            
            s_id_disp = "Unknown"
            if s_name in ["dtno", "AddInfoDtno"]:
                s_id_disp = params.get("dtnoNum", "N/A")
            elif "GoogleSheet" in str(s_name):
                sn = params.get('sheetName', 'NoName')
                si = params.get('sheetId', 'NoID')
                s_id_disp = f"{sn} ({si})"
            elif s_name in ["USCommodity", "USStockCalculation"]:
                s_id_disp = "System/Calc"

            src_cols = params.get("columns", [])
            final_fields_disp = []
            
            if src_cols:
                for col in src_cols:
                    style = field_style_map.get(col, "Raw Data")
                    final_fields_disp.append(f"{col} ({style})")
            else:
                for col in all_used_fields:
                    style = field_style_map.get(col, "Unknown")
                    final_fields_disp.append(f"{col} ({style})")
                if not final_fields_disp:
                    final_fields_disp = ["(未偵測到明確欄位使用)"]

            results.append({
                "group": new_context.get("current_group", "其他"),
                "display_name": final_name,
                "source_type": s_name,
                "source_id": s_id_disp,
                "fields_info": final_fields_disp,
                "has_explicit_columns": bool(src_cols)
            })

    if "subComponents" in component:
        for sub in component["subComponents"]:
            extract_data_sources_recursive(sub, new_context, results, stats)

def analyze_blueprint_content(json_content):
    """[功能A入口] 分析資料來源"""
    try:
        data = json.loads(json_content)
    except:
        return [], 0

    results = []
    stats = {'count': 0}
    ctx = {
        "current_group": "其他",
        "parent_name": None,
        "inside_main": False,
        "just_entered_main": False
    }
    
    for page in data.get("pages", []):
        extract_data_sources_recursive(page, ctx, results, stats)

    return results, stats['count']


# ==========================================
#  功能 B: 架構與事件分析 (For App Structure)
# ==========================================

def get_app_structure(component, parent_id, current_depth, max_depth, nodes, edges):
    """遞迴建立 App 結構 (支援穿透邏輯)"""
    if current_depth > max_depth:
        return

    info = get_node_info(component)
    my_id = info["uuid"]
    my_name = info["name"]
    my_event = info["eventId"]
    my_title = info["title"]
    
    # 隱藏條件：是純排版容器 AND 沒有標題 AND 沒有 EventID
    is_layout_container = my_name in ["靜態容器", "垂直捲動容器", "水平捲動容器", "底部分頁容器", "分頁容器", "頁籤分頁容器"]
    should_hide = is_layout_container and (not my_title) and (not my_event)

    if my_id == "20000001":
        should_hide = False

    next_parent_id = parent_id if should_hide else my_id
    
    if not should_hide:
        nodes.append({
            "id": my_id,
            "label": info["label"],
            "type": my_name,
            "eventId": my_event,
            "has_title": bool(my_title)
        })
        if parent_id:
            edges.append((parent_id, my_id))
    
    next_depth = current_depth if should_hide else current_depth + 1
    
    if "subComponents" in component:
        for sub in component["subComponents"]:
            get_app_structure(sub, next_parent_id, next_depth, max_depth, nodes, edges)

def extract_all_events(component, path_str, event_list):
    """遞迴掃描所有的 Event ID"""
    info = get_node_info(component)
    
    current_path = path_str
    if info["label"]:
        current_path = f"{path_str} > {info['label']}"
    
    if info["eventId"]:
        event_list.append({
            "eventId": info["eventId"],
            "uuid": info["uuid"],
            "component": info["name"],
            "path": current_path
        })
        
    if "subComponents" in component:
        for sub in component["subComponents"]:
            extract_all_events(sub, current_path, event_list)

def analyze_structure_and_events(json_content, max_depth=3):
    """[功能B入口] 分析架構與事件"""
    try:
        data = json.loads(json_content)
    except:
        return None, None

    # 1. 找 Root
    root_node = find_root_component(data.get("pages", []), "20000001")
    if not root_node:
        return None, None

    # 2. 結構圖資料
    nodes = []
    edges = []
    get_app_structure(root_node, None, 1, max_depth, nodes, edges)
    
    graph_data = {"nodes": nodes, "edges": edges}

    # 3. Event 資料
    event_list = []
    extract_all_events(root_node, "App Entry", event_list)
        
    return graph_data, event_list
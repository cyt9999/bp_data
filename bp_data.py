import json
import re

# --- 共用工具函式 ---

def clean_title(title):
    """移除 {{ }} 並清理標題"""
    if not title: return None
    return title.replace('{{', '').replace('}}', '')

def get_node_info(comp):
    """提取節點基本資訊，包含 Event ID"""
    uuid = comp.get("uuid", str(hash(str(comp))))
    name = comp.get("name", "Unknown")
    params = comp.get("parameters", {})
    title = clean_title(params.get("title"))
    event_id = comp.get("eventId") # 抓取 eventId
    
    # 標籤顯示邏輯：如果有 Title 用 Title，否則用 Name
    label = title if title else name
    
    return {
        "uuid": uuid,
        "name": name,
        "title": title,
        "label": label,
        "eventId": event_id
    }

def find_root_component(components, target_uuid="20000001"):
    """
    深度優先搜尋 (DFS) 尋找指定 UUID 的組件
    """
    for comp in components:
        if comp.get("uuid") == target_uuid:
            return comp
        
        # 遞迴尋找
        if "subComponents" in comp:
            found = find_root_component(comp["subComponents"], target_uuid)
            if found:
                return found
    return None

# --- 1. 結構化圖表資料提取 (支援穿透邏輯) ---

def get_app_structure(component, parent_id, current_depth, max_depth, nodes, edges):
    """
    遞迴建立 App 結構，具備「穿透靜態容器」的邏輯。
    """
    if current_depth > max_depth:
        return

    info = get_node_info(component)
    my_id = info["uuid"]
    my_name = info["name"]
    my_event = info["eventId"]
    my_title = info["title"]
    
    # --- 關鍵邏輯：決定是否要「顯示」這個節點 ---
    # 隱藏條件：是純排版容器 AND 沒有標題 AND 沒有 EventID
    is_layout_container = my_name in ["靜態容器", "垂直捲動容器", "水平捲動容器", "底部分頁容器", "分頁容器"]
    should_hide = is_layout_container and (not my_title) and (not my_event)

    # 唯一的例外：如果是 Root (App入口)，絕對不能藏
    if my_id == "20000001":
        should_hide = False

    # 下一層的 Parent ID
    # 如果我被隱藏了，我的孩子就要認我的爸爸作父 (穿透)
    next_parent_id = parent_id if should_hide else my_id
    
    # 如果我不被隱藏，就將自己加入節點列表
    if not should_hide:
        nodes.append({
            "id": my_id,
            "label": info["label"],
            "type": my_name,
            "eventId": my_event,
            "has_title": bool(my_title)
        })
        # 建立與父親的連結
        if parent_id:
            edges.append((parent_id, my_id))
    
    # 繼續遞迴找孩子
    # 注意：如果我被隱藏了，深度(current_depth)不增加，這樣才能讓圖表顯示更多層
    next_depth = current_depth if should_hide else current_depth + 1
    
    if "subComponents" in component:
        for sub in component["subComponents"]:
            get_app_structure(sub, next_parent_id, next_depth, max_depth, nodes, edges)


# --- 2. Event ID 掃描 ---

def extract_all_events(component, path_str, event_list):
    """
    遞迴掃描所有的 Event ID
    """
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

# --- 主呼叫函式 ---

def analyze_structure_and_events(json_content, max_depth=3):
    try:
        data = json.loads(json_content)
    except:
        return None, None

    # 1. 先找到 Root 節點 (App 入口)
    # 搜尋範圍：data['pages']
    root_node = find_root_component(data.get("pages", []), "20000001")

    if not root_node:
        # 如果找不到入口，回傳空值，讓 UI 顯示錯誤
        return None, None

    # 2. 結構圖資料 (只從 Root 開始長)
    nodes = []
    edges = []
    get_app_structure(root_node, None, 1, max_depth, nodes, edges)
    
    graph_data = {"nodes": nodes, "edges": edges}

    # 3. Event 資料 (只抓 Root 底下的)
    event_list = []
    extract_all_events(root_node, "App Entry", event_list)
        
    return graph_data, event_list
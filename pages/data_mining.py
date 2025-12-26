import streamlit as st
import json
import pandas as pd
import re

st.set_page_config(page_title="埋點管理系統", layout="wide")
st.title("🎯 埋點管理與同步系統 (Strict Mode)")
st.markdown("僅針對 **容器類 (Container)** 與 **頁面 (Page)** 進行埋點管理，自動過濾無效 UUID 與圖表雜訊。")

# --- 核心邏輯函式 ---

def is_valid_event_id(eid):
    """判斷 Event ID 是否為有效的自定義 ID (非 UUID, 非空)"""
    if not eid: return False
    eid_str = str(eid).strip()
    if not eid_str: return False
    
    # 如果是 UUID 格式 (8-4-4-4-12)，視為無效 (系統自動生成的)
    uuid_pattern = r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-'
    if re.match(uuid_pattern, eid_str):
        return False
        
    return True

def get_node_info(comp):
    uuid = comp.get("uuid", str(hash(str(comp))))
    name = comp.get("name", "Unknown")
    title = comp.get("parameters", {}).get("title", "")
    title = title.replace('{{', '').replace('}}', '') if title else ""
    event_id = comp.get("eventId", "")
    return uuid, name, title, event_id

def collect_components_recursive(component, parent_path, data_list, depth=1, allowed_types=None):
    """
    遞迴收集組件
    allowed_types: 允許的組件名稱列表 (白名單)
    """
    uuid, name, title, event_id = get_node_info(component)
    
    label = title if title else name
    current_path = f"{parent_path} > {label}" if parent_path else label
    
    # --- 嚴格篩選邏輯 ---
    
    # 1. 判斷是否為「有效」的 Event ID (非 UUID)
    has_valid_event = is_valid_event_id(event_id)
    
    # 2. 組件類型檢查
    # 如果 component name 在白名單內，或是 Root Page (通常沒有 name 或 name 為 Page)
    is_target_type = False
    if allowed_types:
        if name in allowed_types:
            is_target_type = True
        # 特殊處理：有些 Page 的 name 是 None 或 "Page"
        if depth == 1: 
            is_target_type = True

    # 3. 排除垃圾標題 (K線, 圖例等)
    # 這裡可以根據您的需求擴充
    ignored_keywords = ["K線", "Bar", "Line", "圖例", "Legend", "Chart", "標題文本"]
    is_junk = False
    if title:
        for kw in ignored_keywords:
            if kw in title:
                is_junk = True
                break
    
    # 4. 決定是否收集
    # 邏輯：(是目標類型 AND 不是垃圾) OR (已經有有效埋點 - 防呆)
    should_collect = (is_target_type and not is_junk) or has_valid_event
        
    if should_collect:
        data_list.append({
            "uuid": uuid,
            "path": current_path,
            "component": name,
            "title": title,
            "eventId": event_id, 
            "depth": depth,
            "has_valid_event": has_valid_event
        })
        
    if "subComponents" in component:
        for sub in component["subComponents"]:
            collect_components_recursive(sub, current_path, data_list, depth + 1, allowed_types)

def update_blueprint_recursive(component, updates_dict):
    uuid = component.get("uuid")
    if uuid in updates_dict:
        new_id = updates_dict[uuid]
        if new_id and new_id.strip():
            component["eventId"] = new_id.strip()
        elif "eventId" in component:
            del component["eventId"]
    if "subComponents" in component:
        for sub in component["subComponents"]:
            update_blueprint_recursive(sub, updates_dict)

# --- UI 區域 ---

with st.sidebar:
    st.header("⚙️ 篩選設定")
    
    # 層級設定
    max_depth_val = st.slider("顯示最大層級 (Max Depth)", 1, 10, 4)
    
    # 組件白名單設定
    default_types = ["靜態容器", "頁籤分頁容器", "底部分頁容器", "分頁容器", "垂直捲動容器"]
    selected_types = st.multiselect(
        "只顯示以下組件類型 (白名單)",
        options=default_types + ["WebView", "NativeView", "水平捲動容器"],
        default=default_types
    )
    
    st.info("💡 提示：UUID 格式的 eventId 將被視為「未設定」。")

col1, col2 = st.columns([1, 1])

with col1:
    bp_file = st.file_uploader("1️⃣ 上傳 Blueprint.json", type="json")

with col2:
    event_json_str = st.text_area("2️⃣ 貼上 Event List JSON", height=150, placeholder='[{"name":"home_view","track_duration":true}, ...]')

if bp_file and event_json_str:
    try:
        bp_data = json.load(bp_file)
        ref_events = json.loads(event_json_str)
        ref_event_names = set(item.get("name") for item in ref_events)
        
        # 提取資料
        flat_components = []
        for page in bp_data.get("pages", []):
            collect_components_recursive(
                page, "", flat_components, 
                depth=1, 
                allowed_types=selected_types
            )
            
        df = pd.DataFrame(flat_components)
        
        if df.empty:
            st.warning("沒有找到符合條件的組件。")
            st.stop()

        # 過濾層級 (這裡過濾是為了顯示，但在 collect 時若有 valid event 已經保留了)
        # 我們希望：如果已經有 valid event，就算深度超過也要顯示 (防呆)
        # 如果是空的，則嚴格遵守深度限制
        df = df[ (df['depth'] <= max_depth_val) | (df['has_valid_event'] == True) ]

        # 狀態判斷
        def check_status(row):
            eid = row['eventId']
            is_valid = row['has_valid_event']
            
            # 關鍵修改：如果是無效 ID (UUID/Empty)，視為未設定
            if not is_valid:
                return "⚪ 未設定 (Empty/UUID)"
            
            if eid in ref_event_names:
                return "🟢 已同步"
            
            return "🔴 未在清單中 (需確認)"

        df['status'] = df.apply(check_status, axis=1)
        
        # 排序：未在清單 > 未設定 > 已同步
        df.sort_values(by=['status', 'depth'], ascending=[False, True], inplace=True)

        st.divider()
        st.subheader("3️⃣ 編輯埋點")
        
        filter_opt = st.radio(
            "過濾顯示:", 
            ["全部顯示", "🔴 僅顯示「未在清單中」", "⚪ 僅顯示「未設定」", "🟢 僅顯示「已同步」"], 
            horizontal=True
        )
        
        df_display = df
        if "未在清單" in filter_opt:
            df_display = df[df['status'].str.contains("未在清單")]
        elif "未設定" in filter_opt:
            df_display = df[df['status'].str.contains("未設定")]
        elif "已同步" in filter_opt:
            df_display = df[df['status'].str.contains("已同步")]

        edited_df = st.data_editor(
            df_display,
            column_config={
                "status": st.column_config.TextColumn("狀態", width="medium", disabled=True),
                "eventId": st.column_config.TextColumn("Event ID (編輯此處)", required=False),
                "component": st.column_config.TextColumn("組件類型", width="small", disabled=True),
                "title": st.column_config.TextColumn("標題/名稱", width="medium", disabled=True),
                "depth": st.column_config.NumberColumn("層級", width="small", disabled=True),
                "path": st.column_config.TextColumn("完整路徑", width="large", disabled=True),
                "uuid": st.column_config.TextColumn("UUID", width="small", disabled=True),
                "has_valid_event": None # 隱藏此輔助欄位
            },
            hide_index=True,
            use_container_width=True,
            key="editor"
        )

        st.divider()
        st.subheader("4️⃣ 確認並輸出")
        
        if st.button("💾 更新 Blueprint 並合併 Event List", type="primary"):
            
            updates = {}
            for index, row in edited_df.iterrows():
                uuid_key = row['uuid']
                new_eid = row['eventId']
                updates[uuid_key] = new_eid
            
            # 更新 BP
            new_bp_data = bp_data.copy()
            for page in new_bp_data.get("pages", []):
                update_blueprint_recursive(page, updates)
            
            # 重新掃描 BP 中所有的 Valid Event ID
            final_bp_events = set()
            def scan_valid_ids(comp, s):
                eid = comp.get("eventId")
                if is_valid_event_id(eid): # 只抓取非 UUID 的
                    s.add(eid)
                if "subComponents" in comp:
                    for sub in comp["subComponents"]: scan_valid_ids(sub, s)
            
            for page in new_bp_data.get("pages", []):
                scan_valid_ids(page, final_bp_events)
            
            # 合併清單
            final_list = list(ref_events)
            existing_names = set(r['name'] for r in final_list)
            
            added_count = 0
            for eid in final_bp_events:
                if eid not in existing_names:
                    final_list.append({"name": eid, "track_duration": True})
                    added_count += 1
            
            st.success(f"✅ 更新成功！已將 {added_count} 個新埋點加入輸出清單。")
            
            c1, c2 = st.columns(2)
            with c1:
                st.download_button(
                    "📥 下載 blueprint_updated.json",
                    data=json.dumps(new_bp_data, ensure_ascii=False, indent=2),
                    file_name="blueprint_updated.json",
                    mime="application/json"
                )
            with c2:
                st.text_area("📋 最終 Event List JSON", value=json.dumps(final_list, ensure_ascii=False), height=100)

    except json.JSONDecodeError:
        st.error("JSON 格式錯誤。")
    except Exception as e:
        st.error(f"Error: {e}")
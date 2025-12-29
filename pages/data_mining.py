import streamlit as st
import sys
import os
import json
import pandas as pd

try:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(current_dir)
    if root_dir not in sys.path:
        sys.path.insert(0, root_dir)
except:
    pass

from bp_data import render_global_sidebar, get_blueprint_data, get_node_info

st.set_page_config(page_title="埋點管理", layout="wide")
render_global_sidebar()

st.title("🎯 埋點管理 (Data Mining)")

blueprint_data = get_blueprint_data()

if not blueprint_data:
    st.warning("⚠️ 請先在左側上傳 Blueprint。")
    st.stop()

# 收集節點
all_nodes = []
def collect_nodes(node, path=""):
    info = get_node_info(node)
    current_path = f"{path} > {info['label']}" if path else info['label']
    if info['name'] not in ["Unknown"]:
        all_nodes.append({
            "Path": current_path,
            "Component": info['name'],
            "Title": info['title'],
            "Event ID": info['eventId'],
            "UUID": info['uuid'],
            "Has ID": bool(info['eventId'])
        })
    for sub in node.get('subComponents', []) + node.get('pages', []):
        collect_nodes(sub, current_path)

collect_nodes(blueprint_data)
df = pd.DataFrame(all_nodes)

# 控制列
with st.container(border=True):
    c1, c2, c3 = st.columns([1, 1, 2])
    with c1:
        filter_type = st.multiselect("篩選類型", options=df['Component'].unique())
    with c2:
        filter_status = st.radio("篩選狀態", ["全部", "有埋點", "無埋點"], horizontal=True)
    with c3:
        compare_json = st.text_area("📋 (選填) 貼上 Event JSON", height=68)

# 篩選邏輯
if filter_type: df = df[df['Component'].isin(filter_type)]
if filter_status == "有埋點": df = df[df['Has ID'] == True]
elif filter_status == "無埋點": df = df[df['Has ID'] == False]

if compare_json:
    try:
        ref_events = json.loads(compare_json)
        ref_names = set(e.get('name') for e in ref_events)
        df['Sync'] = df.apply(lambda r: "🟢" if r['Event ID'] in ref_names else ("🔴" if r['Event ID'] else "⚪"), axis=1)
        st.success("JSON 比對成功")
    except:
        st.error("JSON 格式錯誤")

st.data_editor(df, use_container_width=True, hide_index=True, height=600)
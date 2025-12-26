import streamlit as st
import pandas as pd
from collections import defaultdict
import sys
import os

# 確保可以匯入根目錄的 bp_data
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from bp_data import analyze_blueprint_content

st.set_page_config(page_title="資料源分析", layout="wide")

st.markdown("""
<style>
    .stExpander { border: 1px solid #ddd; border-radius: 8px; margin-bottom: 5px; }
</style>
""", unsafe_allow_html=True)

st.title("📊 Blueprint 資料源深度分析")

uploaded_file = st.file_uploader("上傳 blueprint.json", type="json")

if uploaded_file:
    string_data = uploaded_file.read().decode('utf-8')
    results, count = analyze_blueprint_content(string_data)
    
    if not results:
        st.error("分析完成但未找到資料來源。")
    else:
        st.success(f"掃描 {count} 個組件，提取 {len(results)} 個資料節點")
        st.divider()

        # 分組處理
        grouped = defaultdict(lambda: defaultdict(list))
        groups = []
        for item in results:
            g = item['group']
            if g not in groups: groups.append(g)
            grouped[g][item['display_name']].append(item)

        if "其他" in groups:
            groups.remove("其他")
            groups.append("其他")

        # 渲染 UI (Grid Layout)
        for group in groups:
            with st.expander(f"📂 {group}", expanded=True):
                cards = grouped[group]
                cols = st.columns(3) # 3欄位排版
                
                for idx, (card_name, sources) in enumerate(cards.items()):
                    with cols[idx % 3]:
                        with st.container(border=True):
                            st.markdown(f"#### {card_name}")
                            for src in sources:
                                icon = "☁️" if "Google" in src['source_type'] else "📈"
                                label = f"{icon} **{src['source_type']}**"
                                
                                with st.expander(label):
                                    st.markdown(f"**ID:** `{src['source_id']}`")
                                    if not src['has_explicit_columns']:
                                        st.caption("⚠️ 推斷欄位 (Source未定義)")
                                    
                                    for f in src['fields_info']:
                                        # 防呆切割邏輯
                                        if " (" in f and f.endswith(")"):
                                            try:
                                                parts = f.rsplit(" (", 1)
                                                fname, fstyle = parts[0], parts[1].rstrip(")")
                                                st.markdown(f"- **{fname}** <span style='color:#666;font-size:0.8em'>[{fstyle}]</span>", unsafe_allow_html=True)
                                            except:
                                                st.markdown(f"- {f}")
                                        else:
                                            st.markdown(f"- {f}")
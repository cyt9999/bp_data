import streamlit as st
import sys
import os
from collections import defaultdict

# --- 絕對路徑修正 ---
try:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(current_dir)
    if root_dir not in sys.path:
        sys.path.insert(0, root_dir)
except:
    pass

# 匯入共用模組
from bp_data import render_global_sidebar, get_blueprint_data, analyze_blueprint_content

# --- 頁面設定 ---
st.set_page_config(page_title="資料源分析", layout="wide")

# CSS 優化 Expander
st.markdown("""
<style>
    .stExpander { border: 1px solid #ddd; border-radius: 8px; margin-bottom: 5px; }
</style>
""", unsafe_allow_html=True)

# 1. 呼叫全域 Sidebar (共用上傳)
render_global_sidebar()

st.title("📊 Blueprint 資料源深度分析")

# 2. 從全域取得資料
blueprint_data = get_blueprint_data()

if blueprint_data:
    # 直接傳入 dict 資料
    results, count = analyze_blueprint_content(blueprint_data)
    
    if not results:
        st.warning("分析完成，但在該 Blueprint 中未找到明確的資料來源定義。")
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
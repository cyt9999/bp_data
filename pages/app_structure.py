import streamlit as st
import sys
import os

# 嘗試匯入 ECharts
try:
    from streamlit_echarts import st_echarts
    HAS_ECHARTS = True
except ImportError:
    HAS_ECHARTS = False

try:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(current_dir)
    if root_dir not in sys.path:
        sys.path.insert(0, root_dir)
except:
    pass

from bp_data import render_global_sidebar, get_blueprint_data, get_echarts_tree_data

st.set_page_config(page_title="App 架構導覽", layout="wide")
render_global_sidebar()

st.title("🗺️ App Sitemap (Smooth Tree)")

if not HAS_ECHARTS:
    st.error("❌ 需要安裝 `streamlit-echarts`。")
    st.code("pip install streamlit-echarts", language="bash")
    st.stop()

blueprint_data = get_blueprint_data()

if not blueprint_data:
    st.warning("⚠️ 請先在左側上傳 Blueprint。")
    st.stop()

# --- 控制項 ---
with st.container(border=True):
    c1, c2 = st.columns([1, 3])
    with c1:
        initial_depth = st.slider("初始展開層級", 1, 5, 2, help="重新整理後預設展開的深度")
    with c2:
        st.info("💡 提示：此圖表支援點擊展開/收合，且**不會**刷新頁面。滑鼠懸停可查看 Event ID。")

# --- 資料轉換 ---
tree_data = get_echarts_tree_data(
    blueprint_data, 
    root_uuid="20000001", 
    initial_depth=initial_depth
)

if not tree_data:
    st.error("無法解析架構資料。")
    st.stop()

# --- ECharts 設定 ---
option = {
    "tooltip": {
        "trigger": "item",
        "triggerOn": "mousemove",
        # Hover 顯示內容：{b}為名稱, {c}為 value (Event ID)
        "formatter": "<strong>{b}</strong><br/>Event ID: {c}"
    },
    "series": [
        {
            "type": "tree",
            "data": [tree_data],

            "top": "5%",
            "left": "7%",
            "bottom": "5%",
            "right": "20%",

            "symbol": "roundRect", # 圓角矩形
            "symbolSize": [140, 35], # 寬, 高

            # 垂直佈局 (Top to Bottom) 改為 水平佈局 (Left to Right)
            "orient": "LR",  
            
            "label": {
                "position": "inside", # 文字在框內
                "verticalAlign": "middle",
                "align": "center",
                "fontSize": 12,
                "color": "#333" # 文字顏色 (黑)
            },

            "leaves": {
                "label": {
                    "position": "inside",
                    "verticalAlign": "middle",
                    "align": "center"
                }
            },

            "expandAndCollapse": True, # 開啟前端互動
            "animationDuration": 550,
            "animationDurationUpdate": 750
        }
    ]
}

# --- 渲染 ---
# height 設定高一點，讓垂直樹有空間伸展
st_echarts(options=option, height="900px")
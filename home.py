import streamlit as st

# 設定頁面資訊
st.set_page_config(
    page_title="Developer Tools Portal",
    page_icon="🛠️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定義 CSS 讓卡片漂亮一點 (選擇性)
st.markdown("""
<style>
    .stContainer {
        transition: transform 0.2s;
    }
    .stContainer:hover {
        transform: scale(1.02);
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)

# 首頁標題
st.title("🛠️ Developer Tools Portal")
st.markdown("歡迎使用內部開發者工具集，請從左側選單或下方卡片選擇工具。")
st.divider()

# --- 定義工具清單 ---
# 這裡定義您的工具資訊，方便統一管理卡片
tools = [
    {
        "title": "Blueprint 資料源分析器",
        "icon": "📊",
        "desc": "上傳 blueprint.json，自動解析 dtno、GoogleSheet 等資料來源與欄位對應。",
        "page": "pages/bp_analyzer.py", # 對應 pages 資料夾內的檔名
        "btn_label": "開始分析"
    },
    {
    "title": "埋點管理",
    "icon": "🎯",
    "desc": "檢查與更新埋點。",
    "page": "pages/data_mining.py",
    "btn_label": "查看架構"
    },{
    "title": "App 架構圖生成器",
    "icon": "🗺️",
    "desc": "視覺化呈現 App 的 IA 架構與導航層級。",
    "page": "pages/app_structure.py",
    "btn_label": "查看架構"
    }
]

# --- 渲染卡片 (Grid Layout) ---
# 設定每行顯示幾個卡片 (例如 2 個)
cols_per_row = 2
cols = st.columns(cols_per_row)

for index, tool in enumerate(tools):
    with cols[index % cols_per_row]:
        # 使用 container 畫出卡片外框
        with st.container(border=True):
            col_icon, col_text = st.columns([1, 5])
            
            with col_icon:
                st.markdown(f"<h1 style='text-align: center;'>{tool['icon']}</h1>", unsafe_allow_html=True)
            
            with col_text:
                st.subheader(tool['title'])
                st.write(tool['desc'])
                
                # 這裡是最重要的跳轉按鈕
                st.page_link(
                    tool['page'], 
                    label=tool['btn_label'], 
                    icon="👉",
                    use_container_width=True 
                )

# 側邊欄額外資訊
with st.sidebar:
    st.info("💡 提示：點擊左上角的 'X' 或 '>' 按鈕可以收合/展開側邊選單。")
    st.markdown("---")
    st.caption("v1.0.0 | Created with Streamlit")
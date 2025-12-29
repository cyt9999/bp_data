import streamlit as st

# 設定頁面資訊
st.set_page_config(
    page_title="Developer Tools Portal",
    page_icon="🛠️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS 優化 (卡片懸停特效 + 等高排版) ---
st.markdown("""
<style>
    /* 卡片懸停特效 */
    .stContainer {
        transition: transform 0.2s, box-shadow 0.2s;
    }
    div[data-testid="stVerticalBlockBorderWrapper"]:hover {
        transform: translateY(-5px);
        box-shadow: 0 6px 12px rgba(0,0,0,0.15);
        border-color: #FF4B4B !important; /* Streamlit Primary Color */
    }

    /* === 卡片等高 CSS Hack === */
    
    /* 1. 將每個 Column 轉為 Flex Container，方向為垂直 */
    [data-testid="column"] {
        display: flex;
        flex-direction: column;
    }
    
    /* 2. 讓 Column 內部的 div (包含垂直區塊) 佔滿空間 */
    [data-testid="column"] > div {
        flex: 1;
        display: flex;
        flex-direction: column;
    }
    
    /* 3. 讓帶有 Border 的 Container 自動伸展 (flex-grow) */
    [data-testid="stVerticalBlockBorderWrapper"] {
        flex: 1;
        display: flex;
        flex-direction: column;
    }
    
    /* 4. 確保內容物撐開 */
    [data-testid="stVerticalBlockBorderWrapper"] > div {
        flex: 1;
    }
</style>
""", unsafe_allow_html=True)

# 首頁標題
st.title("🛠️ Developer Tools Portal")
st.markdown("歡迎使用內部開發者工具集，請從左側選單或下方卡片選擇工具。")
st.divider()

# --- 定義工具清單 ---
tools = [
    {
        "title": "Blueprint 資料源分析器",
        "icon": "📊",
        "desc": "上傳 blueprint.json，自動解析 dtno、GoogleSheet 等資料來源與欄位對應。",
        "page": "pages/bp_analyzer.py",
        "btn_label": "開始分析"
    },
    {
        "title": "Deep Link 生成器",
        "icon": "🔗",
        "desc": "上傳藍圖，自動產生 App 跳轉連結 (Deep Link)，支援動態參數與社團預設。",
        "page": "pages/deep_link_tool.py",
        "btn_label": "產生連結"
    },
    {
        "title": "埋點管理",
        "icon": "🎯",
        "desc": "檢查與更新埋點，支援自動過濾無效 UUID 與圖表雜訊。",
        "page": "pages/data_mining.py",
        "btn_label": "檢查埋點"
    },
    {
        "title": "App 架構圖生成器",
        "icon": "🗺️",
        "desc": "視覺化呈現 App 的 IA 架構與導航層級，支援圖片下載。",
        "page": "pages/app_structure.py",
        "btn_label": "查看架構"
    }
]

# --- 渲染卡片 (Grid Layout) ---
cols_per_row = 2
cols = st.columns(cols_per_row)

for index, tool in enumerate(tools):
    # 根據索引分配到對應的 column
    with cols[index % cols_per_row]:
        # 使用 container 畫出卡片外框 (CSS 會強制它等高)
        with st.container(border=True):
            col_icon, col_text = st.columns([1, 5])
            
            with col_icon:
                st.markdown(f"<h1 style='text-align: center; margin: 0;'>{tool['icon']}</h1>", unsafe_allow_html=True)
            
            with col_text:
                st.subheader(tool['title'])
                st.write(tool['desc'])
                
            # 將按鈕推到底部 (選用，如果希望按鈕對齊底部可以使用 st.write("") 填充)
            # st.markdown("<div style='margin-top: auto;'></div>", unsafe_allow_html=True)
            
            st.page_link(
                tool['page'], 
                label=tool['btn_label'], 
                icon="👉",
                use_container_width=True 
            )

# 側邊欄額外資訊
with st.sidebar:
    st.info("💡 提示：所有工具皆共用同一份上傳的 Blueprint 檔案。")
    st.markdown("---")
    st.caption("v1.1.0 | Created with Streamlit")
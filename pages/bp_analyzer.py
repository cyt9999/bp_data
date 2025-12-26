import streamlit as st
import sys
import os

# --- 絕對路徑修正 (強制加入根目錄) ---
try:
    # 1. 取得當前檔案 (bp_analyzer.py) 的絕對路徑
    current_file_path = os.path.abspath(__file__)
    # 2. 取得 pages 資料夾路徑
    pages_dir = os.path.dirname(current_file_path)
    # 3. 取得根目錄路徑 (pages 的上一層)
    root_dir = os.path.dirname(pages_dir)
    
    # 4. 強制將根目錄插入到系統搜尋路徑的第一位
    if root_dir not in sys.path:
        sys.path.insert(0, root_dir)

    # 5. 嘗試匯入
    from bp_data import analyze_blueprint_content

except ImportError as e:
    st.error(f"❌ 嚴重錯誤：無法匯入 `bp_data`。")
    st.warning("系統偵測到的路徑資訊如下，請截圖給工程師（或檢查檔名）：")
    
    # 顯示除錯資訊
    st.write(f"📂 預期根目錄: `{root_dir}`")
    
    # 檢查根目錄下到底有哪些檔案
    try:
        files_in_root = os.listdir(root_dir)
        st.write(f"📂 根目錄下的檔案列表: {files_in_root}")
        
        if "bp_data.py" in files_in_root:
            st.success("✅ `bp_data.py` 確實存在於根目錄中，但 Python 載入失敗 (可能是該檔案內部有語法錯誤)。")
        else:
            st.error("❌ 根目錄中 **找不到** `bp_data.py`。請檢查檔名大小寫 (Linux系統區分大小寫)。")
            # 常見錯誤檢查
            if "bp_data.py.txt" in files_in_root:
                st.info("💡 發現 `bp_data.py.txt`，請移除 .txt 副檔名。")
    except Exception as ex:
        st.error(f"無法讀取目錄: {ex}")
        
    st.stop()

# --- 以下是原本的程式碼 (保持不變) ---
import pandas as pd
from collections import defaultdict

# --- 頁面設定 ---
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
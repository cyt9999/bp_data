import streamlit as st
import pandas as pd
import graphviz
import sys
import os

# 匯入核心邏輯
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from bp_data import analyze_structure_and_events

st.set_page_config(page_title="App 架構導覽", layout="wide")

st.title("🗺️ App 架構導覽 (Sitemap)")

# 側邊欄設定
with st.sidebar:
    st.header("設定")
    depth = st.slider("顯示層級深度", 1, 10, 5)
    st.info("💡 邏輯說明：\n\n僅顯示從 **App 入口** 延伸出的有效節點。\n\n圖表僅呈現架構，詳細資料請見下方表格。")
    st.divider()
    st.markdown("### 圖例")
    st.markdown("🟡 **雙圈**：App 入口")
    st.markdown("📂 **藍色**：分頁/導航容器")
    st.markdown("⬜ **灰色**：一般頁面/組件")

uploaded_file = st.file_uploader("📂 請先上傳 blueprint.json", type="json")

if uploaded_file:
    bp_text = uploaded_file.read().decode("utf-8")
    
    # 執行分析
    graph_data, bp_events = analyze_structure_and_events(bp_text, max_depth=depth)
    
    if graph_data is None:
        st.error("❌ 分析失敗：找不到 App 入口節點 (UUID: 20000001)。")
        st.stop()
    
    if not graph_data["nodes"]:
        st.warning("⚠️ 掃描完成，但沒有產生任何節點。請檢查深度設定。")
        st.stop()

    # --- 建立 Tabs ---
    tab1, tab2 = st.tabs(["🗺️ 架構視圖", "🔍 Event ID 覆蓋檢查"])

    # === Tab 1: 架構圖 + 表格 ===
    with tab1:
        st.caption(f"目前顯示深度: {depth}")
        
        # 1. 建立 Graphviz 物件
        dot = graphviz.Digraph(comment='App Structure')
        dot.attr(rankdir='LR') # 橫向 (左到右)
        
        # 字型設定 (支援中文)
        font_config = 'Microsoft JhengHei, Noto Sans CJK TC, sans-serif'
        dot.attr('node', fontname=font_config, shape='box', style='filled')
        dot.attr('edge', fontname=font_config)
        
        # 2. 繪製節點 (已移除 Event ID 的紅色標記邏輯)
        for node in graph_data["nodes"]:
            n_id = node["id"]
            n_label = node["label"]
            
            # 樣式邏輯 (純淨版)
            fill = "#F0F0F0" # 預設灰
            shape = "box"
            style = "filled,rounded"
            border_color = "black"
            font_color = "black"
            pen_width = "1"
            
            # 特殊節點樣式
            if n_id == "20000001": # Root
                fill = "#FFD700"
                shape = "doubleoctagon"
                display_label = f"📱 {n_label}"
            elif node["type"] in ["分頁容器", "底部分頁容器", "頁籤分頁容器"]:
                fill = "#ADD8E6" # 藍色導航
                shape = "folder"
                display_label = n_label
            elif not node["has_title"]: # 穿透的中間層
                style = "dashed"
                fill = "#FFFFFF"
                display_label = n_label
            else:
                display_label = n_label

            dot.node(n_id, display_label, fillcolor=fill, shape=shape, style=style, color=border_color, fontcolor=font_color, penwidth=pen_width)

        # 3. 繪製連線
        for parent, child in graph_data["edges"]:
            dot.edge(parent, child)

        # 4. 顯示圖表
        st.graphviz_chart(dot, use_container_width=True)

        # 5. 下載按鈕
        col_dl1, col_dl2 = st.columns([1, 5])
        try:
            png_bytes = dot.pipe(format='png')
            with col_dl1:
                st.download_button("📥 下載架構圖 (PNG)", data=png_bytes, file_name="app_structure.png", mime="image/png")
        except:
            pass

        st.divider()

        # 6. 結構表格 (新增功能)
        st.subheader("📑 架構清單明細")
        
        # 將 Graph Data 轉為 DataFrame
        df_nodes = pd.DataFrame(graph_data["nodes"])
        
        if not df_nodes.empty:
            # 整理欄位顯示
            df_display = df_nodes[["label", "type", "id", "eventId"]]
            df_display.columns = ["組件名稱/標題", "組件類型", "UUID", "綁定 Event ID"]
            
            # 顯示表格
            st.dataframe(
                df_display,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "組件名稱/標題": st.column_config.TextColumn("名稱", width="medium"),
                    "組件類型": st.column_config.TextColumn("類型", width="small"),
                    "UUID": st.column_config.TextColumn("UUID", width="small"),
                    "綁定 Event ID": st.column_config.TextColumn("目前埋點 (參考)", width="medium"),
                }
            )
            
            # CSV 下載
            csv = df_display.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 下載此表格 (CSV)", data=csv, file_name="structure_list.csv", mime="text/csv")

    # === Tab 2: 埋點健檢 (保留原本功能) ===
    with tab2:
        st.subheader("埋點覆蓋率檢查")
        st.info("此處僅檢查圖表中顯示的路徑 (有效路徑)。")
        
        csv_file = st.file_uploader("📂 上傳 '(新)投資talk君事件埋點 - uuid 對照表.csv'", type="csv")
        
        if csv_file:
            df_bp = pd.DataFrame(bp_events)
            if df_bp.empty:
                st.warning("目前路徑中無 Event ID")
            else:
                try:
                    df_csv = pd.read_csv(csv_file)
                    df_csv.columns = [c.strip() for c in df_csv.columns]
                    
                    if "eventId" in df_csv.columns:
                        target_events = set(df_csv["eventId"].dropna().astype(str))
                        bp_events_set = set(df_bp["eventId"].dropna().astype(str))
                        
                        missing_in_bp = target_events - bp_events_set
                        extra_in_bp = bp_events_set - target_events
                        common = target_events & bp_events_set
                        
                        c1, c2, c3 = st.columns(3)
                        c1.metric("✅ 匹配成功", len(common))
                        c2.metric("❌ 疑似漏埋", len(missing_in_bp))
                        c3.metric("❓ 未登記", len(extra_in_bp))
                        
                        col_l, col_r = st.columns(2)
                        with col_l:
                            st.error(f"❌ 漏埋清單 ({len(missing_in_bp)})")
                            if missing_in_bp:
                                st.dataframe(df_csv[df_csv["eventId"].isin(missing_in_bp)][["eventId", "uuid"]], use_container_width=True)
                        with col_r:
                            st.warning(f"❓ 未登記清單 ({len(extra_in_bp)})")
                            if extra_in_bp:
                                st.dataframe(df_bp[df_bp["eventId"].isin(extra_in_bp)][["eventId", "component", "path"]], use_container_width=True)
                    else:
                        st.error("CSV 格式錯誤：找不到 eventId 欄位")
                except Exception as e:
                    st.error(f"Error: {e}")
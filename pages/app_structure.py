import streamlit as st
import pandas as pd
import graphviz
import sys
import os

# 匯入核心邏輯
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from bp_data import analyze_structure_and_events

st.set_page_config(page_title="App 架構與埋點", layout="wide")

st.title("🗺️ App 架構與埋點檢查")

# 側邊欄設定
with st.sidebar:
    st.header("設定")
    depth = st.slider("顯示層級深度", 1, 10, 5)
    st.info("💡 邏輯說明：\n\n僅顯示從 **App 入口 (UUID: 20000001)** 延伸出的節點。\n\n已自動隱藏無標題的排版容器。")
    st.divider()
    st.markdown("### 圖例")
    st.markdown("🟡 **雙圈**：App 入口")
    st.markdown("🔴 **紅框/紅字**：該節點有埋點 (Event)")
    st.markdown("📂 **藍色**：分頁/導航容器")

uploaded_file = st.file_uploader("📂 請先上傳 blueprint.json", type="json")

if uploaded_file:
    bp_text = uploaded_file.read().decode("utf-8")
    
    # 執行分析
    graph_data, bp_events = analyze_structure_and_events(bp_text, max_depth=depth)
    
    if graph_data is None:
        st.error("❌ 分析失敗：找不到 App 入口節點 (UUID: 20000001)。請確認此 Blueprint 包含該節點。")
        st.stop()
    
    if not graph_data["nodes"]:
        st.warning("⚠️ 掃描完成，但沒有產生任何節點。請檢查深度設定或 JSON 結構。")
        st.stop()

    # --- 建立 Tabs ---
    tab1, tab2 = st.tabs(["🗺️ IA 架構圖 (導覽)", "🔍 Event ID 埋點健檢"])

    # === Tab 1: 架構圖 ===
    with tab1:
        st.caption(f"目前顯示深度: {depth} (從 App 入口開始)")
        
        # 建立 Graphviz 物件
        dot = graphviz.Digraph(comment='App Structure')
        dot.attr(rankdir='LR') # 由左至右
        dot.attr('node', fontname='Microsoft JhengHei', shape='box', style='filled')
        
        # 繪製節點
        for node in graph_data["nodes"]:
            n_id = node["id"]
            n_label = node["label"]
            n_event = node["eventId"]
            
            # 樣式邏輯
            fill = "#F0F0F0" # 預設灰
            shape = "box"
            style = "filled,rounded"
            border_color = "black"
            font_color = "black"
            pen_width = "1"
            
            # 顯示標籤增強 (移除 Event ID 文字，僅保留視覺提示)
            display_label = n_label
            
            if n_event:
                # display_label += f"\n({n_event})"  <-- 已移除此行，不顯示 ID
                border_color = "red"     # 框線變紅
                font_color = "#B22222"   # 文字變深紅
                fill = "#FFF0F0"         # 背景淡紅
                pen_width = "2"          # 框線加粗

            if n_id == "20000001": # Root
                fill = "#FFD700"
                shape = "doubleoctagon"
                display_label = "📱 App 入口"
                border_color = "black"
                font_color = "black"
            elif node["type"] in ["分頁容器", "底部分頁容器", "頁籤分頁容器"]:
                fill = "#ADD8E6" # 藍色導航
                shape = "folder"
            elif not node["has_title"] and not n_event:
                style = "dashed"
                fill = "#FFFFFF"

            dot.node(n_id, display_label, fillcolor=fill, shape=shape, style=style, color=border_color, fontcolor=font_color, penwidth=pen_width)

        # 繪製連線
        for parent, child in graph_data["edges"]:
            dot.edge(parent, child)

        # 顯示圖表
        st.graphviz_chart(dot, use_container_width=True)

        # --- 新增下載按鈕 ---
        st.divider()
        col_dl1, col_dl2 = st.columns(2)
        
        try:
            # 渲染成 PNG 的二進位資料
            png_bytes = dot.pipe(format='png')
            
            with col_dl1:
                st.download_button(
                    label="📥 下載架構圖 (PNG 圖片)",
                    data=png_bytes,
                    file_name="app_structure.png",
                    mime="image/png"
                )
            
            # 渲染成 SVG (向量圖，無限放大不失真)
            svg_bytes = dot.pipe(format='svg')
            with col_dl2:
                st.download_button(
                    label="📥 下載架構圖 (SVG 向量圖)",
                    data=svg_bytes,
                    file_name="app_structure.svg",
                    mime="image/svg"
                )
        except Exception as e:
            st.warning("⚠️ 無法產生下載檔案 (可能缺少系統 Graphviz 函式庫)。但在網頁上檢視是正常的。")

    # === Tab 2: 埋點健檢 ===
    with tab2:
        st.subheader("埋點覆蓋率檢查 (僅限與入口相連的頁面)")
        
        csv_file = st.file_uploader("📂 上傳 '(新)投資talk君事件埋點 - uuid 對照表.csv'", type="csv")
        
        if csv_file:
            # 1. 準備 Blueprint 的資料
            df_bp = pd.DataFrame(bp_events)
            if df_bp.empty:
                st.warning("Blueprint (從入口延伸的路徑中) 沒有發現任何 Event ID。")
            else:
                st.info(f"有效路徑中共掃描到 {len(df_bp)} 個埋點。")

                # 2. 準備 CSV 的資料
                try:
                    df_csv = pd.read_csv(csv_file)
                    df_csv.columns = [c.strip() for c in df_csv.columns]
                    
                    if "eventId" in df_csv.columns:
                        target_events = set(df_csv["eventId"].dropna().astype(str))
                        bp_events_set = set(df_bp["eventId"].dropna().astype(str))
                        
                        # 3. 比對邏輯
                        missing_in_bp = target_events - bp_events_set
                        extra_in_bp = bp_events_set - target_events
                        common = target_events & bp_events_set
                        
                        # 4. 顯示結果 metrics
                        c1, c2, c3 = st.columns(3)
                        c1.metric("✅ 匹配成功", len(common))
                        c2.metric("❌ 疑似漏埋 (BP缺)", len(missing_in_bp))
                        c3.metric("❓ 未登記 (BP多)", len(extra_in_bp))
                        
                        st.divider()
                        
                        col_l, col_r = st.columns(2)
                        
                        with col_l:
                            st.error(f"❌ Excel 有規劃，但有效路徑中找不到 ({len(missing_in_bp)} 筆)")
                            if missing_in_bp:
                                st.dataframe(df_csv[df_csv["eventId"].isin(missing_in_bp)][["eventId", "uuid"]], use_container_width=True)
                            else:
                                st.success("完美！所有規劃的埋點都存在。")
                                
                        with col_r:
                            st.warning(f"❓ BP 有效路徑有埋，但 Excel 沒記錄 ({len(extra_in_bp)} 筆)")
                            if extra_in_bp:
                                st.dataframe(df_bp[df_bp["eventId"].isin(extra_in_bp)][["eventId", "component", "path"]], use_container_width=True)
                            else:
                                st.success("沒有多餘的未登記埋點。")

                    else:
                        st.error("CSV 格式不符：找不到 `eventId` 欄位。")
                        
                except Exception as e:
                    st.error(f"讀取 CSV 失敗: {e}")
        else:
            if bp_events:
                st.write("👇 有效路徑中現有的 Event List:")
                st.dataframe(pd.DataFrame(bp_events), use_container_width=True)
            else:
                st.write("目前路徑中無 Event ID")
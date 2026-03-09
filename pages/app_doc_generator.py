import streamlit as st
import re
import json
import zipfile
import os
from collections import OrderedDict
from bp_data import render_global_sidebar, get_blueprint_data, clean_title, find_root_component, analyze_blueprint_content, get_echarts_tree_data

render_global_sidebar()

st.title("📝 App 說明文件產生器")
st.markdown("根據 Blueprint 自動產出 App 說明文件 (Markdown)，可作為 Chatbot 知識庫使用。")
st.divider()

# --- 使用者輸入區 ---
st.subheader("📋 填寫 App 基本資訊")

col1, col2 = st.columns(2)
with col1:
    app_name = st.text_input("App 名稱", placeholder="e.g. CMoney 股市")
    ios_link = st.text_input("iOS App Store 連結", placeholder="https://apps.apple.com/...")
with col2:
    app_desc = st.text_input("App 一句話簡介", placeholder="e.g. 提供即時股市資訊與投資工具的財經 App")
    android_link = st.text_input("Google Play Store 連結", placeholder="https://play.google.com/...")

st.divider()

# --- BP 上傳區 ---
st.subheader("📂 上傳 Blueprint")
st.markdown("可同時上傳免費版與付費版 BP，系統會自動比對兩者的架構與 lock 差異。")

col_free, col_paid = st.columns(2)
with col_free:
    free_file = st.file_uploader("免費版 Blueprint (JSON/ZIP)", type=["json", "zip"], key="free_bp")
with col_paid:
    paid_file = st.file_uploader("付費版 Blueprint (JSON/ZIP)", type=["json", "zip"], key="paid_bp")

use_sidebar_bp = st.checkbox("或使用左側已上傳的 Blueprint（單一版本）", value=False)

st.divider()


# --- 檔案解析 ---
def _parse_uploaded_bp(uploaded_file):
    """解析上傳的 BP 檔案（JSON 或 ZIP）"""
    if not uploaded_file:
        return None
    try:
        if uploaded_file.name.endswith(".zip"):
            with zipfile.ZipFile(uploaded_file) as z:
                for f in z.namelist():
                    if os.path.basename(f).lower() == "blueprint.json":
                        with z.open(f) as bf:
                            return json.load(bf)
            st.error(f"❌ ZIP 檔 `{uploaded_file.name}` 中未找到 blueprint.json")
        elif uploaded_file.name.endswith(".json"):
            uploaded_file.seek(0)
            return json.load(uploaded_file)
    except Exception as e:
        st.error(f"讀取失敗: {e}")
    return None


# --- 產生邏輯 ---

# 容器類型名稱清單，這些節點在文件中應被穿透（只顯示其有 title 的子節點）
_LAYOUT_NAMES = {"靜態容器", "垂直捲動容器", "水平捲動容器", "底部分頁容器", "分頁容器", "頁籤分頁容器", "頁面流程"}


def _build_doc_tree(node, depth=0, max_depth=6):
    """
    從原始 blueprint node 建立乾淨的文件樹。
    規則：只顯示有 title 的節點，容器類型一律穿透（不增加深度）。
    回傳: list of {"title": str, "depth": int, "children_titles": [str]}
    """
    if depth > max_depth or not isinstance(node, dict):
        return []

    name = node.get("name", "")
    raw_title = (node.get("parameters") or {}).get("title") or node.get("title", "")
    title = clean_title(raw_title)
    is_layout = name in _LAYOUT_NAMES

    lines = []
    children = (node.get("subComponents") or []) + (node.get("pages") or [])

    if title and not is_layout:
        # 有 title 且不是容器 → 顯示
        lines.append("  " * depth + f"- {title}")
        for child in children:
            lines.extend(_build_doc_tree(child, depth + 1, max_depth))
    elif title and is_layout:
        # 是容器但有 title（如 Tab 頁面 "宏觀"）→ 顯示 title，但標記為容器
        lines.append("  " * depth + f"- {title}")
        for child in children:
            lines.extend(_build_doc_tree(child, depth + 1, max_depth))
    else:
        # 沒 title 或是純容器 → 穿透，不增加深度
        for child in children:
            lines.extend(_build_doc_tree(child, depth, max_depth))

    return lines


def _get_tabs_from_bp(data):
    """從 blueprint 取得主要 Tab 與其子功能"""
    root = find_root_component(data.get("pages", []), "20000001")
    if not root:
        if data.get("uuid") == "20000001":
            root = data
        else:
            return []

    tabs = []
    tab_idx = 0
    for comp in root.get("subComponents", []):
        raw_title = (comp.get("parameters") or {}).get("title") or comp.get("title", "")
        title = clean_title(raw_title)
        if not title:
            continue

        # 收集子功能（只取有 title 的，穿透容器）
        features = []
        _collect_titled_children(comp, features, max_depth=3)
        tabs.append({"index": tab_idx, "title": title, "features": features})
        tab_idx += 1

    return tabs


def _collect_titled_children(node, features, depth=0, max_depth=3):
    """遞迴收集有 title 的子節點名稱，穿透容器"""
    if depth > max_depth:
        return
    children = (node.get("subComponents") or []) + (node.get("pages") or [])
    for child in children:
        if not isinstance(child, dict):
            continue
        name = child.get("name", "")
        raw_title = (child.get("parameters") or {}).get("title") or child.get("title", "")
        title = clean_title(raw_title)
        is_layout = name in _LAYOUT_NAMES

        if title:
            features.append(title)

        # 不管是否為容器，都繼續往下找（容器不佔深度）
        next_depth = depth if is_layout else depth + 1
        _collect_titled_children(child, features, next_depth, max_depth)


def _extract_lock_info(node, breadcrumbs=None, locks=None):
    """
    遞迴遍歷 blueprint，提取每個有 lock 的區塊資訊。
    locks: dict, key=breadcrumb_path -> lock condition string
    """
    if locks is None:
        locks = {}
    if breadcrumbs is None:
        breadcrumbs = []
    if not isinstance(node, dict):
        return locks

    # 更新麵包屑
    current_crumbs = list(breadcrumbs)
    raw_t = node.get('title') or (node.get('parameters') or {}).get('title')
    if raw_t:
        clean = re.sub(r'{{|}}', '', raw_t).strip()
        if clean:
            current_crumbs.append(clean)

    params = node.get('parameters', {})

    # lock 可能出現在多個位置，逐一檢查
    columns_to_check = []

    # 1. parameters.tableSetting.columns (最常見)
    table_setting = params.get('tableSetting', {})
    if isinstance(table_setting, dict) and 'columns' in table_setting:
        columns_to_check.extend(table_setting['columns'])

    # 2. parameters.columns (備用)
    if 'columns' in params and isinstance(params['columns'], list):
        columns_to_check.extend(params['columns'])

    # 3. 直接在 node 上的 tableSetting
    if 'tableSetting' in node and isinstance(node['tableSetting'], dict):
        ts_cols = node['tableSetting'].get('columns', [])
        if isinstance(ts_cols, list):
            columns_to_check.extend(ts_cols)

    for col in columns_to_check:
        if isinstance(col, dict) and 'lock' in col:
            lock_info = col['lock']
            condition = lock_info.get('condition', '')
            if condition:
                context_key = " > ".join(current_crumbs) if current_crumbs else "Unknown"
                locks[context_key] = condition
                break  # 同一個元件只需記錄一次

    # 遞迴子節點
    children = (node.get('subComponents') or []) + (node.get('pages') or [])
    for child in children:
        _extract_lock_info(child, current_crumbs, locks)

    return locks


def _parse_lock_condition(condition):
    """
    解析 lock condition，回傳人類可讀的描述。
    例如 "資料索引位置>=3" -> "免費用戶可查看前 3 筆資料"
    例如 "資料索引位置>2" -> "免費用戶可查看前 3 筆資料"
    例如 "資料索引位置>=0" -> "此區塊為付費限定"
    """
    match = re.match(r'資料索引位置\s*(>=|>)\s*(\d+)', condition)
    if not match:
        return f"付費限制：{condition}"

    op = match.group(1)
    num = int(match.group(2))

    if op == ">=":
        free_count = num
    else:  # ">"
        free_count = num + 1

    if free_count == 0:
        return "此區塊為付費限定內容"
    else:
        return f"免費用戶可查看前 {free_count} 筆，更多內容需付費解鎖"


def _get_data_index_with_lock(data):
    """
    取得數據指標索引（按區塊分組），同時偵測 lock 條件。
    回傳: OrderedDict, key=(所在頁面, 所在區塊) -> {"fields": [...], "lock": str|None}
    """
    results, _ = analyze_blueprint_content(data)

    # 同時提取 lock 資訊
    lock_map = _extract_lock_info(data)

    grouped = OrderedDict()
    for r in results:
        fields = r.get("fields_info", [])
        field_names = [f for f in fields if isinstance(f, str)]
        cleaned_fields = []
        for f in field_names:
            if " (" in f and f.endswith(")"):
                cleaned_fields.append(f.rsplit(" (", 1)[0])
            else:
                cleaned_fields.append(f)

        if not cleaned_fields:
            continue

        key = (r["group"], r["display_name"])
        if key not in grouped:
            grouped[key] = {"fields": [], "lock": None}
        for field in cleaned_fields:
            if field not in grouped[key]["fields"]:
                grouped[key]["fields"].append(field)

    # 匹配 lock 條件到各區塊
    for (page, block), info in grouped.items():
        for lock_context, condition in lock_map.items():
            # lock_context 是麵包屑路徑，嘗試匹配到所在區塊
            if block in lock_context or page in lock_context:
                info["lock"] = _parse_lock_condition(condition)
                break

    return grouped


def generate_markdown(app_name, app_desc, ios_link, android_link, data):
    """產生完整的 Markdown 說明文件"""
    bp_version = data.get("version", "Unknown")
    tabs = _get_tabs_from_bp(data)

    md = []

    # 一、App 總覽
    md.append(f"# {app_name} App 說明文件")
    md.append("")
    md.append("## 一、App 總覽")
    md.append("")
    if app_desc:
        md.append(f"**簡介：** {app_desc}")
        md.append("")
    md.append(f"**Blueprint 版本：** {bp_version}")
    md.append("")

    if ios_link or android_link:
        md.append("### 下載連結")
        md.append("")
        if ios_link:
            md.append(f"- iOS App Store: {ios_link}")
        if android_link:
            md.append(f"- Google Play Store: {android_link}")
        md.append("")

    # 二、App 架構與頁面導覽
    md.append("## 二、App 架構與頁面導覽")
    md.append("")
    if tabs:
        md.append("### 主要分頁 (Bottom Tab)")
        md.append("")
        for tab in tabs:
            md.append(f"#### {tab['index'] + 1}. {tab['title']}")
            md.append("")
            if tab["features"]:
                seen = set()
                for feat in tab["features"]:
                    if feat and feat not in seen:
                        md.append(f"- {feat}")
                        seen.add(feat)
                md.append("")

    # 完整架構樹
    root = find_root_component(data.get("pages", []), "20000001")
    if not root and data.get("uuid") == "20000001":
        root = data
    if root:
        tree_lines = _build_doc_tree(root, depth=0, max_depth=5)
        if tree_lines:
            md.append("### 完整架構樹")
            md.append("")
            md.append("```")
            for line in tree_lines:
                md.append(line)
            md.append("```")
            md.append("")

    # 三、數據指標索引
    md.append("## 三、數據指標索引")
    md.append("")
    data_grouped = _get_data_index_with_lock(data)
    if data_grouped:
        page_groups = OrderedDict()
        for (page, block), info in data_grouped.items():
            if page not in page_groups:
                page_groups[page] = []
            page_groups[page].append((block, info))

        for page, blocks in page_groups.items():
            md.append(f"### {page}")
            md.append("")
            for block, info in blocks:
                md.append(f"**{block}**")
                if info["lock"]:
                    md.append(f"")
                    md.append(f"> {info['lock']}")
                md.append("")
                for field in info["fields"]:
                    md.append(f"- {field}")
                md.append("")
    else:
        md.append("（此 Blueprint 中未偵測到數據指標）")
        md.append("")

    # 四、功能說明
    md.append("## 四、功能說明")
    md.append("")
    if tabs:
        for tab in tabs:
            md.append(f"### {tab['title']}")
            md.append("")
            md.append(f"- **位置：** App 底部第 {tab['index'] + 1} 個分頁")
            if tab["features"]:
                md.append(f"- **包含功能：**")
                seen = set()
                for feat in tab["features"]:
                    if feat and feat not in seen:
                        md.append(f"  - {feat}")
                        seen.add(feat)
            md.append("")

    # 五、免費 vs 付費內容
    locked_blocks = [(page, block, info) for (page, block), info in data_grouped.items() if info["lock"]]
    if locked_blocks:
        md.append("## 五、免費 vs 付費內容")
        md.append("")
        md.append("以下區塊包含付費限制：")
        md.append("")
        md.append("| 所在頁面 | 區塊 | 付費限制 |")
        md.append("|---------|------|---------|")
        for page, block, info in locked_blocks:
            md.append(f"| {page} | {block} | {info['lock']} |")
        md.append("")

    md.append("---")
    md.append("*此文件由 Blueprint 萬能工具箱自動產生*")
    return "\n".join(md)


def _collect_all_titled_names(node):
    """遞迴收集所有有 title 的節點名稱（用於比對）"""
    names = set()
    if not isinstance(node, dict):
        return names
    raw_title = (node.get("parameters") or {}).get("title") or node.get("title", "")
    title = clean_title(raw_title)
    if title:
        names.add(title)
    for child in (node.get("subComponents") or []) + (node.get("pages") or []):
        names.update(_collect_all_titled_names(child))
    return names


def generate_markdown_compare(app_name, app_desc, ios_link, android_link, free_data, paid_data):
    """免費版 vs 付費版對比的 Markdown 產生"""
    free_version = free_data.get("version", "Unknown")
    paid_version = paid_data.get("version", "Unknown")

    paid_tabs = _get_tabs_from_bp(paid_data)

    free_features = _collect_all_titled_names(free_data)
    paid_features = _collect_all_titled_names(paid_data)
    paid_only = paid_features - free_features
    free_only = free_features - paid_features

    free_data_grouped = _get_data_index_with_lock(free_data)
    paid_data_grouped = _get_data_index_with_lock(paid_data)

    md = []

    # 一、App 總覽
    md.append(f"# {app_name} App 說明文件")
    md.append("")
    md.append("## 一、App 總覽")
    md.append("")
    if app_desc:
        md.append(f"**簡介：** {app_desc}")
        md.append("")
    md.append(f"**Blueprint 版本：** 免費版 {free_version} / 付費版 {paid_version}")
    md.append("")

    if ios_link or android_link:
        md.append("### 下載連結")
        md.append("")
        if ios_link:
            md.append(f"- iOS App Store: {ios_link}")
        if android_link:
            md.append(f"- Google Play Store: {android_link}")
        md.append("")

    # 二、App 架構與頁面導覽
    md.append("## 二、App 架構與頁面導覽")
    md.append("")
    md.append("> 以付費版架構為主，標示免費版差異。")
    md.append("")

    if paid_tabs:
        md.append("### 主要分頁 (Bottom Tab)")
        md.append("")
        for tab in paid_tabs:
            md.append(f"#### {tab['index'] + 1}. {tab['title']}")
            md.append("")
            if tab["features"]:
                seen = set()
                for feat in tab["features"]:
                    if feat and feat not in seen:
                        suffix = " `[付費限定]`" if feat in paid_only else ""
                        md.append(f"- {feat}{suffix}")
                        seen.add(feat)
                md.append("")

    # 完整架構樹（付費版）
    paid_root = find_root_component(paid_data.get("pages", []), "20000001")
    if not paid_root and paid_data.get("uuid") == "20000001":
        paid_root = paid_data
    if paid_root:
        tree_lines = _build_doc_tree(paid_root, depth=0, max_depth=5)
        if tree_lines:
            md.append("### 完整架構樹（付費版）")
            md.append("")
            md.append("```")
            for line in tree_lines:
                md.append(line)
            md.append("```")
            md.append("")

    # 三、數據指標索引（合併兩版）
    md.append("## 三、數據指標索引")
    md.append("")

    # 合併兩版，按區塊分組，比對欄位差異
    all_blocks = OrderedDict()

    for (page, block), info in free_data_grouped.items():
        if (page, block) not in all_blocks:
            all_blocks[(page, block)] = {"fields": OrderedDict(), "lock": info["lock"]}
        for field in info["fields"]:
            all_blocks[(page, block)]["fields"][field] = "免費"

    for (page, block), info in paid_data_grouped.items():
        if (page, block) not in all_blocks:
            all_blocks[(page, block)] = {"fields": OrderedDict(), "lock": info["lock"]}
        else:
            # 付費版的 lock 通常更寬鬆或沒有
            if not info["lock"]:
                all_blocks[(page, block)]["lock"] = None
        for field in info["fields"]:
            if field in all_blocks[(page, block)]["fields"]:
                all_blocks[(page, block)]["fields"][field] = "免費 + 付費"
            else:
                all_blocks[(page, block)]["fields"][field] = "付費限定"

    if all_blocks:
        page_groups = OrderedDict()
        for (page, block), info in all_blocks.items():
            if page not in page_groups:
                page_groups[page] = []
            page_groups[page].append((block, info))

        for page, blocks in page_groups.items():
            md.append(f"### {page}")
            md.append("")
            for block, info in blocks:
                md.append(f"**{block}**")
                if info["lock"]:
                    md.append("")
                    md.append(f"> {info['lock']}")
                md.append("")
                for field, perm in info["fields"].items():
                    suffix = f" `[{perm}]`" if perm != "免費 + 付費" else ""
                    md.append(f"- {field}{suffix}")
                md.append("")
    else:
        md.append("（未偵測到數據指標）")
        md.append("")

    # 四、功能說明
    md.append("## 四、功能說明")
    md.append("")
    if paid_tabs:
        for tab in paid_tabs:
            md.append(f"### {tab['title']}")
            md.append("")
            md.append(f"- **位置：** App 底部第 {tab['index'] + 1} 個分頁")
            if tab["features"]:
                md.append(f"- **包含功能：**")
                seen = set()
                for feat in tab["features"]:
                    if feat and feat not in seen:
                        suffix = " `[付費限定]`" if feat in paid_only else ""
                        md.append(f"  - {feat}{suffix}")
                        seen.add(feat)
            md.append("")

    # 五、免費 vs 付費內容
    md.append("## 五、免費 vs 付費內容")
    md.append("")

    if paid_only:
        md.append("### 付費版限定功能")
        md.append("")
        for feat in sorted(paid_only):
            md.append(f"- {feat}")
        md.append("")

    if free_only:
        md.append("### 免費版獨有（付費版移除）")
        md.append("")
        for feat in sorted(free_only):
            md.append(f"- {feat}")
        md.append("")

    # lock 限制彙整
    locked_blocks = [(page, block, info) for (page, block), info in all_blocks.items() if info["lock"]]
    if locked_blocks:
        md.append("### 付費限制區塊")
        md.append("")
        md.append("| 所在頁面 | 區塊 | 付費限制 |")
        md.append("|---------|------|---------|")
        for page, block, info in locked_blocks:
            md.append(f"| {page} | {block} | {info['lock']} |")
        md.append("")

    # 付費限定欄位
    paid_only_fields = []
    for (page, block), info in all_blocks.items():
        for field, perm in info["fields"].items():
            if perm == "付費限定":
                paid_only_fields.append((field, page, block))
    if paid_only_fields:
        md.append("### 付費版限定數據指標")
        md.append("")
        for field, page, block in paid_only_fields:
            md.append(f"- {field}（{page} > {block}）")
        md.append("")

    md.append("---")
    md.append("*此文件由 Blueprint 萬能工具箱自動產生*")
    return "\n".join(md)


# --- 判斷模式與生成 ---
free_data = _parse_uploaded_bp(free_file)
paid_data = _parse_uploaded_bp(paid_file)
sidebar_data = get_blueprint_data() if use_sidebar_bp else None

has_both = free_data is not None and paid_data is not None
has_single = sidebar_data is not None or free_data is not None or paid_data is not None

if has_both:
    st.success("✅ 已載入免費版與付費版 BP，將產生對比文件。")
elif sidebar_data:
    st.info("ℹ️ 使用側欄 BP（含 lock 偵測）。")
elif free_data:
    st.info("ℹ️ 僅載入免費版 BP。")
elif paid_data:
    st.info("ℹ️ 僅載入付費版 BP。")
else:
    st.warning("⚠️ 請上傳至少一份 Blueprint 檔案，或勾選使用側欄已上傳的 BP。")

# --- 生成按鈕 ---
if st.button("🚀 生成說明文件", type="primary", use_container_width=True):
    if not app_name:
        st.error("請填寫 App 名稱")
        st.stop()

    if not has_both and not has_single:
        st.error("請上傳至少一份 Blueprint")
        st.stop()

    with st.spinner("正在分析 Blueprint 並產生文件..."):
        if has_both:
            md_content = generate_markdown_compare(app_name, app_desc, ios_link, android_link, free_data, paid_data)
        else:
            single_data = sidebar_data or free_data or paid_data
            md_content = generate_markdown(app_name, app_desc, ios_link, android_link, single_data)

        st.session_state["generated_md"] = md_content
        st.session_state["generated_app_name"] = app_name

# --- 顯示結果與下載 ---
if "generated_md" in st.session_state:
    st.divider()
    st.subheader("📄 產生結果")

    generated_app_name = st.session_state.get("generated_app_name", "app")
    file_name = f"{generated_app_name}_說明文件.md"

    st.download_button(
        label="⬇️ 下載 Markdown 檔案",
        data=st.session_state["generated_md"],
        file_name=file_name,
        mime="text/markdown",
        use_container_width=True,
        type="primary"
    )

    with st.expander("預覽內容", expanded=True):
        st.markdown(st.session_state["generated_md"])

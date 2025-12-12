import json
from collections import defaultdict
import re

def extract_data_sources(component, component_path, results):
    """遞迴遍歷組件，提取資料來源、ID 和使用的欄位。"""
    
    # 嘗試從 component 或 parameters 中獲取更友善的名稱作為路徑
    component_name = component.get("name", "Unknown Component")
    param_title = component.get("parameters", {}).get("title")
    # 將 {{...}} 變數名稱移除，保留中文名稱
    title_clean = param_title.replace('{', '').replace('}', '') if param_title else None
    path_name = f"{component_name} ({title_clean})" if title_clean else component_name
    current_path = f"{component_path} > {path_name}"

    # 定義要檢查的資料源列表 (source 和 readSources)
    sources_lists = [
        ("source", component.get("source", [])),
        ("readSources", component.get("readSources", []))
    ]

    component_fields = set()

    # 1. 從組件的顯示設定中提取欄位 (優先從這裡獲取，因為這是組件實際使用的欄位)
    
    # 處理「資訊展示板」
    if component_name == "資訊展示板" and "contentSetting" in component.get("parameters", {}):
        for content in component["parameters"]["contentSetting"].get("contents", []):
            if "numberLineNumberParams" in content:
                key = content["numberLineNumberParams"].get("columnKey")
                if key: component_fields.add(key)
            if "numberLineImageParams" in content:
                key = content["numberLineImageParams"].get("columnKey")
                if key: component_fields.add(key)
    
    # 處理「合併表格」
    elif component_name == "合併表格" and "tableSetting" in component.get("parameters", {}):
        for col_setting in component["parameters"]["tableSetting"].get("columns", []):
            # 從欄位標題的排序設定中提取 key
            sort_key = col_setting.get("title", {}).get("parameters", {}).get("sortSetting", {}).get("key")
            if sort_key: component_fields.add(sort_key)
            
            # 從內容設定中提取欄位名稱
            content_text = col_setting.get("content", {}).get("parameters", {}).get("text")
            if content_text and content_text not in ["名稱", "PureText", "ConditionalText"]:
                component_fields.add(content_text)
                
            # 從數值欄位組件中提取 columnKey
            if col_setting.get("content", {}).get("name") in ["數線型數值欄位", "ConditionFromBase"]:
                key = col_setting["content"]["parameters"].get("columnKey") or col_setting["content"]["parameters"].get("showingNumber")
                if key: component_fields.add(key)

    # 2. 遍歷所有的資料來源
    for source_list_name, sources in sources_lists:
        for source in sources:
            source_name = source.get("name")
            params = source.get("sourceParameters", {})
            source_id = None
            source_fields_set = component_fields.copy() 

            # 確定資料 ID
            if source_name in ["dtno", "AddInfoDtno"]:
                source_id = params.get("dtnoNum")
            elif source_name == "GoogleSheet":
                sheet_id = params.get('sheetId', 'N/A')
                sheet_name = params.get('sheetName', 'N/A')
                source_id = f"Sheet ID: {sheet_id}, Sheet Name: {sheet_name}"
            elif source_name in ["USCommodity", "USStockCalculation"] and not source_id:
                source_id = "N/A" # 沒有 dtno 編號的資料源給予 N/A

            # 提取來源中明確定義的欄位列表 (例如: GoogleSheet, AddInfoDtno 的 columns 陣列)
            columns_in_source = params.get("columns", [])
            if columns_in_source:
                source_fields_set.update(columns_in_source) 

            # 記錄結果 (只有當有有效的資料來源名稱和 ID 時才記錄)
            if source_name and source_id:
                results.append({
                    "清單/組件名稱": current_path,
                    "欄位": sorted(list(source_fields_set)), 
                    "資料來源類型": source_name,
                    "資料編號/ID": source_id
                })

    # 3. 遞迴進入子組件
    if "subComponents" in component:
        for sub_comp in component["subComponents"]:
            extract_data_sources(sub_comp, current_path, results)

def simplify_component_name(full_path):
    """簡化路徑名稱，只取最後一個組件名稱和相關的頁籤標題作為上下文。"""
    parts = full_path.split(" > ")
    
    main_component_name = parts[-1] if parts else "Unknown"
    context_name = ""
    
    # 從倒數第二個元素開始找上下文標題
    for part in reversed(parts[:-1]):
        match = re.search(r"\((.*?)\)", part)
        if match:
            # 排除純 ID 或通用屬性名稱
            context = match.group(1).replace("{", "").replace("}", "")
            if context and not re.match(r"^[0-9a-f-]+$", context) and context not in ["ratio", "height"]:
                context_name = context
                break

    # 特殊組件名稱處理
    if "資訊展示板" in main_component_name:
        return "資訊展示板 (市場指標)"
    elif "合併表格" in main_component_name:
        return f"合併表格 ({context_name})" if context_name else "合併表格 (未知)"
    
    return main_component_name.split(" ")[0]

def analyze_blueprint(json_content):
    """主分析函式，接收 JSON 內容並返回結構化的結果。"""
    try:
        data = json.loads(json_content)
    except json.JSONDecodeError:
        return {"error": "JSON 解碼錯誤，請檢查檔案格式。"}

    results = []
    for page in data.get("pages", []):
        extract_data_sources(page, "Pages", results)

    # 彙整結果，將相同組件的多個資料來源合併
    grouped_output = defaultdict(lambda: {"清單/組件名稱": "", "欄位": set(), "資料來源": set()})

    for item in results:
        comp_name = simplify_component_name(item["清單/組件名稱"])
        source_info = (item["資料來源類型"], item["資料編號/ID"])
        
        key = comp_name
        grouped_output[key]["清單/組件名稱"] = comp_name
        grouped_output[key]["欄位"].update(item["欄位"])
        grouped_output[key]["資料來源"].add(source_info)

    # 整理最終的表格資料
    final_table_data = []
    for name, data in grouped_output.items():
        source_list = []
        source_types = set()
        # 依據類型和 ID 排序
        for type_name, id_num in sorted(list(data["資料來源"])):
            source_list.append(f"{type_name} ({id_num})")
            source_types.add(type_name)

        final_table_data.append({
            "清單/組件名稱": name,
            "欄位": ", ".join(sorted(list(data["欄位"]))),
            "對應資料來源": ", ".join(sorted(list(source_types))),
            "資料來源對應資料編號": "\n".join(source_list)
        })
        
    return final_table_data

# 範例使用方式：
# with open('BLUEPRINT.JSON', 'r', encoding='utf-8') as f:
#     json_content = f.read()
# analysis_result = analyze_blueprint(json_content)
# for item in analysis_result:
#     print(f"清單/組件名稱: {item['清單/組件名稱']}")
#     print(f"欄位: {item['欄位']}")
#     print(f"對應資料來源: {item['對應資料來源']}")
#     print(f"資料來源對應資料編號:\n{item['資料來源對應資料編號']}\n{'-'*30}")
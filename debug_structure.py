import json
import re

def load_blueprint():
    with open('blueprint.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def clean_title(title):
    if not title: return ""
    return title.replace('{{', '').replace('}}', '')

def find_tab_index_by_name(blueprint_data, keyword_list, parent_uuid="20000001"):
    if not blueprint_data: return "0", None
    parent_node = None
    if blueprint_data.get('uuid') == parent_uuid: parent_node = blueprint_data
    else:
        def _find(node):
            if node.get('uuid') == parent_uuid: return node
            for child in node.get('subComponents', []) + node.get('pages', []):
                res = _find(child)
                if res: return res
            return None
        parent_node = _find(blueprint_data)
    
    if not parent_node or 'subComponents' not in parent_node: 
        print(f"Parent node {parent_uuid} not found or has no subComponents")
        return "0", None
        
    for idx, comp in enumerate(parent_node['subComponents']):
        name = comp.get('name', '')
        title = clean_title(comp.get('parameters', {}).get('title', ''))
        if not title: title = clean_title(comp.get('title', ''))
        
        print(f"Checking Index {idx}: Title='{title}', Name='{name}'")
        
        for kw in keyword_list:
            if kw in title or kw in name: 
                print(f"MATCH: '{kw}' in Title or Name")
                return str(idx), comp.get('uuid')
    return "0", None

def main():
    data = load_blueprint()
    print("Test 1: Club")
    idx, uuid = find_tab_index_by_name(data, ["社團", "Club"])
    print(f"Result: Index={idx}, UUID={uuid}")

    print("\nTest 2: Stock")
    idx, uuid = find_tab_index_by_name(data, ["選股", "行情", "Stock", "Quote"])
    print(f"Result: Index={idx}, UUID={uuid}")

if __name__ == "__main__":
    main()

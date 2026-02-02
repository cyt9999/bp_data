import json

def load_blueprint():
    with open('blueprint.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def clean_title(title):
    if not title: return ""
    return title.replace('{{', '').replace('}}', '')

def main():
    data = load_blueprint()
    
    def find_node(node, uuid):
        if node.get('uuid') == uuid: return node
        children = (node.get('subComponents') or []) + (node.get('pages') or [])
        for child in children:
            if isinstance(child, dict):
                res = find_node(child, uuid)
                if res: return res
        return None

    # Found in previous step: [2] is Pager Container
    pager_uuid = "265589102"
    pager_node = find_node(data, pager_uuid)
    
    if not pager_node:
        print("Pager node not found")
        return

    print(f"Pager Node: {pager_node.get('name')}")
    if 'subComponents' in pager_node:
        for i, tab_container in enumerate(pager_node['subComponents']):
            name = tab_container.get('name')
            title = clean_title(tab_container.get('parameters', {}).get('title', ''))
            print(f"  Layer 2 - Index {i}: {title} ({name})")
            
            # Check Layer 3 (Free/VIP etc)
            if 'subComponents' in tab_container:
                for j, sub in enumerate(tab_container['subComponents']):
                    s_title = clean_title(sub.get('parameters', {}).get('title', ''))
                    print(f"      Layer 3 - Index {j}: {s_title} ({sub.get('name')})")

if __name__ == "__main__":
    main()

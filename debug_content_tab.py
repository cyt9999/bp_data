import json
import os

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

    # Content Tab UUID from previous debug
    content_uuid = "876543217775555555" 
    content_node = find_node(data, content_uuid)
    
    if not content_node:
        print(f"Content node {content_uuid} not found")
        return

    print(f"Content Node: {content_node.get('name')} ({content_node.get('uuid')})")
    
    # Check its subcomponents (Layer 1: Article / Video ?)
    if 'subComponents' in content_node:
        for i, comp in enumerate(content_node['subComponents']):
            name = comp.get('name')
            title = clean_title(comp.get('parameters', {}).get('title', ''))
            print(f"  [{i}] {title} ({name}) - {comp.get('uuid')}")
            
            # Check Layer 2
            if 'subComponents' in comp:
                for j, sub in enumerate(comp['subComponents']):
                    s_title = clean_title(sub.get('parameters', {}).get('title', ''))
                    print(f"      [{i}.{j}] {s_title} ({sub.get('name')})")

if __name__ == "__main__":
    main()

import json, csv, os, datetime, requests

class Exporter:
    def __init__(self, logger, export_dir='output/exports'):
        self.logger = logger; self.dir = export_dir
        os.makedirs(export_dir, exist_ok=True)

    def export(self, data, fmt='json'):
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        path = f"{self.dir}/export_{ts}.{fmt}"
        try:
            if fmt=='json': json.dump(data, open(path,'w',encoding='utf-8'), indent=2, ensure_ascii=False)
            elif fmt=='md':
                with open(path,'w',encoding='utf-8') as f:
                    for it in data: f.write(f"# {it.get('title','')}\n\n**Source:** {it.get('source','')}\n\n{it.get('summary','')}\n\n---\n\n")
            elif fmt=='txt':
                with open(path,'w',encoding='utf-8') as f:
                    for it in data: f.write(f"{it.get('title','')}\n{it.get('summary','')}\n\n")
            elif fmt=='csv':
                with open(path,'w',newline='',encoding='utf-8') as f:
                    w = csv.DictWriter(f, fieldnames=['title','source','summary','url'])
                    w.writeheader()
                    for it in data: w.writerow({k:it.get(k,'') for k in ['title','source','summary','url']})
            elif fmt=='obsidian':
                # Markdown with [[wiki-links]]
                with open(path.replace('.obsidian','.md'),'w',encoding='utf-8') as f:
                    for it in data:
                        tags = f"#{it.get('source','').replace('.','_')} #ai-generated"
                        f.write(f"# {it.get('title','')}\n{tags}\n\n{it.get('summary','')}\n\n[[source]]: {it.get('url','')}\n\n---\n\n")
                path = path.replace('.obsidian','.md')
            self.logger.log(f"Export: {path}","success")
            return path
        except Exception as e: self.logger.log(f"export: {e}","error"); return None

    def push_notion(self, data, notion_key, database_id):
        """#24 Notion publisher"""
        if not notion_key or not database_id: return None
        try:
            for it in data:
                requests.post("https://api.notion.com/v1/pages",
                    headers={"Authorization":f"Bearer {notion_key}","Notion-Version":"2022-06-28","Content-Type":"application/json"},
                    json={"parent":{"database_id":database_id},
                          "properties":{"Name":{"title":[{"text":{"content":it.get('title','')[:100]}}]}},
                          "children":[{"object":"block","type":"paragraph","paragraph":{"rich_text":[{"text":{"content":it.get('summary','')[:2000]}}]}}]})
            self.logger.log(f"Notion: {len(data)} pages pushed","success")
            return True
        except Exception as e: self.logger.log(f"notion: {e}","error"); return False
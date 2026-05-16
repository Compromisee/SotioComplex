import json, os

def load_json(path, default=None):
    if not os.path.exists(path): return default if default is not None else {}
    with open(path) as f: return json.load(f)

def save_json(path, data):
    with open(path,'w',encoding='utf-8') as f: json.dump(data, f, indent=2, ensure_ascii=False)

def load_config(): return load_json('config.json')
def load_presets(): return load_json('presets.json')
def load_themes(): return load_json('themes.json')
def load_pipeline_templates(): return load_json('pipeline_templates.json', {})

def ensure_dirs(cfg):
    for p in cfg['paths'].values(): os.makedirs(p, exist_ok=True)
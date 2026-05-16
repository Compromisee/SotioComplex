from .utils import load_json, save_json

class SourceHealth:
    def __init__(self, logger, path='output/source_health.json'):
        self.logger = logger; self.path = path
        self.data = load_json(path, {})

    def record(self, site, success):
        d = self.data.setdefault(site, {"success":0,"fail":0})
        if success: d['success'] += 1
        else: d['fail'] += 1
        save_json(self.path, self.data)

    def score(self, site):
        d = self.data.get(site, {"success":1,"fail":0})
        total = d['success']+d['fail']
        return int(d['success']/total*100) if total else 50

    def auto_disable(self, threshold=20):
        return [s for s,d in self.data.items() if self.score(s) < threshold]

    def report(self):
        return [{"site":s,"score":self.score(s),**d} for s,d in self.data.items()]
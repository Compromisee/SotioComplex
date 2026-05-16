import json, os, datetime, uuid

class HistoryManager:
    def __init__(self, logger, hist_dir='output/history'):
        self.logger = logger; self.dir = hist_dir
        os.makedirs(hist_dir, exist_ok=True)
        self.index = f"{hist_dir}/index.json"
        if not os.path.exists(self.index): json.dump([], open(self.index,'w'))

    def save_job(self, job_data):
        jid = uuid.uuid4().hex[:10]
        e = {"id":jid,"timestamp":datetime.datetime.now().isoformat(),"data":job_data}
        json.dump(e, open(f"{self.dir}/job_{jid}.json",'w',encoding='utf-8'), indent=2, ensure_ascii=False)
        idx = json.load(open(self.index))
        idx.append({"id":jid,"timestamp":e['timestamp'],"summary":job_data.get('title','Job')})
        json.dump(idx, open(self.index,'w'), indent=2)
        return jid

    def list_jobs(self): return json.load(open(self.index))
    def load_job(self, jid):
        p = f"{self.dir}/job_{jid}.json"
        return json.load(open(p)) if os.path.exists(p) else None
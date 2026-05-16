import datetime, os, json

class Logger:
    def __init__(self, socketio, log_dir='output/logs'):
        self.socketio = socketio; self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)
        self.file = f"{log_dir}/{datetime.date.today()}.log"
        self.history = []
        self.notifications = []

    def log(self, msg, level="info"):
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        entry = {"time": ts, "level": level, "msg": msg}
        self.history.append(entry)
        print(f"[{ts}][{level.upper()}] {msg}")
        with open(self.file,'a',encoding='utf-8') as f: f.write(f"[{ts}][{level.upper()}] {msg}\n")
        self.socketio.emit('log', entry)

    def progress(self, step, percent, label=""):
        self.socketio.emit('progress', {"step":step,"percent":percent,"label":label})

    def status(self, status, level="info"):
        self.socketio.emit('status', {"status":status,"level":level})

    def notify(self, title, body="", level="info"):
        n = {"title":title,"body":body,"level":level,"time":datetime.datetime.now().isoformat()}
        self.notifications.append(n)
        self.socketio.emit('notification', n)

    def preview(self, kind, path):
        """Live preview emit (#2)"""
        self.socketio.emit('preview', {"kind":kind,"path":path,"ts":datetime.datetime.now().isoformat()})

    def get_history(self, q=""):
        return [h for h in self.history if q.lower() in h['msg'].lower()] if q else self.history
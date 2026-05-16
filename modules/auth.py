import bcrypt, json, os, secrets

class AuthManager:
    def __init__(self, logger, path='users.json'):
        self.logger = logger; self.path = path
        if not os.path.exists(path):
            json.dump({}, open(path,'w'))
        self.sessions = {}

    def _load(self): return json.load(open(self.path))
    def _save(self, d): json.dump(d, open(self.path,'w'), indent=2)

    def register(self, user, password, role='user'):
        users = self._load()
        if user in users: return False
        users[user] = {"password_hash":bcrypt.hashpw(password.encode(),bcrypt.gensalt()).decode(),"role":role}
        self._save(users); return True

    def login(self, user, password):
        users = self._load()
        u = users.get(user)
        if u and bcrypt.checkpw(password.encode(), u['password_hash'].encode()):
            token = secrets.token_hex(16)
            self.sessions[token] = user
            return token
        return None

    def verify(self, token): return self.sessions.get(token)
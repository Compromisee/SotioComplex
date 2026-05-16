import diskcache, hashlib, time

class SmartCache:
    def __init__(self, logger, cache_dir='output/cache', ttl_hours=24):
        self.logger = logger
        self.cache = diskcache.Cache(cache_dir)
        self.ttl = ttl_hours * 3600

    def _k(self, *parts): return hashlib.md5("|".join(map(str,parts)).encode()).hexdigest()

    def get(self, *parts):
        k = self._k(*parts)
        v = self.cache.get(k)
        if v: self.logger.log(f"Cache HIT: {parts[0][:30]}", "info")
        return v

    def set(self, value, *parts):
        self.cache.set(self._k(*parts), value, expire=self.ttl)

    def clear(self):
        self.cache.clear()
        self.logger.log("Cache cleared","success")

    def stats(self):
        return {"size": self.cache.volume(), "count": len(self.cache)}
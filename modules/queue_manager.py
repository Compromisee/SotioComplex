from concurrent.futures import ThreadPoolExecutor, as_completed

class QueueManager:
    def __init__(self, logger, max_workers=3):
        self.logger = logger
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.pending = []
        self.done = []

    def submit(self, fn, *args, **kwargs):
        f = self.executor.submit(fn, *args, **kwargs)
        self.pending.append(f)
        return f

    def wait_all(self):
        results = []
        for f in as_completed(self.pending):
            try: results.append(f.result())
            except Exception as e: self.logger.log(f"Queue err: {e}","error")
        self.pending.clear()
        return results

    def status(self):
        return {"pending": sum(1 for f in self.pending if not f.done()), "done": sum(1 for f in self.pending if f.done())}
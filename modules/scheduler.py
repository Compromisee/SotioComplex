from apscheduler.schedulers.background import BackgroundScheduler

class JobScheduler:
    def __init__(self, logger):
        self.logger = logger
        self.sched = BackgroundScheduler(); self.sched.start()
        self.jobs = {}

    def schedule(self, func, interval_minutes, job_id, **kwargs):
        j = self.sched.add_job(func,'interval', minutes=interval_minutes, id=job_id, kwargs=kwargs, replace_existing=True)
        self.jobs[job_id] = j
        return job_id

    def schedule_cron(self, func, hour, minute, job_id, **kwargs):
        j = self.sched.add_job(func,'cron', hour=hour, minute=minute, id=job_id, kwargs=kwargs, replace_existing=True)
        self.jobs[job_id] = j
        return job_id

    def cancel(self, job_id):
        if job_id in self.jobs:
            self.sched.remove_job(job_id); del self.jobs[job_id]

    def list_jobs(self):
        return [{"id":j.id,"next":str(j.next_run_time)} for j in self.sched.get_jobs()]
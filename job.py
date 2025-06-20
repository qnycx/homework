class Job:
    def __init__(self, job_id, size, arrival_time, run_time):
        self.job_id = job_id
        self.size = size
        self.arrival_time = arrival_time
        self.run_time = run_time
        self.remaining_time = run_time
        self.status = 'waiting'  # 'waiting', 'running', 'finished'
        self.finish_time = None
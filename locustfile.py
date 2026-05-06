from locust import HttpUser, task, between
import random


class TimelineUser(HttpUser):
    wait_time = between(1, 2)

    @task
    def get_timeline(self):
        random_user = f"user{random.randint(1, 1000)}"
        self.client.get(f"/api/timeline?user={random_user}&limit=20",
                        name="/api/timeline")

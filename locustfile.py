import os
import random
from locust import HttpUser, task, between

NUM_USERS = int(os.environ.get("NUM_USERS", "1000"))
USER_PREFIX = os.environ.get("USER_PREFIX", "user")


class TimelineUser(HttpUser):
    # Temps d'attente aléatoire entre les requêtes (simule un vrai utilisateur)
    wait_time = between(0.1, 0.5)

    @task
    def get_timeline(self):
        """Requête GET sur /api/timeline avec un utilisateur aléatoire."""
        user_id = random.randint(1, NUM_USERS)
        username = f"{USER_PREFIX}{user_id}"
        with self.client.get(
            f"/api/timeline?user={username}&limit=20",
            name="/api/timeline",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"HTTP {response.status_code}: {response.text[:100]}")

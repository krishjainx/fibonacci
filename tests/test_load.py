from locust import HttpUser, task, between

class FibonacciLoadTest(HttpUser):
    wait_time = between(1, 2)

    @task
    def test_fibonacci(self):
        self.client.get("/fibonacci?n=10")

    @task
    def test_health(self):
        self.client.get("/health") 
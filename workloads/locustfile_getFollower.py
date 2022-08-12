from locust import LoadTestShape, HttpUser, constant_throughput, task
import resource
resource.setrlimit(resource.RLIMIT_NOFILE, (250000, 250000))


class MyCustomShape(LoadTestShape):
    time_limit = 600

    def tick(self):
        run_time = self.get_run_time()
        if run_time < self.time_limit:
            return 100, 100
        return None


class SocialNetworkUser(HttpUser):
    wait_time = constant_throughput(1)

    @task
    def login(self):
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        user_id = 1
        data = {'username': 'username_%d' % user_id,
                'password': 'password_%d' % user_id}

        self.client.post("/wrk2-api/user/login", data=data, headers=headers)

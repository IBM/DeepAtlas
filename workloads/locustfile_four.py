from locust import LoadTestShape, HttpUser, constant_throughput, task
import resource
import random
resource.setrlimit(resource.RLIMIT_NOFILE, (250000, 250000))


class MyCustomShape(LoadTestShape):
    time_limit = 300

    def tick(self):
        run_time = self.get_run_time()
        if run_time < self.time_limit:
            return 100, 100
        return None


class SocialNetworkUser(HttpUser):
    wait_time = constant_throughput(1)

    @task(25)
    def login(self):
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        user_id = 1
        data = {'username': 'username_%d' % user_id,
                'password': 'password_%d' % user_id}

        self.client.post("/wrk2-api/user/login", data=data, headers=headers)

    @task(25)
    def register(self):
        user = random.randint(1000, 1000000)
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        data = {'first_name': 'first_name_%d' % user,
                'last_name': 'last_name_%d' % user,
                'username': 'username_%d' % user,
                'password': 'password_%d' % user,
                'user_id': user}

        self.client.post("/wrk2-api/user/register", data=data, headers=headers)

    @task(25)
    def follow(self):
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        user1, user2 = random.randint(1, 800), random.randint(1, 800)
        self.client.post("/wrk2-api/user/follow", data={'user_id': user1, 'followee_id': user2}, headers=headers)

    @task(25)
    def unfollow(self):
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        user1, user2 = random.randint(1, 800), random.randint(1, 800)
        self.client.post("/wrk2-api/user/unfollow", data={'user_id': user1, 'followee_id': user2}, headers=headers)

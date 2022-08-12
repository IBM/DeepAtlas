from locust import LoadTestShape, HttpUser, task, between, events
import numpy as np
import resource
import pickle
import random
import math
import os
resource.setrlimit(resource.RLIMIT_NOFILE, (250000, 250000))


########################################################################################################################
# Simulation Configuration
########################################################################################################################
GLOBAL_NGINX_FRONTEND_URL  = 'http://c4130-110233.wisc.cloudlab.us:31364/frontend'
GLOBAL_MEDIA_FRONTEND_URL  = 'http://c4130-110233.wisc.cloudlab.us:31364/media'

########################################################################################################################
texts = [text.replace('@', '') for text in list(open('datasets/fb-posts/news.txt'))]
media = [os.path.join('datasets/inria-person', fname) for fname in os.listdir('datasets/inria-person')]
users = list(range(1, 963))
users_dummy_free = list(range(1000, 100000))
users_dummy_used = []
friendship = set()

active_users, inactive_users = [], list(range(1, 963))
with open('datasets/social-graph/socfb-Reed98.mtx', 'r') as f:
    friends = {}
    for edge in f.readlines():
        edge = list(map(int, edge.strip().split()))
        if len(edge) == 0:
            continue
        if edge[0] not in friends:
            friends[edge[0]] = set()
        if edge[1] not in friends:
            friends[edge[1]] = set()
        friends[edge[0]].add(edge[1])
        friends[edge[1]].add(edge[0])
    friends = {user: list(l) for user, l in friends.items()}


class LoadShape(LoadTestShape):
    def tick(self):
        if round(self.get_run_time()) > 10 * 60:
            return None
        return round(100), round(100)


class SocialNetworkUser(HttpUser):
    wait_time = between(1, 3)
    host = GLOBAL_NGINX_FRONTEND_URL

    @task(5)
    def login(self):
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        user_id = random.choice(users)
        data = {'username': 'username_%d' % user_id,
                'password': 'password_%d' % user_id}

        self.client.post("/wrk2-api/user/login", data=data, headers=headers)

    @task(5)
    def register(self):
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        user = users_dummy_free.pop(0)
        users_dummy_used.append(user)
        data = {'first_name': 'first_name_%d' % user,
                'last_name': 'last_name_%d' % user,
                'username': 'username_%d' % user,
                'password': 'password_%d' % user,
                'user_id': user}

        self.client.post("/wrk2-api/user/register", data=data, headers=headers)

    @task(5)
    def follow(self):
        if len(users_dummy_used) < 10:
            return
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        link = tuple(random.sample(users_dummy_used, 2))
        while link in friendship:
            link = tuple(random.sample(users_dummy_used, 2))
        friendship.add(link)
        user1, user2 = link
        self.client.post("/wrk2-api/user/follow", data={'user_id': user1, 'followee_id': user2}, headers=headers)

    @task(2)
    def unfollow(self):
        if len(friendship) < 2:
            return
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        link = random.choice(tuple(friendship))
        friendship.remove(link)
        user1, user2 = link
        self.client.post("/wrk2-api/user/unfollow", data={'user_id': user1, 'followee_id': user2}, headers=headers)

    @task(5)
    def readHomeTimeline(self):
        start = random.randint(0, 100)
        stop = start + 10

        response = self.client.get(
            "/wrk2-api/home-timeline/read?start=%s&stop=%s&user_id=%s" % (str(start), str(stop), str(self.user_id)),
            name="/wrk2-api/home-timeline/read")
        for post in eval(response.content):
            if len(post['media']) > 0:
                fname = post['media'][0]['media_id'] + '.' + post['media'][0]['media_type']
                self.client.get(
                    '%s/get-media?filename=%s' % (GLOBAL_MEDIA_FRONTEND_URL, fname),
                    name='/get-media')

    @task(5)
    def readUserTimeline(self):
        start = random.randint(0, 100)
        stop = start + 10
        user_id = random.choice(friends[self.user_id])

        response = self.client.get(
            "/wrk2-api/user-timeline/read?start=%s&stop=%s&user_id=%s" % (str(start), str(stop), str(user_id)),
            name='/wrk2-api/user-timeline/read')
        for post in eval(response.content):
            if len(post['media']) > 0:
                fname = post['media'][0]['media_id'] + '.' + post['media'][0]['media_type']
                self.client.get(
                    '%s/get-media?filename=%s' % (GLOBAL_MEDIA_FRONTEND_URL, fname),
                    name='/get-media')

    @task(5)
    def composePost(self):
        text = random.choice(texts)

        # User mentions
        number_of_user_mentions = random.randint(0, min(5, len(friends[self.user_id])))
        if number_of_user_mentions > 0:
            for friend_id in random.choices(friends[self.user_id], k=number_of_user_mentions):
                text += " @username_" + str(friend_id)
        # Media
        media_id = ''
        media_type = ''
        if random.random() < 0.20:
            with open(random.choice(media), "rb") as f:
                media_response = self.client.post('%s/upload-media' % GLOBAL_MEDIA_FRONTEND_URL,
                                                  files={"media": f})
            if media_response.ok:
                media_json = eval(media_response.text)
                media_id = '"%s"' % media_json['media_id']
                media_type = '"%s"' % media_json['media_type']
        # URLs - Note: no need to add it as the original post content has URLs already

        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        data = {'username': 'username_' + str(self.user_id),
                'user_id': str(self.user_id),
                'text': text,
                'media_ids': "[" + str(media_id) + "]",
                'media_types': "[" + str(media_type) + "]",
                'post_type': '0'}

        self.client.post("/wrk2-api/post/compose", data=data, headers=headers)

    def on_stop(self):
        active_users.remove(self.user_id)
        inactive_users.append(self.user_id)

    def on_start(self):
        self.user_id = random.choice(inactive_users)
        active_users.append(self.user_id)
        inactive_users.remove(self.user_id)

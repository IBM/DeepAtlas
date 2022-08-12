from tqdm import tqdm
import resource
import random
import requests
import os
import time
resource.setrlimit(resource.RLIMIT_NOFILE, (250000, 250000))


########################################################################################################################
# Simulation Configuration
########################################################################################################################
GLOBAL_NGINX_FRONTEND_URL  = 'http://c4130-110233.wisc.cloudlab.us:31347/frontend'
GLOBAL_MEDIA_FRONTEND_URL  = 'http://c4130-110233.wisc.cloudlab.us:31347/media'


########################################################################################################################
texts = [text.replace('@', '') for text in list(open('datasets/fb-posts/news.txt'))]
media = [os.path.join('datasets/inria-person', fname) for fname in os.listdir('datasets/inria-person')]
users = list(range(1, 963))

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


def composePost(user_id):
    text = random.choice(texts)

    # User mentions
    number_of_user_mentions = random.randint(0, min(5, len(friends[user_id])))
    if number_of_user_mentions > 0:
        for friend_id in random.choices(friends[user_id], k=number_of_user_mentions):
            text += " @username_" + str(friend_id)
    # Media
    media_id = ''
    media_type = ''
    if random.random() < 0.20:
        with open(random.choice(media), "rb") as f:
            media_response = requests.post('%s/upload-media' % GLOBAL_MEDIA_FRONTEND_URL, files={"media": f})
        if media_response.ok:
            media_json = eval(media_response.text)
            media_id = '"%s"' % media_json['media_id']
            media_type = '"%s"' % media_json['media_type']
    # URLs - Note: no need to add it as the original post content has URLs already

    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    data = {'username': 'username_' + str(user_id),
            'user_id': str(user_id),
            'text': text,
            'media_ids': "[" + str(media_id) + "]",
            'media_types': "[" + str(media_type) + "]",
            'post_type': '0'}

    requests.post("%s/wrk2-api/post/compose" % GLOBAL_NGINX_FRONTEND_URL, data=data, headers=headers)


pbar = tqdm(users)
for user_id in pbar:
    for i in range(100):
        pbar.set_description('Iter %d/100' % i)
        composePost(user_id)
        time.sleep(1 / 50)

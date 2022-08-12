import matplotlib.pyplot as plt
import numpy as np
import pickle
from datetime import datetime
from constants import *
import random
import math


with open('./experiments/story/telemetry.pkl', 'rb') as f:
    data = pickle.load(f)
timestamps = data['timestamps']

LOW_DAYS = 3
HIGH_DAYS = 7
GLOBAL_SECONDS_PER_DAY = 60 * 10
GLOBAL_MIN_USERS_I         = 50
GLOBAL_MIN_USERS_II        = 150
GLOBAL_PEAKS_I             = [180, 200, 220]
GLOBAL_PEAKS_II            = [540, 600, 660]
GLOBAL_RANDOMNESS          = 0.10
_second_of_day = None
cycle = 0
peak_one_users = None
peak_two_users = None


def tick(get_run_time):
    global cycle, _second_of_day, peak_one_users, peak_two_users
    second_of_day = round(get_run_time) % GLOBAL_SECONDS_PER_DAY
    if _second_of_day is None or second_of_day < _second_of_day:
        cycle += 1
        global_peak = GLOBAL_PEAKS_I if cycle <= LOW_DAYS else GLOBAL_PEAKS_II
        peak_one_users = random.choice(global_peak)
        peak_two_users = random.choice(global_peak)
    _second_of_day = second_of_day
    min_users = GLOBAL_MIN_USERS_I if cycle <= LOW_DAYS else GLOBAL_MIN_USERS_II
    user_count = (
            (peak_one_users - min_users)
            * math.e ** -(((second_of_day / (GLOBAL_SECONDS_PER_DAY / 10 * 2 / 3)) - 5) ** 2)
            + (peak_two_users - min_users)
            * math.e ** -(((second_of_day / (GLOBAL_SECONDS_PER_DAY / 10 * 2 / 3)) - 10) ** 2)
            + min_users
    )
    max_offset = math.ceil(user_count * GLOBAL_RANDOMNESS)
    user_count += random.choice(list(range(-max_offset, max_offset + 1)))
    return round(user_count)


compositions1 = {'/wrk2-api/user/login': 8, '/wrk2-api/user/register': 8, '/wrk2-api/user/follow': 8, '/wrk2-api/user/unfollow': 2,
                 '/wrk2-api/home-timeline/read': 50, '/wrk2-api/user-timeline/read': 10, '/wrk2-api/post/compose': 15}
compositions2 = {'/wrk2-api/user/login': 8, '/wrk2-api/user/register': 8, '/wrk2-api/user/follow': 8, '/wrk2-api/user/unfollow': 2,
                 '/wrk2-api/home-timeline/read': 50, '/wrk2-api/user-timeline/read': 10, '/wrk2-api/post/compose': 215}  # TODO: Try 2x first, then if OK, 3x

xs, ys = [], []
API = np.zeros(shape=(len(timestamps)*5, len(API2ID)))
for i in range(len(timestamps)*5):
    a = tick(i)

    xs.append(i)
    ys.append(a)
    denominator = sum(list(compositions1.values() if cycle <= LOW_DAYS else compositions2.values()))

    for api, weight in (compositions1.items() if cycle <= LOW_DAYS else compositions2.items()):
        API[i, API2ID[api]] = int(a * weight / denominator)

plt.plot(xs, ys)
plt.plot(xs, API.sum(axis=1))
plt.show()

API_ = API.transpose()
print([l.shape for l in API_])
plt.stackplot(range(len(xs)), *[l for l in API_])
plt.show()
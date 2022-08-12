from datetime import datetime, timedelta
import pickle
import urllib.request
import json
from tqdm import tqdm

JAEGER_URL = 'http://c4130-110233.wisc.cloudlab.us:32285/'
START_TIME = datetime(2022, 6, 20, 12, 55, 50)
END_TIME   = datetime(2022, 6, 20, 14, 00, 00)

query_url = JAEGER_URL + 'api/traces?lookback=custom&maxDuration&minDuration&service=sn-nginx&start=%s&end=%s&limit=10000'

start_time_milliseconds = int(START_TIME.timestamp() * 1e6)
end_time_milliseconds = int(END_TIME.timestamp() * 1e6)
step_milliseconds = int(1 * 1e6)
window_milliseconds = int(2 * 1e6)

buffer_keys = set()
pbar = tqdm(range(start_time_milliseconds, end_time_milliseconds, step_milliseconds))
for curr_time_milliseconds in pbar:
    with urllib.request.urlopen(query_url % (curr_time_milliseconds, curr_time_milliseconds + window_milliseconds)) as url:
        data = json.loads(url.read().decode())['data']
    pbar.set_description('Buffer: %d | Batch: %d' % (len(buffer_keys), len(data)))
    for trace in data:
        buffer_keys.add(trace['traceID'])

from datetime import datetime, timedelta
import pickle
import urllib.request
import json
from tqdm import tqdm

JAEGER_URL = 'http://c220g1-031116.wisc.cloudlab.us:32688/'
START_TIME = datetime(2022, 6, 17, 12, 40, 00)
END_TIME   = datetime(2022, 6, 17, 14, 00, 00)

query_url = JAEGER_URL + 'api/traces?lookback=custom&maxDuration&minDuration&service=sn-nginx&start=%s&end=%s&limit=10000'

start_time_milliseconds = int(START_TIME.timestamp() * 1e6)
end_time_milliseconds = int(END_TIME.timestamp() * 1e6)
step_milliseconds = int(5 * 1e6)
window_milliseconds = int(10 * 1e6)

buffer_id = 0
buffer_keys = set()
buffer = []
pbar = tqdm(range(start_time_milliseconds, end_time_milliseconds, step_milliseconds))
for curr_time_milliseconds in pbar:
    with urllib.request.urlopen(query_url % (curr_time_milliseconds, curr_time_milliseconds + window_milliseconds)) as url:
        data = json.loads(url.read().decode())['data']
    pbar.set_description('Buffer: %d | Batch: %d' % (len(buffer), len(data)))

    for trace in data:
        traceID = trace['traceID']
        if traceID in buffer_keys:
            continue
        buffer_keys.add(traceID)
        buffer.append(trace)
    if len(buffer) >= 10000:
        # Flush
        with open('./data/20220617-traces/buffer_%.6d.pkl' % buffer_id, 'wb') as o:
            pickle.dump(buffer, o)
        buffer = []
        buffer_id += 1

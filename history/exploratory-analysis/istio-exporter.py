import pickle
from datetime import datetime
from urllib import request, parse

import matplotlib.pyplot as plt
import numpy as np
import json

PROMETHEUS_URL = 'http://c220g1-031116.wisc.cloudlab.us:31268/'
START_TIME = datetime(2022, 6, 17, 12, 40, 00)
END_TIME   = datetime(2022, 6, 17, 14, 00, 00)
OUTPUT_ID  = '20220617-metrics'


def prometheus_query(query, start=int(START_TIME.timestamp()), end=int(END_TIME.timestamp()), step=5):
    url = PROMETHEUS_URL + 'api/v1/query_range?query=%s' % parse.quote(query)
    if start is not None:
        url += '&start=%d' % start
    if end is not None:
        url += '&end=%d' % end
    if step is not None:
        url += '&step=%d' % step
    with request.urlopen(url) as u:
        data = json.loads(u.read().decode())
    assert data['status'] == 'success', 'Error: %s' % data
    return data


def istio_query(query):
    _data = prometheus_query(query)
    ret = {}
    for result in _data['data']['result']:
        metric = result['metric']
        key = (metric['source_app'], metric['destination_app'])
        if 'unknown' in key:  # TODO:
            continue
        reporter = ['source', 'destination']['unknown' in key]
        if metric['reporter'] == reporter:
            timestamps, measurements = zip(*result['values'])
            timestamps = list(map(int, timestamps))
            measurements = list(map(float, measurements))
            assert key not in ret
            ret[key] = (timestamps, measurements)
    return ret


with open('./data/%s.json' % OUTPUT_ID) as f:
    data = json.load(f)
istio_sent = istio_query(query='rate(istio_tcp_sent_bytes_total[1m])')
istio_received = istio_query(query='rate(istio_tcp_received_bytes_total[1m])')

for container in data['components']:
    data['components'][container]['outbound-to'] = {}
    data['components'][container]['inbound-from'] = {}

    # istio_tcp_received_bytes_total
    for (source, destination), (timestamps, measurements) in istio_received.items():
        assert timestamps == data['timestamps'], 'Timestamps mismatch. Check start time and end time.'
        if source == container:
            data['components'][container]['outbound-to'][destination] = measurements
        if destination == container:
            data['components'][container]['inbound-from'][source] = measurements
    # istio_tcp_sent_bytes_total
    for (source, destination), (timestamps, measurements) in istio_sent.items():
        assert timestamps == data['timestamps'], 'Timestamps mismatch. Check start time and end time.'
        if source == container:
            data['components'][container]['inbound-from'][destination] = measurements
        if destination == container:
            data['components'][container]['outbound-to'][source] = measurements


with open("./data/%s-istio.json" % OUTPUT_ID, "w") as outfile:
    json.dump(data, outfile)

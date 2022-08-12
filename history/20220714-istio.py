from urllib import request, parse
from datetime import datetime
import json

PROMETHEUS_URL = 'http://amd125.utah.cloudlab.us:30343/'
EXPERIMENT_ID = '202207131729_202207141313'

START_TIME = datetime(int(EXPERIMENT_ID[0:4]), int(EXPERIMENT_ID[4:6]), int(EXPERIMENT_ID[6:8]),
                      int(EXPERIMENT_ID[8:10]), int(EXPERIMENT_ID[10:12]), 00)
END_TIME   = datetime(int(EXPERIMENT_ID[13:17]), int(EXPERIMENT_ID[17:19]), int(EXPERIMENT_ID[19:21]),
                      int(EXPERIMENT_ID[21:23]), int(EXPERIMENT_ID[23:25]), 00)


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
        if 'unknown' in key:
            continue
        if metric['reporter'] == 'source':
            timestamps, measurements = zip(*result['values'])
            timestamps = list(map(int, timestamps))
            measurements = list(map(float, measurements))
            assert key not in ret, key
            ret[key] = (timestamps, measurements)
    return ret


with open('experiments/%s/cadvisor.json' % EXPERIMENT_ID) as f:
    data = json.load(f)
istio_sent = istio_query(query='rate(istio_tcp_sent_bytes_total[1m])')
istio_received = istio_query(query='rate(istio_tcp_received_bytes_total[1m])')
istio_sent_http = istio_query(query='rate(istio_request_bytes_sum{response_code="200"}[1m])')
istio_received_http = istio_query(query='rate(istio_response_bytes_sum{response_code="200"}[1m])')

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
    for (source, destination), (timestamps, measurements) in istio_received_http.items():
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
    for (source, destination), (timestamps, measurements) in istio_sent_http.items():
        assert timestamps == data['timestamps'], 'Timestamps mismatch. Check start time and end time.'
        if source == container:
            data['components'][container]['inbound-from'][destination] = measurements
        if destination == container:
            data['components'][container]['outbound-to'][source] = measurements

for component in ['nginx-thrift', 'media-frontend']:
    for name in data['components'][component]['outbound-to']:
        print('  TO: %s' % name)
    for name in data['components'][component]['inbound-from']:
        print('FROM: %s' % name)


with open('experiments/%s/cadvisor+istio.json' % EXPERIMENT_ID, 'w') as outfile:
    json.dump(data, outfile)

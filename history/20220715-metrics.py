import itertools
from urllib import request, parse
from datetime import datetime
import json

import matplotlib.pyplot as plt

PROMETHEUS_URL = 'http://amd125.utah.cloudlab.us:30343/'
EXPERIMENT_ID = '202207131538_202207131614'
EXPERIMENT_ID = '202207141248_202207141314'

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
            if key not in ret:
                ret[key] = []
            ret[key].append((timestamps, measurements))
    return ret


########################################################################################################################
# Discover all components in the namespace
########################################################################################################################
data = prometheus_query(query='sum(rate(container_cpu_usage_seconds_total{namespace="social-network", container!=""}[1m])) by (pod)')
components = {}
for result in data['data']['result']:
    cid = '-'.join(result['metric']['pod'].split('-')[:-2])
    components[cid] = {'id': cid}

########################################################################################################################
# Prometheus
########################################################################################################################
istio_sent = istio_query(query='rate(istio_tcp_sent_bytes_total[1m])')
istio_received = istio_query(query='rate(istio_tcp_received_bytes_total[1m])')
istio_sent_http = istio_query(query='rate(istio_request_bytes_sum{response_code="200"}[1m])')
istio_received_http = istio_query(query='rate(istio_response_bytes_sum{response_code="200"}[1m])')

edges = {}
for flow, data in istio_received.items():
    if flow not in edges:
        edges[flow] = {}
    xs, ys = [], []
    for tup in data:
        xs += tup[0]
        ys += tup[1]
    edges[flow]['request'] = sorted(zip(xs, ys), key=lambda d: d[0])
for flow, data in istio_sent.items():
    xs, ys = [], []
    for tup in data:
        xs += tup[0]
        ys += tup[1]
    edges[flow]['response'] = sorted(zip(xs, ys), key=lambda d: d[0])

for flow, data in istio_sent_http.items():
    if flow not in edges:
        edges[flow] = {}
    xs, ys = [], []
    for tup in data:
        xs += tup[0]
        ys += tup[1]
    edges[flow]['request'] = sorted(zip(xs, ys), key=lambda d: d[0])
for flow, data in istio_received_http.items():
    xs, ys = [], []
    for tup in data:
        xs += tup[0]
        ys += tup[1]
    edges[flow]['response'] = sorted(zip(xs, ys), key=lambda d: d[0])


src = 'user-service'
tar = 'user-mongodb'
xs, ys = zip(*edges[(src, tar)]['request'])
plt.plot(xs, [v * 1e-3 for v in ys])
plt.ylabel('Data Size (KB)')
plt.xlabel('Timeline')
plt.show()
# for component in ['nginx-thrift', 'media-frontend']:
#     for name in components[component]['outbound-to']:
#         print('  TO: %s' % name)
#     for name in components[component]['inbound-from']:
#         print('FROM: %s' % name)


exit()
queries = {
    'cpu': 'sum(rate(container_cpu_usage_seconds_total{namespace="social-network", container!=""}[1m])) by (pod)',
    'memory': 'sum(container_memory_rss{namespace="social-network", container!=""}) by (pod)',
    'traffic-in': 'sum(rate(container_network_receive_bytes_total{namespace="social-network"}[1m])) by (pod)',
    'traffic-out': 'sum(rate(container_network_transmit_bytes_total{namespace="social-network"}[1m])) by (pod)'
}

timestamps = None
for query_name, query in queries.items():
    data = prometheus_query(query=query)
    for result in data['data']['result']:
        cid = '-'.join(result['metric']['pod'].split('-')[:-2])
        assert cid in components, 'Pod `%s` has no container %s' % (result['metric']['pod'], cid)

        _timestamps = [int(tup[0]) for tup in result['values']]
        _values = [float(tup[1]) for tup in result['values']]
        components[cid][query_name] = _values
        if timestamps is None:
            timestamps = _timestamps
        assert timestamps == _timestamps, 'Timestamps are inconsistent!'


queries = {
    'write-iops': 'increase(openebs_writes{}[1m])/60',
    'read-iops': 'increase(openebs_reads{}[1m])/60',
    'write-throughput': 'increase(openebs_write_block_count{}[1m])*4096/60',
    'read-throughput': 'increase(openebs_read_block_count{}[1m])*4096/60',
    'disk-usage': 'openebs_actual_used{}'
}

for query_name, query in queries.items():
    data = prometheus_query(query=query)
    for result in data['data']['result']:
        pvc_name = result['metric']['openebs_pvc']
        cid = pvc_name.replace('-pvc', '')
        if cid not in components:
            print('No host is found for PVC `%s`' % pvc_name)
            continue
        assert cid in components, 'Pod `%s` has no container %s' % (result['metric']['pod'], cid)

        _timestamps = [int(tup[0]) for tup in result['values']]
        _values = [float(tup[1]) for tup in result['values']]
        components[cid][query_name] = _values
        assert timestamps == _timestamps, 'Timestamps are inconsistent!'

with open("experiments/%s/cadvisor.json" % EXPERIMENT_ID, "w") as outfile:
    json.dump({'components': components, 'timestamps': timestamps,
               'start': int(START_TIME.timestamp()), 'end': int(END_TIME.timestamp()), 'step': 5}, outfile)

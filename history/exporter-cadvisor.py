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
    print(url)
    with request.urlopen(url) as u:
        data = json.loads(u.read().decode())
    assert data['status'] == 'success', 'Error: %s' % data
    return data


########################################################################################################################
# Discover all components in the namespace
########################################################################################################################
data = prometheus_query(query='sum(rate(container_cpu_usage_seconds_total{namespace="social-network", container!=""}[1m])) by (pod)')
components = {}
for result in data['data']['result']:
    cid = '-'.join(result['metric']['pod'].split('-')[:-2])
    components[cid] = {'id': cid, 'stateful': False, 'pvcs': []}

########################################################################################################################
# Check stateful or stateless
########################################################################################################################
data = prometheus_query(query='openebs_actual_used{}')
for result in data['data']['result']:
    pvc_name = result['metric']['openebs_pvc']
    cid = pvc_name.replace('-pvc', '')
    if cid not in components:
        print('No host is found for PVC `%s`' % pvc_name)
        continue
    components[cid]['stateful'] = True
    components[cid]['pvcs'].append(pvc_name)

for cid, component in components.items():
    print('Component %s' % cid)
    for k, v in component.items():
        print('   > %s: %s' % (k, v))


########################################################################################################################
# Prometheus
########################################################################################################################
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

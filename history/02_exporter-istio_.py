import pickle
from urllib import request, parse
from datetime import datetime
from matplotlib import pyplot as plt
import numpy as np
import json

########################################################################################################################
PROMETHEUS_URL = 'http://c4130-110233.wisc.cloudlab.us:30913/'
EXPERIMENT_ID = '202208012125_202208012245'
########################################################################################################################

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


def process(data):
    edge2metric = {}
    for result in data['data']['result']:
        metric, values = result['metric'], result['values']
        edge = (metric['source_app'], metric['destination_app'])
        if metric['reporter'] != 'source' or 'unknown' in edge:
            continue
        xs = np.asarray([int(value[0]) for value in values])
        ys = np.asarray([float(value[1]) for value in values])
        assert edge not in edge2metric, 'Edge %s already exists.' % str(edge)
        edge2metric[edge] = (xs, ys)
    return edge2metric


def standardize(data, step=5):
    # Find the maximum and the minimum timestamps
    x_min, x_max = np.inf, -np.inf
    for traffic_type, edge2metric_list in data.items():
        for edge2metric in edge2metric_list:
            for edge, metric in edge2metric.items():
                x_min = min(x_min, np.min(metric[0]))
                x_max = max(x_max, np.max(metric[0]))
    xs = np.asarray(list(range(x_min, x_max + step, step)))

    # Make sure all metrics share the same x-axis
    edges = {}
    for traffic_type, edge2metric_list in data.items():
        for edge2metric in edge2metric_list:
            for edge, metric in edge2metric.items():
                if edge not in edges:
                    edges[edge] = {}
                ts2value = dict(zip(metric[0], metric[1]))
                edges[edge][traffic_type] = np.asarray([0. if x not in ts2value else ts2value[x] for x in xs])
    return xs, edges


istio_tcp_sent = process(prometheus_query('increase(istio_tcp_sent_bytes_total[1m])'))
istio_tcp_received = process(prometheus_query('increase(istio_tcp_received_bytes_total[1m])'))
istio_http_request = process(prometheus_query('increase(istio_request_bytes_sum{response_code="200"}[1m])'))
istio_http_response = process(prometheus_query('increase(istio_response_bytes_sum{response_code="200"}[1m])'))

xs, edges = standardize({'request': (istio_tcp_received, istio_http_request),
                         'response': (istio_tcp_sent, istio_http_response)})

with open('./experiments/%s/02_exporter-istio.pkl' % EXPERIMENT_ID, 'wb') as o:
    pickle.dump((xs, edges), o)


# for edge, data in edges.items():
#     plt.clf()
#     plt.title(edge)
#     plt.plot(xs, data['request'], label='request', color='red')
#     plt.plot(xs, data['response'], label='response', color='blue')
#     plt.legend()
#     plt.show()
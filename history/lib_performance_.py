from constants import *
from lib_cost import CostEstimator
from core.application import PlacementPlan
from core.experiment import Experiment
import numpy as np
import pickle
import copy


class PerformanceEstimator:
    MIN_OVERLAPPING = 0.10
    RTT_MICROSECONDS = 22700
    SPEED_MICROSECONDS_PER_BYTE = 1 / (1.25 * 1000)

    @staticmethod
    def get_duration(span, id2span):
        return int(sum((log if type(log) != list else max(
            _offset + PerformanceEstimator.get_duration(id2span[_spanID], id2span) for _offset, _spanID in log)
                        ) for log in span['logs']))

    def __init__(self, experiment_id, rtt=RTT_MICROSECONDS, speed=SPEED_MICROSECONDS_PER_BYTE):
        self.rtt = rtt
        self.speed = speed

        ################################################################################################################
        # Load data footprint and representative traces
        ################################################################################################################
        with open('./experiments/%s/04_network-footprint-learning.pkl' % experiment_id, 'rb') as f:
            self.data_footprint = pickle.load(f)

        ################################################################################################################
        # Load traces into our data structure
        ################################################################################################################
        with open('05_representative-traces_.pkl', 'rb') as f:
            repr_traces = pickle.load(f)

        self.repr_traces_ds = {}
        for api, traces in repr_traces.items():
            self.repr_traces_ds[api] = []
            for trace in traces:
                trace = trace[1:] if 'media' in api else trace[2:]

                # Add children to parent nodes for forward access
                spanID2span = {}
                for span in trace:
                    spanID = span['spanID']
                    spanID2span[spanID] = span
                    span['children'] = []
                    if len(span['references']) > 0:
                        parent_spanID = span['references'][0]['spanID']
                        for _span in trace:
                            if _span['spanID'] == parent_spanID:
                                _span['children'].append(spanID)

                _trace = []
                for span in trace:
                    spanID = span['spanID']
                    spanEndTime = span['startTime'] + span['duration']
                    children = span['children']
                    operationName = span['operationName'].replace('/wrk2-api/user', '')
                    serviceName = list(filter(lambda x: x['key'] == 'container.name', span['process']['tags']))[0]['value']
                    if (serviceName, operationName) in SPAN_MAPPING:
                        (serviceName, operationName) = SPAN_MAPPING[(serviceName, operationName)]

                    clusters = []
                    for child in children:
                        child_startTime = spanID2span[child]['startTime']
                        child_endTime = child_startTime + spanID2span[child]['duration']
                        child_isForeground = spanEndTime >= child_endTime
                        if not child_isForeground:
                            # If the span was a background job, there is no need to include it in the tree because it does not
                            # affect the API performance.
                            continue

                        child_range = set(list(range(child_startTime, child_endTime)))
                        max_overlapping, max_cid = PerformanceEstimator.MIN_OVERLAPPING, -1
                        for cid, cluster in enumerate(clusters):
                            cluster_startTime = spanID2span[cluster[0][1]]['startTime']
                            cluster_endTime = max(spanID2span[_spanID]['startTime'] + spanID2span[_spanID]['duration'] for _offset, _spanID in cluster)
                            cluster_range = set(list(range(cluster_startTime, cluster_endTime)))
                            overlapping = len(cluster_range.intersection(child_range)) / len(child_range)
                            if overlapping >= max_overlapping:
                                max_overlapping = overlapping
                                max_cid = cid
                        if max_cid >= 0:  # parallel execution
                            cluster_startTime = spanID2span[clusters[max_cid][0][1]]['startTime']
                            clusters[max_cid].append((child_startTime - cluster_startTime, child))
                        else:  # sequential execution
                            clusters.append([(0, child)])

                    logs = []
                    time_ptr = span['startTime']
                    for cluster in clusters:
                        cluster_startTime = spanID2span[cluster[0][1]]['startTime']
                        logs.append(cluster_startTime - time_ptr)
                        logs.append(cluster)
                        time_ptr = cluster_startTime + max(
                            _offset + spanID2span[_spanID]['duration'] for _offset, _spanID in cluster)
                    if len(children) > 0:
                        logs.append(span['startTime'] + span['duration'] - time_ptr)
                    else:
                        logs.append(span['duration'])

                    _span = {'spanID': spanID, 'operationName': operationName, 'serviceName': serviceName, 'logs': logs}
                    _trace.append(_span)
                _spanID2span = {_span['spanID']: _span for _span in _trace}
                groundtruth = trace[0]['duration']

                estimation = PerformanceEstimator.get_duration(_trace[0], _spanID2span)
                assert groundtruth == estimation, 'Ground truth does no match estimation before migration!'
                self.repr_traces_ds[api].append(_trace)

    def estimate(self, plan, critical_apis=(), detailed=False, weighted=True):
        if type(plan) != set:
            plan = plan.cloud_msvcs
        ret = {}
        for api, traces in self.repr_traces_ds.items():
            ret[api] = []
            for trace_pre in traces[:10]:
                trace_post = copy.deepcopy(trace_pre)
                spanID2span_pre = {span['spanID']: span for span in trace_pre}
                spanID2span_post = {span['spanID']: span for span in trace_post}
                for parentSpan in trace_post:
                    parentService = parentSpan['serviceName']
                    for i, log in enumerate(parentSpan['logs']):
                        if type(log) == list:
                            is_intercloud = False
                            childService = None
                            for _, childSpan in log:
                                childService = spanID2span_post[childSpan]['serviceName']
                                if (parentService in plan) != (childService in plan):
                                    is_intercloud = True
                                    break
                            if is_intercloud:
                                request_bytes = self.data_footprint[api][(parentService, childService)]['request']
                                response_bytes = self.data_footprint[api][(parentService, childService)]['response']
                                parentSpan['logs'][i - 1] += (self.rtt + request_bytes * self.speed)
                                parentSpan['logs'][i + 1] += (response_bytes * self.speed)
                pre_migration = PerformanceEstimator.get_duration(trace_pre[0], spanID2span_pre) * 1e-3
                post_migration = PerformanceEstimator.get_duration(trace_post[0], spanID2span_post) * 1e-3
                ret[api].append((pre_migration, post_migration))
        if not detailed:
            return np.mean([np.mean([vv[1] for vv in v]) / np.mean([vv[0] for vv in v]) for k, v in ret.items()])
        return ret


if __name__ == '__main__':
    # import json
    # APIs = ['/wrk2-api/post/compose', '/wrk2-api/home-timeline/read',
    #         '/get-media', '/upload-media', '/wrk2-api/user/follow', '/wrk2-api/user/login', '/wrk2-api/user/register']
    # API2fname = {
    #     '/wrk2-api/post/compose': 'compose', '/wrk2-api/home-timeline/read': 'hometimeline',
    #     '/get-media': 'getmedia', '/upload-media': 'uploadmedia',
    #     '/wrk2-api/user/follow': 'follow', '/wrk2-api/user/login': 'login', '/wrk2-api/user/register': 'register'
    # }
    #
    # repr = {}
    # for API in APIs:
    #     repr[API] = []
    #     with open('api-comparisons/original-%s.json' % API2fname[API]) as f:
    #         data = json.load(f)
    #         for trace in data['data']:
    #             spans = []
    #             for span in trace['spans']:
    #                 span['process'] = trace['processes'][span['processID']]
    #                 spans.append(span)
    #             spans = sorted(spans, key=lambda ttt: ttt['startTime'])
    #             repr[API].append(spans)
    # with open('05_representative-traces_.pkl', 'wb') as f:
    #     pickle.dump(repr, f)
    # exit()
    ########################################################################################################################
    exp = Experiment(path='experiments/story/cadvisor+istio.json')
    perf = PerformanceEstimator(experiment_id='202207302259_202207310221')
    plan = {component for component in exp.msvcs if component not in ('media-frontend', 'media-mongodb', 'media-service', 'nginx-thrift', 'post-storage-mongodb', 'unique-id-service', 'user-memcached', 'user-mention-service', 'user-mongodb', 'user-service')}

    results = perf.estimate(plan=plan, detailed=True)

    for api, r in results.items():
        print('%s: %.2fms -> %.2fms' % (api, np.mean([t[0] for t in r]), np.mean([t[1] for t in r])))

from constants import *
import numpy as np
import pickle
import copy


class PerformanceEstimator:
    MIN_OVERLAPPING = 0.10
    RTT_MICROSECONDS = 10000#22700
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
        with open('./experiments/%s/05_representative-traces.pkl' % experiment_id, 'rb') as f:
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

    def estimate(self, plan, critical_apis=(), detailed=False):
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
    from core.application import PlacementPlan
    from core.experiment import Experiment
    from lib_cost import CostEstimator

    ########################################################################################################################
    exp = Experiment(path='experiments/story/cadvisor+istio.json')
    perf = PerformanceEstimator(experiment_id='202207302259_202207310221')
    cost = CostEstimator()
    # plan = {'post-storage-service', 'unique-id-service', 'post-storage-memcached', 'user-timeline-mongodb', 'user-service', 'user-timeline-redis', 'write-home-timeline-rabbitmq', 'media-service', 'home-timeline-redis', 'home-timeline-service', 'compose-post-redis', 'user-timeline-service', 'url-shorten-mongodb', 'text-service', 'write-home-timeline-service', 'social-graph-redis', 'compose-post-service', 'url-shorten-service', 'social-graph-service', 'social-graph-mongodb', 'nginx-thrift'}
    # plan = {'post-storage-service', 'unique-id-service', 'post-storage-memcached', 'user-timeline-mongodb', 'user-service', 'user-timeline-redis', 'write-home-timeline-rabbitmq', 'media-service', 'home-timeline-redis', 'home-timeline-service', 'compose-post-redis', 'url-shorten-mongodb', 'user-timeline-service', 'media-frontend', 'text-service', 'media-memcached', 'write-home-timeline-service', 'url-shorten-memcached', 'media-mongodb', 'social-graph-redis', 'compose-post-service', 'url-shorten-service', 'social-graph-service', 'social-graph-mongodb', 'nginx-thrift'}
    # plan = {'post-storage-service', 'unique-id-service', 'post-storage-memcached', 'user-timeline-mongodb', 'user-service', 'user-timeline-redis', 'write-home-timeline-rabbitmq', 'media-service', 'home-timeline-redis', 'home-timeline-service', 'compose-post-redis', 'url-shorten-mongodb', 'user-timeline-service', 'media-frontend', 'text-service', 'write-home-timeline-service', 'url-shorten-memcached', 'media-mongodb', 'social-graph-redis', 'compose-post-service', 'url-shorten-service', 'social-graph-service', 'social-graph-mongodb', 'nginx-thrift'}
    # plan = {'post-storage-service', 'unique-id-service', 'post-storage-memcached', 'user-timeline-mongodb', 'user-service', 'user-timeline-redis', 'write-home-timeline-rabbitmq', 'media-service', 'home-timeline-redis', 'home-timeline-service', 'compose-post-redis', 'url-shorten-mongodb', 'user-timeline-service', 'text-service', 'media-memcached', 'write-home-timeline-service', 'url-shorten-memcached', 'social-graph-redis', 'compose-post-service', 'url-shorten-service', 'social-graph-service', 'social-graph-mongodb', 'nginx-thrift'}
    # plan = {'post-storage-service', 'unique-id-service', 'post-storage-memcached', 'user-timeline-mongodb', 'user-service', 'user-timeline-redis', 'write-home-timeline-rabbitmq', 'media-service', 'home-timeline-redis', 'home-timeline-service', 'compose-post-redis', 'url-shorten-mongodb', 'user-timeline-service', 'text-service', 'write-home-timeline-service', 'url-shorten-memcached', 'social-graph-redis', 'compose-post-service', 'url-shorten-service', 'social-graph-service', 'social-graph-mongodb', 'nginx-thrift'}
    # plan = {'post-storage-service', 'unique-id-service', 'post-storage-memcached', 'user-timeline-mongodb', 'user-service', 'user-timeline-redis', 'write-home-timeline-rabbitmq', 'media-service', 'home-timeline-redis', 'home-timeline-service', 'compose-post-redis', 'user-timeline-service', 'url-shorten-mongodb', 'text-service', 'write-home-timeline-service', 'social-graph-redis', 'compose-post-service', 'url-shorten-service', 'social-graph-service', 'social-graph-mongodb', 'nginx-thrift'}
    # plan = {'home-timeline-service', 'media-frontend', 'compose-post-redis', 'post-storage-service', 'text-service', 'unique-id-service', 'url-shorten-memcached', 'post-storage-memcached', 'user-timeline-mongodb', 'compose-post-service', 'user-service', 'user-timeline-redis', 'url-shorten-service', 'user-timeline-service', 'media-service', 'nginx-thrift', 'media-mongodb', 'url-shorten-mongodb'}
    plan = {component for component in exp.msvcs if component not in ('media-frontend', 'media-mongodb', 'user-mongodb', 'post-storage-mongodb')}
    # plan = {component for component in exp.msvcs if component not in {'media-mongodb', 'media-frontend', 'url-shorten-mongodb', 'user-timeline-redis'}}
    plan = {"compose-post-service", "home-timeline-redis", "nginx-thrift", "post-storage-service", "url-shorten-mongodb", "social-graph-redis", "user-service", "user-timeline-service", "home-timeline-service", "text-service", "compose-post-redis", "write-home-timeline-service", "user-timeline-redis", "social-graph-mongodb", "social-graph-service", "unique-id-service", "media-service", "user-timeline-mongodb", "post-storage-memcached", "url-shorten-service", "write-home-timeline-rabbitmq"}
    plan = {'user-mention-service', 'write-home-timeline-service', 'media-frontend', 'text-service', 'nginx-thrift', 'post-storage-service', 'compose-post-service', 'user-timeline-service', 'home-timeline-redis'}

    print(cost.estimate(plan=PlacementPlan(exp=exp, mapping={
        component: [PlacementPlan.ONPREM, PlacementPlan.CLOUD][component in plan] for component in exp.msvcs
    })))
    results = perf.estimate(plan=plan, detailed=True)

    labels = []
    men_means = []
    ratio = []
    women_means = []
    for api in results:
        data = results[api]
        print(api)
        print('   > Before: %.2fms' % np.mean([t[0] for t in data]))
        print('   > After : %.2fms (%.2fx)' % (np.mean([t[1] for t in data]), np.mean([t[1] for t in data]) / np.mean([t[0] for t in data])))
        ratio.append(np.mean([t[1] for t in data]) / np.mean([t[0] for t in data]))
        labels.append(READABLE_NAME[api])
        men_means.append(round(np.mean([t[0] for t in data]), 2))
        women_means.append(round(np.mean([t[1] for t in data]), 2))
    print(np.mean(ratio))
    from matplotlib import pyplot as plt
    plt.style.use('ggplot')

    x = np.arange(len(labels))  # the label locations
    width = 0.35  # the width of the bars

    fig, ax = plt.subplots()
    rects1 = ax.bar(x - width, men_means, width, label='Before Migration', color='tab:green')
    rects2 = ax.bar(x, women_means, width, label='After Migration - Busiest', color='tab:red')

    # Add some text for labels, title and custom x-axis tick labels, etc.
    ax.set_ylabel('End-to-end Latency (ms)')
    ax.set_xticks(x, labels)
    ax.legend()

    ax.bar_label(rects1, padding=3)
    ax.bar_label(rects2, padding=3)
    ax.set_ylim(0, 460)

    fig.tight_layout()

    plt.show()

    print(perf.estimate(plan={
        'compose-post-service',
        'nginx-thrift',
        'media-frontend',
        'user-mention-service',
        'text-service',
        'post-storage-service',
        'user-timeline-service',
        'write-home-timeline-service',
        }, detailed=False))
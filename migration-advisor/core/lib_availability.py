from utils.constants import *
import itertools


class AvailabilityEstimator:
    def __init__(self):
        self.msvc2apis = {}
        for api, edges in API2EDGES.items():
            for msvc in set(list(itertools.chain(*edges))):
                if msvc not in self.msvc2apis:
                    self.msvc2apis[msvc] = set()
                self.msvc2apis[msvc].add(api)

    def estimate(self, plan, critical_apis=(), detailed=False):
        if type(plan) not in (list, set):
            plan = plan.cloud_msvcs
        disruption = set()
        for msvc in plan:
            if 'mongodb' in msvc or 'home-timeline-redis' == msvc:
                for api in self.msvc2apis[msvc]:
                    disruption.add(api)

        if detailed:
            return list(disruption)

        if len(critical_apis) > 0:
            num_critical_unavailable = len(disruption.intersection(critical_apis))
            num_noncritical = len(API2ID) - len(critical_apis)
            num_noncritical_unavailable = len(set(API2ID.keys()).difference(critical_apis).intersection(disruption))
            score = num_critical_unavailable + num_noncritical_unavailable / num_noncritical
            return score
        return len(disruption)

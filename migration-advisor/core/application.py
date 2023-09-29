import matplotlib.pyplot as plt
import numpy as np


class Microservice:
    def __init__(self, config):
        self.id = config['id']
        self.pvcs = config['pvcs']

        # Metrics
        self.cpu = np.asarray(config['cpu'])  # cores
        self.memory = np.asarray(config['memory']) * 1e-9  # GB
        self.inbound_from = {mid: np.asarray(inbound) * 1e-9 for mid, inbound in config['inbound-from'].items()}  # GB
        self.outbound_to = {mid: np.asarray(outbound) * 1e-9 for mid, outbound in config['outbound-to'].items()}  # GB

        self.is_stateful = 'mongodb' in self.id
        zeros = np.zeros_like(self.cpu)
        self.disk_usage = np.asarray(config['disk-usage']) if self.is_stateful else zeros  # GB
        self.write_iops = np.asarray(config['write-iops']) if self.is_stateful else zeros
        self.read_iops = np.asarray(config['read-iops']) if self.is_stateful else zeros
        self.iops = self.write_iops + self.read_iops
        self.write_throughput = np.asarray(config['write-throughput']) if self.is_stateful else zeros
        self.read_throughput = np.asarray(config['read-throughput']) if self.is_stateful else zeros
        self.throughput = self.write_throughput + self.read_throughput


class PlacementUsage(object):
    def __init__(self, microservices):
        self.is_used = len(microservices) > 0
        self.cpu = np.sum(np.asarray([microservice.cpu for microservice in microservices.values()]), axis=0)
        self.memory = np.sum(np.asarray([microservice.memory for microservice in microservices.values()]), axis=0)
        self.iops = np.sum(np.asarray([microservice.iops for microservice in microservices.values()]), axis=0)
        self.throughput = np.sum(np.asarray([microservice.throughput for microservice in microservices.values()]), axis=0)
        self.disk_usage = np.sum(np.asarray([microservice.disk_usage for microservice in microservices.values()]), axis=0)


class PlacementPlan(object):
    ONPREM = 0
    CLOUD = 1

    def __init__(self, mapping, exp):
        self.mapping = mapping
        self.exp = exp
        self.onprem_msvcs = tuple(msvc for msvc, location in mapping.items() if location == PlacementPlan.ONPREM)
        self.cloud_msvcs = tuple(msvc for msvc, location in mapping.items() if location == PlacementPlan.CLOUD)
        self.onprem_usage = PlacementUsage({msvc: exp.microservices[msvc] for msvc in self.onprem_msvcs})
        self.cloud_usage = PlacementUsage({msvc: exp.microservices[msvc] for msvc in self.cloud_msvcs})

        self.onprem_usage_max_cpu = max(self.onprem_usage.cpu[exp.now:]) if self.onprem_usage.is_used else 0.
        self.onprem_usage_max_memory = max(self.onprem_usage.memory[exp.now:]) if self.onprem_usage.is_used else 0.
        self.onprem_usage_max_disk = max(self.onprem_usage.disk_usage[exp.now:]) if self.onprem_usage.is_used else 0.

        self.cost = None
        self.availability = None
        self.performance = None

    def is_intercloud_communication(self, mid_i, mid_j, gateway='istio-ingressgateway'):
        # assert False, 'on-prem istio -> free'
        if mid_i == gateway:
            return self.mapping[mid_j] == PlacementPlan.CLOUD
        elif mid_j == gateway:
            return self.mapping[mid_i] == PlacementPlan.CLOUD
        return self.mapping[mid_i] != self.mapping[mid_j]

    @property
    def is_feasible(self):
        if not self.onprem_usage.is_used:
            return True  # No resources are being used on-prem

        return self.onprem_usage_max_cpu < self.exp.config_onprem.LIMIT_CPU_CORE and \
               self.onprem_usage_max_memory < self.exp.config_onprem.LIMIT_MEMORY_GB and \
               self.onprem_usage_max_disk < self.exp.config_onprem.LIMIT_DISK_GB

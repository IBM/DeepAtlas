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

    # def cost_model(self):
    #     if self.cost is not None:
    #         return self.cost
    #
    #     cost_onprem = self._cost_model_onprem()
    #     cost_cloud = self._cost_model_cloud()
    #
    #     return cost_onprem + cost_cloud
    #
    # def _cost_model_onprem(self):
    #     if not self.onprem_usage.is_used:
    #         return 0.
    #     ################################################################################################################
    #     # 1) Compute Cost
    #     #    Get the maximum usage of CPU and memory at any time point. Compute the fractional usage with a 20% buffer.
    #     #    The larger one is the fraction of cost the application owner pays for the on-prem usage.
    #     ################################################################################################################
    #     cost_compute = 0
    #     frac_cpu_usage = (self.onprem_usage_max_cpu + self.onprem_usage_max_cpu * self.exp.config_onprem.COMPUTE_BUFFER) / self.exp.config_onprem.LIMIT_CPU_CORE
    #     frac_memory_usage = (self.onprem_usage_max_memory + self.onprem_usage_max_memory * self.exp.config_onprem.COMPUTE_BUFFER) / self.exp.config_onprem.LIMIT_MEMORY_GB
    #     frac = max(frac_cpu_usage, frac_memory_usage)
    #     for t in range(self.exp.now, len(self.exp.timestamps)):
    #         cost_compute += (self.exp.step_size * frac * self.exp.config_onprem.PRICE_INSTANCE_SECOND)
    #
    #     ################################################################################################################
    #     # 2) Storage Cost
    #     #    Assumption: the on-prem storage usage is the maximum usage with a 20% buffer at any time point.
    #     #    Round up to GB. The capacity is always bounded by the limit.
    #     ################################################################################################################
    #     cost_storage = 0
    #     max_usage_with_buffer = self.onprem_usage_max_disk + self.onprem_usage_max_disk * self.exp.config_onprem.STORAGE_BUFFER
    #     max_usage_with_buffer_rounded = np.ceil(max_usage_with_buffer)
    #     capacity = min(self.exp.config_onprem.LIMIT_DISK_GB, max_usage_with_buffer_rounded)
    #
    #     for t in range(self.exp.now, len(self.exp.timestamps)):
    #         cost_storage += (self.exp.step_size * capacity * self.exp.config_onprem.PRICE_DISK_GB_SECOND)
    #
    #     ################################################################################################################
    #     # 3) Traffic Cost
    #     ################################################################################################################
    #     cost_traffic = 0
    #
    #     return cost_compute + cost_storage + cost_traffic
    #
    # def _cost_model_cloud(self):
    #     if not self.cloud_usage.is_used:
    #         return 0.
    #
    #     ################################################################################################################
    #     # 1) Compute Cost
    #     #    Get the number of nodes for the CPU usage and the number of nodes for the memory usage. The larger one is
    #     #    the number of instances to be paid.
    #     ################################################################################################################
    #     cost_compute = 0
    #     num_machines = 0
    #     last_scaleup = -1
    #     for t in range(self.exp.now, len(self.exp.timestamps)):
    #         cpu_needed = self.cloud_usage.cpu[t] * 1.2        # 20% buffer
    #         memory_needed = self.cloud_usage.memory[t] * 1.2  # 20% buffer
    #         instances_needed = max(np.ceil(cpu_needed / self.exp.config_cloud.INSTANCE_CPU_CORE),
    #                                np.ceil(memory_needed / self.exp.config_cloud.INSTANCE_MEMORY_GB))
    #
    #         if num_machines == 0:  # initial
    #             num_machines = instances_needed
    #         elif instances_needed > num_machines:  # scale up
    #             num_machines = instances_needed
    #             last_scaleup = t
    #         elif instances_needed < num_machines and t - last_scaleup >= 5:  # scale down
    #             num_machines = instances_needed
    #         cost_compute += (self.exp.step_size * num_machines * self.exp.config_cloud.PRICE_INSTANCE_SECOND)
    #
    #     ################################################################################################################
    #     # 2) Storage Cost
    #     #    The initial capacity is 2 times the usage at the time when migration is conducted. Whenever 80% of the
    #     #    capacity is reached, the capacity is expanded by a factor of 1.2x.
    #     #    Note 1 - Minimum volume size in AWS gp3: 1 GB from https://www.amazonaws.cn/en/ebs/features/
    #     #    Note 2 - The autoscaling configuration comes from https://aws.amazon.com/blogs/storage/automating-amazon-ebs-volume-resizing-with-aws-step-functions-and-aws-systems-manager/
    #     #    Note 3 - Always round up to the nearest GB
    #     #    Note 4 - Autoscaling parameters can be changed in the CloudConfig class
    #     ################################################################################################################
    #     cost_storage = 0
    #     capacity = max(1., np.ceil(self.cloud_usage.disk_usage[self.exp.now] * self.exp.config_cloud.STORAGE_INIT_FACTOR))
    #     for t in range(self.exp.now, len(self.exp.timestamps)):
    #         cost_storage += (self.exp.step_size * capacity * self.exp.config_cloud.PRICE_DISK_GB_SECOND)
    #         disk_needed = self.cloud_usage.disk_usage[t]
    #         if disk_needed / capacity >= self.exp.config_cloud.STORAGE_EXPAND_TRIGGER_CAPACITY:
    #             # Autoscaling triggered
    #             capacity = np.ceil(capacity * self.exp.config_cloud.STORAGE_EXPAND_FACTOR)
    #
    #     ################################################################################################################
    #     # 3) Traffic Cost
    #     ################################################################################################################
    #     # TODO: Egress to the outside world
    #     cost_traffic = 0
    #     for msvc_from in self.exp.msvcs:
    #         for msvc_to, outbound_traffic in self.exp.microservices[msvc_from].outbound_to.items():  # outbound cost
    #             if self.is_intercloud_communication(msvc_from, msvc_to):
    #                 _cost_traffic = 0
    #                 for t in range(self.exp.now, len(self.exp.timestamps)):
    #                     data_transferred = outbound_traffic[t]
    #                     _cost_traffic += (
    #                             self.exp.step_size * data_transferred * self.exp.config_cloud.PRICE_EGRESS_TRAFFIC_GB)
    #                 cost_traffic += _cost_traffic
    #
    #     return cost_compute + cost_storage + cost_traffic
    #
    # def availability_model(self):
    #     if self.availability is not None:
    #         return self.availability
    #
    #     data_transferred = 0.
    #     data_total = 0.
    #     for msvc, location in self.mapping.items():
    #         usage = self.exp.microservices[msvc].disk_usage[self.exp.now]
    #         if location == PlacementPlan.CLOUD:
    #             data_transferred += usage
    #         data_total += usage
    #     return data_transferred * 100. / data_total
    #
    # def performance_model(self):
    #     if self.performance is not None:
    #         return self.performance
    #
    #     num_intercloud = 0
    #     for msvc_u, microservice in self.exp.microservices.items():
    #         for msvc_v, usage in microservice.outbound_to.items():
    #             if self.is_intercloud_communication(msvc_u, msvc_v):
    #                 num_intercloud += 1
    #     return num_intercloud

    @property
    def is_feasible(self):
        if not self.onprem_usage.is_used:
            return True  # No resources are being used on-prem

        return self.onprem_usage_max_cpu < self.exp.config_onprem.LIMIT_CPU_CORE and \
               self.onprem_usage_max_memory < self.exp.config_onprem.LIMIT_MEMORY_GB and \
               self.onprem_usage_max_disk < self.exp.config_onprem.LIMIT_DISK_GB

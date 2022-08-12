import numpy as np


class CostEstimator:
    def __init__(self):
        pass

    def estimate(self, plan, critical_apis=()):
        if plan.cost is not None:
            return plan.cost
        return self._cost_model_cloud(plan)

    @staticmethod
    def _cost_model_onprem(plan):
        if not plan.onprem_usage.is_used:
            return 0.
        ################################################################################################################
        # 1) Compute Cost
        #    Get the maximum usage of CPU and memory at any time point. Compute the fractional usage with a 20% buffer.
        #    The larger one is the fraction of cost the application owner pays for the on-prem usage.
        ################################################################################################################
        cost_compute = 0
        frac_cpu_usage = (plan.onprem_usage_max_cpu + plan.onprem_usage_max_cpu * plan.exp.config_onprem.COMPUTE_BUFFER) / plan.exp.config_onprem.LIMIT_CPU_CORE
        frac_memory_usage = (plan.onprem_usage_max_memory + plan.onprem_usage_max_memory * plan.exp.config_onprem.COMPUTE_BUFFER) / plan.exp.config_onprem.LIMIT_MEMORY_GB
        frac = max(frac_cpu_usage, frac_memory_usage)
        for t in range(plan.exp.now, len(plan.exp.timestamps)):
            cost_compute += (plan.exp.step_size * frac * plan.exp.config_onprem.PRICE_INSTANCE_SECOND)

        ################################################################################################################
        # 2) Storage Cost
        #    Assumption: the on-prem storage usage is the maximum usage with a 20% buffer at any time point.
        #    Round up to GB. The capacity is always bounded by the limit.
        ################################################################################################################
        cost_storage = 0
        max_usage_with_buffer = plan.onprem_usage_max_disk + plan.onprem_usage_max_disk * plan.exp.config_onprem.STORAGE_BUFFER
        max_usage_with_buffer_rounded = np.ceil(max_usage_with_buffer)
        capacity = min(plan.exp.config_onprem.LIMIT_DISK_GB, max_usage_with_buffer_rounded)

        for t in range(plan.exp.now, len(plan.exp.timestamps)):
            cost_storage += (plan.exp.step_size * capacity * plan.exp.config_onprem.PRICE_DISK_GB_SECOND)

        ################################################################################################################
        # 3) Traffic Cost
        ################################################################################################################
        cost_traffic = 0

        return cost_compute + cost_storage + cost_traffic

    @staticmethod
    def _cost_model_cloud(plan):
        if not plan.cloud_usage.is_used:
            return 0.

        ################################################################################################################
        # 1) Compute Cost
        #    Get the number of nodes for the CPU usage and the number of nodes for the memory usage. The larger one is
        #    the number of instances to be paid.
        ################################################################################################################
        cost_compute = 0
        num_machines = 0
        last_scaleup = -1
        for it, t in enumerate(range(plan.exp.now, len(plan.exp.timestamps))):
            cpu_needed = plan.cloud_usage.cpu[t] * 1.2        # 20% buffer
            memory_needed = plan.cloud_usage.memory[t] * 1.2  # 20% buffer
            instances_needed = max(np.ceil(cpu_needed / plan.exp.config_cloud.INSTANCE_CPU_CORE),
                                   np.ceil(memory_needed / plan.exp.config_cloud.INSTANCE_MEMORY_GB))
            if num_machines == 0:  # initial
                num_machines = instances_needed
            elif instances_needed > num_machines:  # scale up
                num_machines = instances_needed
                last_scaleup = t
            elif instances_needed < num_machines and t - last_scaleup >= 5:  # scale down
                num_machines = instances_needed
            cost_compute += (plan.exp.step_size * num_machines * plan.exp.config_cloud.PRICE_INSTANCE_SECOND)

        ################################################################################################################
        # 2) Storage Cost
        #    The initial capacity is 2 times the usage at the time when migration is conducted. Whenever 80% of the
        #    capacity is reached, the capacity is expanded by a factor of 1.2x.
        #    Note 1 - Minimum volume size in AWS gp3: 1 GB from https://www.amazonaws.cn/en/ebs/features/
        #    Note 2 - The autoscaling configuration comes from https://aws.amazon.com/blogs/storage/automating-amazon-ebs-volume-resizing-with-aws-step-functions-and-aws-systems-manager/
        #    Note 3 - Always round up to the nearest GB
        #    Note 4 - Autoscaling parameters can be changed in the CloudConfig class
        ################################################################################################################
        cost_storage = 0
        capacity = max(1., np.ceil(plan.cloud_usage.disk_usage[plan.exp.now] * plan.exp.config_cloud.STORAGE_INIT_FACTOR))
        for t in range(plan.exp.now, len(plan.exp.timestamps)):
            cost_storage += (plan.exp.step_size * capacity * plan.exp.config_cloud.PRICE_DISK_GB_SECOND)
            disk_needed = plan.cloud_usage.disk_usage[t]
            if disk_needed / capacity >= plan.exp.config_cloud.STORAGE_EXPAND_TRIGGER_CAPACITY:
                # Autoscaling triggered
                capacity = np.ceil(capacity * plan.exp.config_cloud.STORAGE_EXPAND_FACTOR)

        ################################################################################################################
        # 3) Traffic Cost
        ################################################################################################################
        cost_traffic = 0
        for msvc_from in plan.exp.msvcs:
            for msvc_to, outbound_traffic in plan.exp.microservices[msvc_from].outbound_to.items():  # outbound cost
                if plan.is_intercloud_communication(msvc_from, msvc_to):
                    _cost_traffic = 0
                    for t in range(plan.exp.now, len(plan.exp.timestamps)):
                        data_transferred = outbound_traffic[t]
                        _cost_traffic += (
                                plan.exp.step_size * data_transferred * plan.exp.config_cloud.PRICE_EGRESS_TRAFFIC_GB)
                    cost_traffic += _cost_traffic
        return cost_compute + cost_storage + cost_traffic

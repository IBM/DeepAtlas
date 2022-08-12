from moo import is_pareto
from tqdm import tqdm
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime
import itertools
import pickle
import random
import json
from plotly.subplots import make_subplots


class Microservice:
    def __init__(self, config):
        self.id = config['id']
        self.pvcs = config['pvcs']

        # Metrics
        self.cpu = np.asarray(config['cpu'])  # cores
        self.memory = np.asarray(config['memory']) * 1e-9  # GB
        self.inbound_from = {mid: np.asarray(inbound) * 1e-9 for mid, inbound in config['inbound-from'].items()}  # GB
        self.outbound_to = {mid: np.asarray(outbound) * 1e-9 for mid, outbound in config['outbound-to'].items()}  # GB

        self.is_stateful = config['stateful']
        zeros = np.zeros_like(self.cpu)
        self.disk_usage = np.asarray(config['disk-usage']) if self.is_stateful else zeros  # GB
        self.write_iops = np.asarray(config['write-iops']) if self.is_stateful else zeros
        self.read_iops = np.asarray(config['read-iops']) if self.is_stateful else zeros
        self.iops = self.write_iops + self.read_iops
        self.write_throughput = np.asarray(config['write-throughput']) if self.is_stateful else zeros
        self.read_throughput = np.asarray(config['read-throughput']) if self.is_stateful else zeros
        self.throughput = self.write_throughput + self.read_throughput


class PlacementUsage(object):
    def __init__(self, mids):
        self.cpu = np.sum(np.asarray([microservices[_id].cpu for _id in mids]), axis=0)
        self.memory = np.sum(np.asarray([microservices[_id].memory for _id in mids]), axis=0)
        self.write_iops = np.sum(np.asarray([microservices[_id].write_iops for _id in mids]), axis=0)
        self.read_iops = np.sum(np.asarray([microservices[_id].read_iops for _id in mids]), axis=0)
        self.iops = np.sum(np.asarray([microservices[_id].iops for _id in mids]), axis=0)
        self.write_throughput = np.sum(np.asarray([microservices[_id].write_throughput for _id in mids]), axis=0)
        self.read_throughput = np.sum(np.asarray([microservices[_id].read_throughput for _id in mids]), axis=0)
        self.disk_usage = np.sum(np.asarray([microservices[_id].disk_usage for _id in mids]), axis=0)


class OnPremConfig(object):
    LIMIT_CPU_CORE = 4
    LIMIT_MEMORY_GB = 8
    LIMIT_DISK_GB = 10


class CloudConfig(object):
    INSTANCE_CPU_CORE = 2
    INSTANCE_MEMORY_GB = 8
    PRICE_INSTANCE_SECOND = 0.096 / 3600
    PRICE_DISK_GB_SECOND = 0.08 / 2592000
    PRICE_EGRESS_TRAFFIC_GB = 0.09


class PlacementPlan(object):
    def __init__(self, onprem_mids, offloaded_mids):
        self.onprem_mids = onprem_mids
        self.offloaded_mids = offloaded_mids
        self.onprem_usage = PlacementUsage(mids=onprem_mids)
        self.offloaded_usage = PlacementUsage(mids=offloaded_mids)

    def is_intercloud_communication(self, mid_i, mid_j):
        return (mid_i in self.onprem_mids and mid_j in self.offloaded_mids) or \
               (mid_i in self.offloaded_mids and mid_j in self.onprem_mids)

    def cost_model(self):
        # TODO: Pricing granularity
        ################################################################################################################
        # 1) Compute Cost
        ################################################################################################################
        cost_compute = 0
        for t in range(t_now, len(timestamps)):
            cpu_needed = self.offloaded_usage.cpu[t]
            memory_needed = self.offloaded_usage.memory[t]
            instances_needed = max(np.ceil(cpu_needed / CloudConfig.INSTANCE_CPU_CORE),
                                   np.ceil(memory_needed / CloudConfig.INSTANCE_MEMORY_GB))
            cost_compute += (step_size * instances_needed * CloudConfig.PRICE_INSTANCE_SECOND)

        ################################################################################################################
        # 2) Storage Cost
        ################################################################################################################
        cost_storage = 0
        for t in range(t_now, len(timestamps)):
            disk_needed = self.offloaded_usage.disk_usage[t]
            cost_storage += (step_size * disk_needed * CloudConfig.PRICE_DISK_GB_SECOND)

        ################################################################################################################
        # 3) Traffic Cost
        ################################################################################################################
        cost_traffic = 0
        for mid_from in microservices:
            for mid_to, outbound_traffic in microservices[mid_from].outbound_to.items():  # outbound cost
                if self.is_intercloud_communication(mid_from, mid_to):
                    _cost_traffic = 0
                    for t in range(t_now, len(timestamps)):
                        data_transferred = outbound_traffic[t]
                        _cost_traffic += (step_size * data_transferred * CloudConfig.PRICE_EGRESS_TRAFFIC_GB)
                    cost_traffic += _cost_traffic
        return cost_compute + cost_storage + cost_traffic

    def availability_model(self):
        data_to_be_transferred = 0.
        for mid, microservice in microservices.items():
            if mid in self.offloaded_mids:
                data_to_be_transferred += max(microservice.disk_usage[:t_now])
        return data_to_be_transferred

    def performance_model(self):
        num_intercloud = 0
        for mid in microservices:
            for mid_to, usage in microservices[mid].outbound_to.items():
                if self.is_intercloud_communication(mid, mid_to):
                    num_intercloud += 1
        return num_intercloud

    @property
    def is_valid(self):
        return max(self.onprem_usage.cpu) < OnPremConfig.LIMIT_CPU_CORE and \
               max(self.onprem_usage.memory) < OnPremConfig.LIMIT_MEMORY_GB and \
               max(self.onprem_usage.disk_usage) < OnPremConfig.LIMIT_DISK_GB


with open('../exploratory-analysis/data/20220617-metrics-istio.json') as f:
    data = json.load(f)
microservices = {k: Microservice(config=v) for k, v in data['components'].items()}
timestamps = data['timestamps']
step_size = data['step']
speedup_factor = 144
step_size *= speedup_factor
mids = list(microservices.keys())
t_now = 28 * 60 // 5
timestamps_dt = [datetime.fromtimestamp(1641024000 + t * step_size) for t in range(len(timestamps))]

print('Number of Components       : %d' % len(microservices))
print('Number of Placement Choices: %d' % (2 ** len(microservices)))

xs_cost = []
ys_effort = []
zs_latency = []
customdata = []
for _ in tqdm(range(1000)):
    sample_size = random.choice(range(1, 29))
    offloaded_mids = random.sample(mids, k=sample_size)
    onprem_mids = list(set(mids).difference(offloaded_mids))

    plan = PlacementPlan(onprem_mids=onprem_mids, offloaded_mids=offloaded_mids)
    if plan.is_valid:
        cost = plan.cost_model()
        availability = plan.availability_model()
        latency = plan.performance_model()
        xs_cost.append(cost)
        ys_effort.append(availability)
        zs_latency.append(latency)

        c1 = '<br>'.join(['   %d) %s%s' % (num + 1, mid,
                                           '  (Stateful: %.4fGB)' % (max(microservices[mid].disk_usage[:t_now])) if
                                           microservices[mid].is_stateful else '') for num, mid in
                          enumerate(onprem_mids)])
        c2 = '<br>'.join(['   %d) %s%s' % (num + 1, mid,
                                           '  (Stateful: %.4fGB)' % (max(microservices[mid].disk_usage[:t_now])) if
                                           microservices[mid].is_stateful else '') for num, mid in
                          enumerate(offloaded_mids)])
        customdata.append((c1, c2, len(onprem_mids), len(offloaded_mids),
                           (sum(microservices[mid].is_stateful for mid in plan.offloaded_mids))))

xs_cost = np.asarray(xs_cost)
ys_effort = np.asarray(ys_effort)
zs_latency = np.asarray(zs_latency)
M = np.asarray([xs_cost, ys_effort, zs_latency]).transpose()
ind = is_pareto(M, maximise=False)

plt.scatter(xs_cost, ys_effort, label='Non-optimal Plans')
plt.scatter(M[ind][:, 0], M[ind][:, 1], color='red', label='Pareto-optimal Plans')
pareto_front = np.asarray(sorted(list(M[ind]), key=lambda x: x[0]))
plt.plot(pareto_front[:, 0], pareto_front[:, 1], color='red')
plt.xlabel('Cost (USD)')
plt.ylabel('Data Migration (GB)')
plt.legend()
# plt.show()
#
# exit()
hovertemplate = '<b>Cost: USD %{x:.2f}</b><br>' \
                '<b>Data Migration: %{y:.4f}GB</b><br>' \
                '<b>Intercloud Links: %{z}</b><br><br><b>===== Placement Plan =====</b><br>' \
                'Keep %{customdata[2]:d} components on-prem:<br>' \
                '%{customdata[0]}' \
                '<br>Offload %{customdata[3]:d} components (%{customdata[4]:d} stateful) to the cloud:<b></b><br>' \
                '%{customdata[1]}'
customdata_opt = np.asarray(customdata)[ind]
customdata_nopt = np.asarray(customdata)[np.logical_not(ind)]

fig = make_subplots(
    rows=4, cols=2, column_widths=[0.4, 0.6],
    specs=[[{}, {"rowspan": 4, 'type': 'scene'}], [{}, {}], [{}, {}], [{}, {}]],
    subplot_titles=(
    "CPU Usage", "Placement Plans (Hover to See the Placement)", "Memory Usage", "", "Disk Usage", "", "IOps Usage"))

max_cpu, max_memory, max_disk, max_iops = 0, 0, 0, 0
for mid, microservice in microservices.items():
    fig.add_trace(go.Scatter(name=mid, x=timestamps_dt, y=microservice.cpu, stackgroup='cpu'), row=1, col=1)
    fig.add_trace(go.Scatter(name=mid, x=timestamps_dt, y=microservice.memory, stackgroup='memory'), row=2, col=1)
    fig.add_trace(go.Scatter(name=mid, x=timestamps_dt, y=microservice.disk_usage, stackgroup='disk'), row=3, col=1)
    fig.add_trace(go.Scatter(name=mid, x=timestamps_dt, y=microservice.iops, stackgroup='iops'), row=4, col=1)
fig.update_yaxes(title_text="Cores", row=1, col=1)
fig.add_shape(type="rect", x0=timestamps_dt[t_now], x1=timestamps_dt[-1], y0=0, y1=OnPremConfig.LIMIT_CPU_CORE,
              line=dict(width=0), fillcolor="green", opacity=0.2, row=1, col=1)

fig.update_yaxes(title_text="GB", row=2, col=1)
fig.add_shape(type="rect", x0=timestamps_dt[t_now], x1=timestamps_dt[-1], y0=0, y1=OnPremConfig.LIMIT_MEMORY_GB,
              line=dict(width=0), fillcolor="green", opacity=0.2, row=2, col=1)
fig.update_yaxes(title_text="GB", row=3, col=1)
fig.add_shape(type="rect", x0=timestamps_dt[t_now], x1=timestamps_dt[-1], y0=0, y1=OnPremConfig.LIMIT_DISK_GB,
              line=dict(width=0), fillcolor="green", opacity=0.2, row=3, col=1)
fig.update_yaxes(title_text="IOps", row=4, col=1)
fig.add_vline(x=timestamps_dt[t_now], line_width=1, line_dash="dot", line_color="red", row=1, col=1)
fig.add_vline(x=timestamps_dt[t_now], line_width=1, line_dash="dot", line_color="red", row=2, col=1)
fig.add_vline(x=timestamps_dt[t_now], line_width=1, line_dash="dot", line_color="red", row=3, col=1)
fig.add_vline(x=timestamps_dt[t_now], line_width=1, line_dash="dot", line_color="red", row=4, col=1)

# fig.add_trace(go.Scatter(x=[timestamps_dt[t_now], timestamps_dt[t_now]], y=[dmin, dmax], mode='lines',
#                          line=dict(color='green', width=2, dash='dash')))

fig.add_trace(go.Scatter3d(name='Non-optimal (%d options)' % np.sum(np.logical_not(ind)),
                           x=xs_cost[np.logical_not(ind)],
                           y=ys_effort[np.logical_not(ind)],
                           z=zs_latency[np.logical_not(ind)],
                           customdata=customdata_nopt,
                           hovertemplate=hovertemplate, marker=dict(color='orange', opacity=0.2),
                           mode='markers'), row=1, col=2)
fig.add_trace(go.Scatter3d(name='Pareto Optimal (%d options)' % np.sum(ind),
                           x=xs_cost[ind],
                           y=ys_effort[ind],
                           z=zs_latency[ind],
                           customdata=customdata_opt,
                           hovertemplate=hovertemplate, marker=dict(color='red', opacity=1.0),
                           mode='markers'), row=1, col=2)
fig.update_scenes(xaxis={'title_text': 'Cost (USD)'},
                  yaxis={'title_text': 'Data Migration (GB)'},
                  zaxis={'title_text': 'Number of Inter-cloud Links'})

title = "API-aware Microservice Placement for Hybrid Multi-cloud | " \
        "[On-prem Limit] CPU: %d cores | Memory: %d GB | Storage: %d GB" % (OnPremConfig.LIMIT_CPU_CORE,
                                                                            OnPremConfig.LIMIT_MEMORY_GB,
                                                                            OnPremConfig.LIMIT_DISK_GB)
fig.update_layout(showlegend=False, title_text=title)
# fig.show()


import plotly.graph_objects as go # or plotly.express as px
import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_cytoscape as cyto

app = dash.Dash()
app.layout = html.Div([
    dcc.Graph(figure=fig),
])



app.run_server(debug=True, use_reloader=False)  # Turn off reloader if inside Jupyter
from plotly.subplots import make_subplots
import plotly.graph_objects as go
import json
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

        self.is_stateful = config['stateful']
        zeros = np.zeros_like(self.cpu)
        self.disk_usage = np.asarray(config['disk-usage']) if self.is_stateful else zeros  # GB
        self.write_iops = np.asarray(config['write-iops']) if self.is_stateful else zeros
        self.read_iops = np.asarray(config['read-iops']) if self.is_stateful else zeros
        self.iops = self.write_iops + self.read_iops
        self.write_throughput = np.asarray(config['write-throughput']) if self.is_stateful else zeros
        self.read_throughput = np.asarray(config['read-throughput']) if self.is_stateful else zeros
        self.throughput = self.write_throughput + self.read_throughput


with open('exploratory-analysis/data/20220617-metrics-istio.json') as f:
    data = json.load(f)
microservices = {k: Microservice(config=v) for k, v in data['components'].items()}
timestamps = data['timestamps']
step_size = data['step']
speedup_factor = 144
step_size *= speedup_factor
mids = list(microservices.keys())
t_now = 10 * 60 // 5


fig = make_subplots(
    rows=4, cols=2, column_widths=[0.4, 0.6],
    specs=[[{}, {"rowspan": 4}], [{}, {}], [{}, {}], [{}, {}]],
    subplot_titles=("CPU Usage", "Placement Plans", "Memory Usage", "", "Disk Usage", "", "IOps Usage"))
#{"rowspan": 4}

for mid, microservice in microservices.items():
    fig.add_trace(go.Scatter(name=mid, x=timestamps, y=microservice.cpu, stackgroup='cpu'), row=1, col=1)
    fig.add_trace(go.Scatter(name=mid, x=timestamps, y=microservice.memory, stackgroup='memory'), row=2, col=1)
    fig.add_trace(go.Scatter(name=mid, x=timestamps, y=microservice.disk_usage, stackgroup='disk'), row=3, col=1)
    fig.add_trace(go.Scatter(name=mid, x=timestamps, y=microservice.iops, stackgroup='iops'), row=4, col=1)

fig.update_layout(showlegend=False, title_text="Specs with Subplot Title")
fig.show()
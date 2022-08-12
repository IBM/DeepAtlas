from matplotlib import pyplot as plt
import numpy as np
import json

l = [1, 2, 3]
print(l.pop(0))
print(l)
exit()

with open('./phase1/2022-06-15-3API.json') as f:
    data = json.load(f)

xs = data['timestamps']
ys = []
key = 'write-throughput'
for k, v in data['components'].items():
    if key in v:
        ys.append(v[key])

plt.stackplot(xs, *ys)
plt.show()
exit()

import matplotlib.pyplot as plt
import itertools

print(2**29)
exit()
components = ['NGINX', 'ComposePostService', 'PostStorageService', 'PostStorageMongoDB', 'UserTimelineService', 'UserTimelineMongoDB']
ASSIGNMENT_ONPREM = 0
ASSIGNMENT_CLOUD = 1


M = [
    [0, 5, 0, 0, 5, 0],
    [1, 0, 5, 0, 5, 0],
    [0, 1, 0, 5, 0, 0],
    [0, 0, 1, 0, 0, 0],
    [1, 1, 0, 0, 0, 5],
    [0, 0, 0, 0, 1, 0],
]
S = [10, 50, 30, 20, 150, 30]

def objective_cost(plan):
    return sum((10 if plan[comp] == ASSIGNMENT_CLOUD else 0) for comp in components)


def objective_latency(plan):
    cost = 0
    for i in range(len(components)):
        for j in range(len(components)):
            c = M[i][j] * (1 + (plan[components[i]] != plan[components[j]]) * 10)
            cost += c
    return cost


print('Combinations: %d' % (2 ** len(components)))
xs_cost, xs_late = [], []
for i in range(len(components) + 1):
    for cloud_components in itertools.combinations(components, r=i):
        plan = {component: component in cloud_components for component in components}
        resrc = sum(S[j] for j in range(len(components)) if components[j] not in cloud_components)
        if resrc >= 100:
            continue
        xs_cost.append(objective_cost(plan))
        xs_late.append(objective_latency(plan))

plt.clf()
plt.scatter(xs_cost, xs_late)
plt.xlabel('Cost')
plt.ylabel('Latency')
plt.show()


# import dash
# import dash_cytoscape as cyto
# import dash_html_components as html
#
# app = dash.Dash(__name__)
# app.layout = html.Div([
#     cyto.Cytoscape(
#         id='cytoscape',
#         elements=[
#             {'data': {'id': 'one', 'label': 'Node 1'}, 'position': {'x': 50, 'y': 50}},
#             {'data': {'id': 'two', 'label': 'Node 2'}, 'position': {'x': 200, 'y': 200}},
#             {'data': {'source': 'one', 'target': 'two','label': 'Node 1 to 2'}}
#         ],
#         layout={'name': 'preset'}
#     )
# ])
#
# if __name__ == '__main__':
#     app.run_server(debug=True)
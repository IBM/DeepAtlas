import matplotlib.pyplot as plt
from core.recommender.nsga2api2d import NSGA2Recommender
from dash.dependencies import Input, Output, State
from plotly.subplots import make_subplots
from core.experiment import Experiment
from constants import READABLE_NAME
from dash import html
from dash import dcc
import plotly.graph_objs as go
import dash_cytoscape as cyto
import numpy as np
import dash

from lib_performance import PerformanceEstimator
from lib_cost import CostEstimator
plt.style.use('ggplot')


performance_est = PerformanceEstimator(experiment_id='202207302259_202207310221')
cost_est = CostEstimator()
exp = Experiment(path='experiments/story/cadvisor+istio.json', ignore=True)
exp.constraints = ['user-mongodb', 'post-storage-mongodb', 'media-mongodb']

# plans = NSGA2Recommender.run(exp)
# xs_ours, ys_ours = [], []
# for plan in plans:
#     print('cloud: %s' % str(plan.onprem_msvcs))
#     p = performance_est.estimate(plan)
#     c = cost_est.estimate(plan)
#     print(p, c)
#     xs_ours.append(p)
#     ys_ours.append(c)
# print('xs_ours = %s' % str(xs_ours))
# print('ys_ours = %s' % str(ys_ours))
# xs_ours = [1.6723698159462286, 1.830969094279653, 2.401210041119845, 4.706192371229753, 3.5605512778340778, 1.970362077409788, 2.9009269521696996, 2.9007667228355154, 2.910988878427718]
# ys_ours = [78.16647624949728, 74.83822471006638, 72.3290399779101, 60.927673571312795, 61.744221951869754, 74.77045147621256, 66.41772734610831, 67.140378873237, 61.87938154113074]
xs_ours = [1.6723698159462286, 1.830969094279653, 2.401210041119845, 2.910988878427718]
ys_ours = [78.16647624949728, 74.83822471006638, 72.3290399779101, 61.87938154113074]
print((95.56 - 78.16) / (95.56))
xs_baseline = [ 4.281641956483028, 3.9614878555429027, 3.1935262524507433, 4.923096147705003, 1.9766159995742096, 1.6723698159462286]
ys_baseline = [68.18779123626777, 69.5355832423239, 75.97800921496719, 67.35365299322194, 80.33763691006639, 95.56598219823911]
# xs_baseline = [1.6723698159462286, 3.6430726451593634, 1.6723698159462286, 1.830969094279653, 3.119641387866002, 1.6723698159462286, 1.6723698159462286, 1.6723698159462286, 2.401210041119845, 1.6723698159462286]
# ys_baseline = [78.33927624949726, 57.605306987735595, 80.36200261307545, 75.04942471006638, 65.86478973451997, 80.40040261307543, 78.20487624949727, 95.56598219823911, 72.5786399779101, 95.39318219823912]

plt.figure(figsize=(4.2, 4), dpi=150)
plt.scatter(ys_ours, xs_ours, label='Plans recommended by ours', color='tab:green')
# plt.scatter(ys_baseline, xs_baseline, label='Plans recommended by baseline', color='tab:red')
# legend = plt.legend(loc='upper right')
plt.ylim([1.5, 5.500])
plt.xlim([58, 97])
plt.ylabel('API Performance Impact')
plt.xlabel('Cost (USD)')
plt.tight_layout()
def export_legend(legend, filename="legend.png"):
    fig  = legend.figure
    fig.canvas.draw()
    bbox  = legend.get_window_extent().transformed(fig.dpi_scale_trans.inverted())
    fig.savefig(filename, dpi="figure", bbox_inches=bbox)

# export_legend(legend)
plt.savefig('./baseline-genetic.png')
plt.show()

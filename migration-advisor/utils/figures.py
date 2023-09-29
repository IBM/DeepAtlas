from utils.data import DataLoader
from utils.constants import TS_XS, TS_XTICKS, TS_LABELS
import plotly.graph_objects as go
import numpy as np


def generate_learning_traffic_figure(dataloader):
    app_learning_traffic = dataloader.get_learning_traffic()

    fig = go.Figure()
    fig['layout'].update(margin=dict(l=30, r=10, b=30, t=30))
    fig.add_trace(go.Scatter(x=TS_XS, y=app_learning_traffic['ALL'],
                             name='ALL', line=dict(color='royalblue', dash='dot')))
    fig.add_trace(go.Scatter(x=TS_XS, y=app_learning_traffic['/composePost'],
                             name='/composePost', line=dict(color='firebrick')))
    fig.add_trace(go.Scatter(x=TS_XS, y=app_learning_traffic['/uploadMedia'],
                             name='/uploadMedia', line=dict(color='forestgreen')))
    fig.add_trace(go.Scatter(x=TS_XS, y=app_learning_traffic['/readTimeline'],
                             name='/readTimeline', line=dict(color='salmon')))
    fig.update_traces(hovertemplate=None)
    fig.update_layout(xaxis_title='Timeline', yaxis_title='Requests per Second', height=250, hovermode="x",
                      xaxis=dict(tickmode='array', tickvals=TS_XTICKS, ticktext=TS_LABELS),
                      yaxis=dict(tickmode='array', tickvals=list(range(0, 600, 50)), ticktext=list(range(0, 600, 50))),
                      yaxis_range=[0, 550], xaxis_range=[0, 420])
    return fig


def generate_query_traffic_figure(dataloader, selected_composition, selected_multiplier, selected_load_shape):
    xs_ = []
    hour = 00
    minute = 00
    for i in range(61):
        xs_.append('%.2d:%.2d' % (hour, minute))
        minute += 24
        if minute >= 60:
            minute %= 60
            hour += 1
    fig = go.Figure()
    fig['layout'].update(margin=dict(l=30, r=10, b=30, t=30))
    fig.update_traces(hovertemplate=None)
    fig.update_layout(xaxis_title='Timeline', yaxis_title='Requests per Second',
                      xaxis=dict(tickmode='array', tickvals=list(range(0, len(xs_), 3)),
                                 ticktext=[xs_[i] for i in range(0, len(xs_), 3)]),
                      yaxis=dict(tickmode='array', tickvals=list(range(0, 600, 50)),
                                 ticktext=list(range(0, 600, 50))),
                      height=250,
                      hovermode="x",
                      yaxis_range=[0, 550],
                      xaxis_range=[0, 59]
                      )
    fig.add_shape(
        type="rect",
        xref="paper", yref="paper",
        x0=0., y0=0,
        x1=1.0, y1=1,
        fillcolor='red', opacity=0.3, line={'width': 0}
    )
    if selected_composition is None:
        return fig
    traffic = dataloader.get_query_traffic(selected_load_shape, selected_multiplier, selected_composition)

    fig.add_trace(go.Scatter(x=xs_, y=traffic['ALL'], name='ALL', line=dict(color='royalblue', dash='dot')))
    fig.add_trace(go.Scatter(x=xs_, y=traffic['/composePost'], name='/composePost', line=dict(color='firebrick')))
    fig.add_trace(go.Scatter(x=xs_, y=traffic['/uploadMedia'], name='/uploadMedia', line=dict(color='forestgreen')))
    fig.add_trace(go.Scatter(x=xs_, y=traffic['/readTimeline'], name='/readTimeline', line=dict(color='salmon')))
    return fig


def generate_timeseries_figure(metadata, selected_metric):
    y_empty = [0. for _ in range(480)]
    y0, y1, y2, y4 = y_empty, y_empty, y_empty, y_empty
    if selected_metric is not None and metadata is not None:
        y0 = metadata['utilization'][selected_metric][0] * DataLoader.UNIT if selected_metric in metadata['utilization'] else y_empty
        y1 = metadata['utilization'][selected_metric][1] * DataLoader.UNIT if selected_metric in metadata['utilization'] else y_empty
        y2 = metadata['utilization'][selected_metric][2] * DataLoader.UNIT if selected_metric in metadata['utilization'] else y_empty
        y4 = metadata['utilization'][selected_metric][4] * DataLoader.UNIT if selected_metric in metadata['utilization'] else y_empty

    fig = go.Figure(data=[
        go.Scatter(name='Actual Usage', x=TS_XS, y=y0, line=dict(color="magenta", width=2, dash="dot")),
        go.Scatter(name='BL: Resrc-aware DNN', x=TS_XS[-60:], y=y1, line=dict(color="orange"), visible='legendonly'),
        go.Scatter(name='BL: Monolithic Scaling', x=TS_XS[-60:], y=y2, line=dict(color="green"), visible='legendonly'),
        go.Scatter(name='DeepRest', x=TS_XS[-60:], y=y4, line=dict(color="black")),
    ])
    fig.add_shape(
        type="rect",
        xref="paper", yref="paper",
        x0=7. / 8, y0=0,
        x1=1.0, y1=1,
        fillcolor='red', opacity=0.3, line={'width': 0}
    )
    ys = list(y0) + list(y1) + list(y2) + list(y4)
    fig['layout'].update(margin=dict(l=30, r=10, b=30, t=30))
    unit = ''
    yrange = [0, 1]
    if selected_metric is not None and metadata is not None:
        unit = metadata['unit'][selected_metric]
        yrange = [0 if selected_metric == 'cpu' else max(0, min(ys) - (max(ys) - min(ys)) * 0.10), max(ys) + (max(ys) - min(ys)) * 0.10]
    fig.update_layout(height=180, yaxis_title=unit,
                      hovermode="x",
                      xaxis=dict(tickmode='array', tickvals=TS_XTICKS + [480], ticktext=TS_LABELS + ['TMR']),
                      xaxis_range=[0, 480],
                      yaxis_range=yrange)
    return fig


def generate_aggr_timeseries_figure(component2metrics, selected_metric, limits):
    xs_ = []
    hour = 00
    minute = 00
    for i in range(61):
        xs_.append('%.2d:%.2d' % (hour, minute))
        minute += 24
        if minute >= 60:
            minute %= 60
            hour += 1

    ys = np.asarray([0. for _ in range(60)])
    unit = ''
    if selected_metric is not None and component2metrics is not None:
        for component, metadata in component2metrics.items():
            if selected_metric in metadata['utilization']:
                ys = ys + metadata['utilization'][selected_metric][4]
            unit = metadata['unit'][selected_metric]
    ys = ys[-60:] * DataLoader.UNIT
    fig = go.Figure()
    fig['layout'].update(margin=dict(l=30, r=10, b=30, t=30))
    fig.update_traces(hovertemplate=None)
    ys_limit = [0. for _ in xs_]
    if selected_metric is not None and component2metrics is not None:
        factor = {'cpu': 1000, 'memory': 1000, 'usage': 1000}
        ys_limit = [limits[selected_metric] * factor[selected_metric] for _ in xs_]
    yss = list(ys) + ys_limit
    fig.update_layout(xaxis_title='Timeline', yaxis_title=unit,
                      xaxis=dict(tickmode='array', tickvals=list(range(0, len(xs_), 3)),
                                 ticktext=[xs_[i] for i in range(0, len(xs_), 3)]),
                      # height=250,
                      hovermode="x",
                      xaxis_range=[0, 59],
                      yaxis_range=[0 if selected_metric == 'cpu' else max(0, min(yss) - (max(yss) - min(yss)) * 0.10),
                                   max(yss) + (max(yss) - min(yss)) * 0.10]
                      )
    fig.add_shape(
        type="rect",
        xref="paper", yref="paper",
        x0=0., y0=0,
        x1=1.0, y1=1,
        fillcolor='red', opacity=0.3, line={'width': 0}
    )
    fig.add_trace(go.Scatter(x=xs_, y=ys, line=dict(color="black"), name='Usage'))
    fig.add_trace(go.Scatter(x=xs_, y=ys_limit, line=dict(color="blue"), name='Limit'))
    return fig

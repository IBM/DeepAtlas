from core.recommender.random import RandomRecommender
from core.recommender.nsga2 import NSGA2Recommender
from dash.dependencies import Input, Output, State
from plotly.subplots import make_subplots
from core.experiment import Experiment
from core.moo import is_pareto
from dash import html
from dash import dcc
import plotly.graph_objs as go
import dash_cytoscape as cyto
import numpy as np
import dash

app = dash.Dash(__name__, meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}])
app.title = "API-aware Microservice Placement for Hybrid Multi-cloud"

server = app.server
app.config.suppress_callback_exceptions = True
exp = Experiment(path='experiments/202207012101_202207012350/cadvisor+istio.json')
onprem_cpu_upper_limit = int(np.ceil(max(np.sum(np.asarray([microservice.cpu for microservice in exp.microservices.values()]), axis=0))))
onprem_memory_upper_limit = int(np.ceil(max(np.sum(np.asarray([microservice.memory for microservice in exp.microservices.values()]), axis=0))))
onprem_disk_upper_limit = int(np.ceil(max(np.sum(np.asarray([microservice.disk_usage for microservice in exp.microservices.values()]), axis=0))))
exp.config_onprem.LIMIT_CPU_CORE = onprem_cpu_upper_limit
exp.config_onprem.LIMIT_MEMORY_GB = onprem_memory_upper_limit
exp.config_onprem.LIMIT_DISK_GB = onprem_disk_upper_limit


def get_resource_figure(resource_type):
    layout = go.Layout(
        margin=go.layout.Margin(
            l=0,  # left margin
            r=0,  # right margin
            b=0,  # bottom margin
            t=0,  # top margin
        ),
        height=150
    )
    fig = go.Figure(layout=layout)
    for msvc, microservice in exp.microservices.items():
        if resource_type == 'cpu':
            fig.add_trace(go.Scatter(name=msvc, x=exp.timestamps_dt, y=microservice.cpu, stackgroup='cpu'))
        if resource_type == 'memory':
            fig.add_trace(go.Scatter(name=msvc, x=exp.timestamps_dt, y=microservice.memory, stackgroup='memory'))
        if resource_type == 'disk':
            fig.add_trace(go.Scatter(name=msvc, x=exp.timestamps_dt, y=microservice.disk_usage, stackgroup='disk_usage'))
        if resource_type == 'iops':
            fig.add_trace(go.Scatter(name=msvc, x=exp.timestamps_dt, y=microservice.iops, stackgroup='iops'))

    fig.update_yaxes(title_text={'cpu': 'cores', 'memory': 'GB', 'disk': 'GB', 'iops': 'IOps'}[resource_type])
    if resource_type == 'cpu':
        fig.add_shape(type="rect", x0=exp.timestamps_dt[exp.now], x1=exp.timestamps_dt[-1], y0=0,
                      y1=exp.config_onprem.LIMIT_CPU_CORE,
                      line=dict(width=0), fillcolor="green", opacity=0.2)
    if resource_type == 'memory':
        fig.add_shape(type="rect", x0=exp.timestamps_dt[exp.now], x1=exp.timestamps_dt[-1], y0=0,
                      y1=exp.config_onprem.LIMIT_MEMORY_GB,
                      line=dict(width=0), fillcolor="green", opacity=0.2)
    if resource_type == 'disk':
        fig.add_shape(type="rect", x0=exp.timestamps_dt[exp.now], x1=exp.timestamps_dt[-1], y0=0,
                      y1=exp.config_onprem.LIMIT_DISK_GB,
                      line=dict(width=0), fillcolor="green", opacity=0.2)
    fig.update_layout(showlegend=False)
    fig.add_vline(x=exp.timestamps_dt[exp.now], line_width=1, line_dash="dot", line_color="red")
    return fig


def generate_control_card():
    """

    :return: A Div containing controls for graphs.
    """
    return html.Div(
        id="control-card",
        children=[
            html.P("Budget (USD)"),
            dcc.Input(id='budget-input', type='number', min=0, step=1, placeholder="Unlimited"),
            html.Div(),

            html.Br(),
            html.P("On-prem Placement Constraints"),

            dcc.Dropdown(
                id="constraint-select",
                options=[{"label": i, "value": i} for i in exp.msvcs],
                multi=True,
            ),
            html.Br(),
            html.Hr(),
            html.Br(),
            html.P("On-prem CPU Limit (Cores)"),
            dcc.Slider(0, onprem_cpu_upper_limit, 1, value=2, id='cpu-slider'),
            dcc.Graph(figure=get_resource_figure('cpu'), id='cpu-graph'),

            html.Br(),
            html.P("On-prem Memory Limit (GB)"),
            dcc.Slider(0, onprem_memory_upper_limit, 1, value=onprem_memory_upper_limit, id='memory-slider'),
            dcc.Graph(figure=get_resource_figure('memory'), id='memory-graph'),

            html.Br(),
            html.P("On-prem Storage Limit (GB)"),
            dcc.Slider(0, onprem_disk_upper_limit, 1, value=onprem_disk_upper_limit, id='disk-slider'),
            dcc.Graph(figure=get_resource_figure('disk'), id='disk-graph'),

            html.Br(),
            html.P("On-prem IOps"),
            dcc.Graph(figure=get_resource_figure('iops')),

            html.Br(),
            html.Div(
                id="reset-btn-outer",
                style={'text-align': 'center'},
                children=html.Button(id="reset-btn", children="Recommend", n_clicks=0),
            ),
            html.Br(),
        ],
    )


@app.callback(Output('cpu-graph', 'figure'), Input('cpu-slider', 'value'))
def update_cpu_graph(value):
    exp.config_onprem.LIMIT_CPU_CORE = value
    return get_resource_figure('cpu')


@app.callback(Output('memory-graph', 'figure'), Input('memory-slider', 'value'))
def update_memory_graph(value):
    exp.config_onprem.LIMIT_MEMORY_GB = value
    return get_resource_figure('memory')


@app.callback(Output('disk-graph', 'figure'), Input('disk-slider', 'value'))
def update_disk_graph(value):
    exp.config_onprem.LIMIT_DISK_GB = value
    return get_resource_figure('disk')


app.layout = html.Div(
    id="app-container",
    children=[
        # Banner
        html.Div(
            id="banner",
            className="banner",
            children=[html.H5('API-aware Microservice Placement for Hybrid Cloud')],
        ),
        # Left column
        html.Div(
            id="left-column",
            className="three columns",
            children=[generate_control_card()]
        ),
        # Right column
        html.Div(
            id="right-column",
            className="nine columns",
            children=[
                # Patient Volume Heatmap
                dcc.Loading(
                    id="loading-2",
                    children=[html.Div([html.Div(id="loading-output-2")])],
                    type="circle", fullscreen=True
                ),
                html.Div(
                    id="patient_volume_card",
                    children=[
                        html.B("Recommended Plans"),
                        html.Hr(),
                        html.Div(id='tradeoff_graph_msg', children=['Use the control panel to select your preference and then click "RECOMMEND"']),
                        html.Div(id='tradeoff_graph_click', style={'display': 'None'}, children=['Click a node below to see the placement summary.']),
                        html.Div(id='tradeoff_graph_div', style={'display': 'None'}, children=dcc.Graph(id="tradeoff_graph")),
                        html.Div(id='no_solution_msg', style={'display': 'None'}, children=['No placement plan found. Please relax the constraints and try again.']),
                        html.Br(),
                    ],
                ),
                html.Div(
                    id="patient_volume_rcard",
                    children=[
                        dcc.Loading(
                            id="loading-1",
                            children=[html.Div([html.Div(id="loading-output-1")])],
                            type="circle",
                        ),
                        html.B("Placement Summary"),
                        html.Hr(),
                        html.Img(src=app.get_asset_url("legend.png"), style={'width': '100%', 'padding-top': '10px'}),
                        html.Div(id="placement-summary"),
                        html.Div(id="network"),
                        html.Br(),
                        html.Hr(),
                        html.Div(id="resrc-saving"),
                        dcc.Graph(id="resrc-summary"),
                    ],
                ),
            ],
        ),
    ],
)


@app.callback(
    [Output('network', 'children'),
     Output('resrc-summary', 'figure'), Output('loading-output-1', 'children'), Output('placement-summary', 'children'),
     Output('resrc-saving', 'children')],
    Input("tradeoff_graph", 'clickData'))
def display_click_data(clickData):
    offloaded_mids = clickData['points'][0]['customdata'][5] if clickData is not None else []
    cost = clickData['points'][0]['customdata'][6] if clickData is not None else 0.
    availability = clickData['points'][0]['customdata'][7] if clickData is not None else 0.
    performance = clickData['points'][0]['customdata'][8] if clickData is not None else 0.
    elements = []
    for mid in exp.microservices:
        element_class = ['onprem', 'cloud'][mid in offloaded_mids]
        if mid in ['media-memcached', 'url-shorten-memcached']:
            element_class = 'remove'
        elements.append({'data': {'id': mid, 'label': mid},
                         'classes': element_class})
    for mid_from, microservice in exp.microservices.items():
        for mid_to in microservice.outbound_to:
            elements.append({'data': {'source': mid_from, 'target': mid_to},
                             'classes': ['intra', 'inter'][
                                 (mid_from in offloaded_mids) != (mid_to in offloaded_mids)]})
    network = cyto.Cytoscape(
        elements=elements,
        layout={'name': 'breadthfirst', 'roots': '#nginx-thrift, #media-frontend'},
        style={'width': '100%', 'height': '260px'},
        stylesheet=[
            # Group selectors
            {
                'selector': 'node',
                'style': {
                    'content': 'data(label)'
                }
            },
            {
                'selector': '.onprem',
                'style': {
                    'background-color': 'green',
                    'line-color': 'green'
                }
            },
            {
                'selector': '.cloud',
                'style': {
                    'background-color': 'blue',
                    'line-color': 'blue',
                    'shape': 'star'
                }
            },
            {
                'selector': '.remove',
                'style': {
                    'background-color': 'orange',
                    'line-color': 'orange',
                }
            },
            {
                'selector': '.intra',
                'style': {
                    'line-color': 'lightgrey',
                }
            },
            {
                'selector': '.inter',
                'style': {
                    'line-color': 'red',
                }
            }
        ]
    )

    ####################################################################################################################
    fig = make_subplots(
        rows=4, cols=2, specs=[[{}, {}], [{}, {}], [{}, {}], [{}, {}]],
        subplot_titles=(
            "On-Prem", "Cloud"))

    microservices = exp.microservices
    timestamps_dt = exp.timestamps_dt
    t_now = exp.now

    cpu, memory, disk = None, None, None
    for mid, microservice in microservices.items():
        col = 2 if mid in offloaded_mids else 1
        fig.add_trace(go.Scatter(name=mid, x=timestamps_dt[t_now:], y=microservice.cpu[t_now:], stackgroup='cpu'), row=1, col=col)
        fig.add_trace(go.Scatter(name=mid, x=timestamps_dt[t_now:], y=microservice.memory[t_now:], stackgroup='memory'), row=2, col=col)
        fig.add_trace(go.Scatter(name=mid, x=timestamps_dt[t_now:], y=microservice.disk_usage[t_now:], stackgroup='disk'), row=3, col=col)
        fig.add_trace(go.Scatter(name=mid, x=timestamps_dt[t_now:], y=microservice.iops[t_now:], stackgroup='iops'), row=4, col=col)
        if col == 1:
            if cpu is None:
                cpu = microservice.cpu[t_now:]
                memory = microservice.memory[t_now:]
                disk = microservice.disk_usage[t_now:]
            else:
                cpu = cpu + microservice.cpu[t_now:]
                memory = memory + microservice.memory[t_now:]
                disk = disk + microservice.disk_usage[t_now:]

    if clickData is None:
        placement_summary = ['Default Placement: All components are assigned to the on-prem cluster.']
        saving_summary = []
    else:
        placement_summary = ['Cost: USD %.2f | Data Migration: %.2f%% | Inter-cloud Links: %d' % (cost,
                                                                                                  availability,
                                                                                                  performance)]
        saving_summary = [
            html.Div('Based on this placement plan, you can further save...')
        ]
        cpu_needed = int(np.ceil(np.max(cpu)))
        memory_needed = int(np.ceil(np.max(memory)))
        disk_needed = int(np.ceil(np.max(disk)))
        if exp.config_onprem.LIMIT_CPU_CORE - cpu_needed > 0:
            delta = exp.config_onprem.LIMIT_CPU_CORE - cpu_needed
            saving_summary += [html.Div('CPU: %d core%s' % (delta, 's' if delta > 1 else ''))]
        if exp.config_onprem.LIMIT_MEMORY_GB - memory_needed > 0:
            saving_summary += [html.Div('Memory: %d GB' % (exp.config_onprem.LIMIT_MEMORY_GB - memory_needed))]
        if exp.config_onprem.LIMIT_DISK_GB - disk_needed > 0:
            saving_summary += [html.Div('Disk: %d GB' % (exp.config_onprem.LIMIT_DISK_GB - disk_needed))]
    fig.update_yaxes(title_text="CPU (Cores)", row=1, col=1)
    fig.update_yaxes(title_text="CPU (Cores)", row=1, col=2)
    fig.add_shape(type="rect", x0=timestamps_dt[t_now], x1=timestamps_dt[-1], y0=0, y1=exp.config_onprem.LIMIT_CPU_CORE,
                  line=dict(width=0), fillcolor="green", opacity=0.2, row=1, col=1)
    fig.update_yaxes(title_text="Memory (GB)", row=2, col=1)
    fig.update_yaxes(title_text="Memory (GB)", row=2, col=2)
    fig.add_shape(type="rect", x0=timestamps_dt[t_now], x1=timestamps_dt[-1], y0=0,
                  y1=exp.config_onprem.LIMIT_MEMORY_GB,
                  line=dict(width=0), fillcolor="green", opacity=0.2, row=2, col=1)
    fig.update_yaxes(title_text="Storage (GB)", row=3, col=1)
    fig.update_yaxes(title_text="Storage (GB)", row=3, col=2)
    fig.add_shape(type="rect", x0=timestamps_dt[t_now], x1=timestamps_dt[-1], y0=0, y1=exp.config_onprem.LIMIT_DISK_GB,
                  line=dict(width=0), fillcolor="green", opacity=0.2, row=3, col=1)
    fig.update_yaxes(title_text="IOps", row=4, col=1)
    fig.update_yaxes(title_text="IOps", row=4, col=2)
    fig.update_layout(showlegend=False, height=600,
                      margin=go.layout.Margin(
                          l=0,  # left margin
                          r=0,  # right margin
                          b=0,  # bottom margin
                          t=40,  # top margin
                      ),
                      )
    return network, fig, [], placement_summary, saving_summary


@app.callback(
    [Output("tradeoff_graph", "figure"), Output('loading-output-2', 'children'),
     Output("tradeoff_graph_div", "style"), Output("tradeoff_graph_msg", "style"), Output("no_solution_msg", "style"),
     Output('tradeoff_graph_click', 'style')],
    Input("reset-btn", "n_clicks"),
    [State('budget-input', 'value'), State('constraint-select', 'value'),
     State('cpu-slider', 'value'), State('memory-slider', 'value'), State('disk-slider', 'value')]
)
def update_table(reset_click, budget, constraint, cpu, memory, disk):
    print('### %d' % reset_click)
    if reset_click == 0:
        return go.Figure(), [], {'display': 'None'}, {'display': 'Block'}, {'display': 'None'}, {'display': 'None'}
    exp.config_cloud.BUDGET = budget if budget is not None else 100000
    exp.constraints = constraint if constraint is not None else []
    exp.config_onprem.LIMIT_CPU_CORE = cpu
    exp.config_onprem.LIMIT_MEMORY_GB = memory
    exp.config_onprem.LIMIT_DISK_GB = disk

    plans = NSGA2Recommender.run(exp)
    if len(plans) == 0:
        return go.Figure(), [], {'display': 'None'}, {'display': 'None'}, {'display': 'Block'}, {'display': 'None'}

    xs_cost = []
    ys_availability = []
    zs_performance = []
    customdata = []
    for plan in plans:
        onprem_msvcs = plan.onprem_msvcs
        cloud_msvcs = plan.cloud_msvcs
        c = plan.cost_model()
        a = plan.availability_model()
        p = plan.performance_model()
        xs_cost.append(c)
        ys_availability.append(a)
        zs_performance.append(p)

        c1 = '<br>'.join(['   %d) %s%s' % (
            num + 1, msvc,
            '  (Stateful: %.4fGB)' % (max(exp.microservices[msvc].disk_usage[:exp.now])) if exp.microservices[
                msvc].is_stateful else '') for num, msvc in enumerate(onprem_msvcs)])
        c2 = '<br>'.join(['   %d) %s%s' % (
            num + 1, msvc,
            '  (Stateful: %.4fGB)' % (max(exp.microservices[msvc].disk_usage[:exp.now])) if exp.microservices[
                msvc].is_stateful else '') for num, msvc in enumerate(cloud_msvcs)])
        customdata.append((c1, c2, len(onprem_msvcs), len(cloud_msvcs),
                           (sum(exp.microservices[msvc].is_stateful for msvc in cloud_msvcs)), cloud_msvcs,
                           c, a, p))

    xs_cost = np.asarray(xs_cost)
    ys_availability = np.asarray(ys_availability)
    zs_performance = np.asarray(zs_performance)

    hovertemplate = '<b>Cost: USD %{x:.2f}</b><br>' \
                    '<b>Data Migration: %{y:.4f}%</b><br>' \
                    '<b>Intercloud Links: %{z}</b><br><br><b>===== Placement Plan =====</b><br>' \
                    'Keep %{customdata[2]:d} components on-prem:<br>' \
                    '%{customdata[0]}' \
                    '<br>Offload %{customdata[3]:d} components (%{customdata[4]:d} stateful) to the cloud:<b></b><br>' \
                    '%{customdata[1]}'

    layout = go.Layout(
        margin=go.layout.Margin(
            l=0,  # left margin
            r=0,  # right margin
            b=0,  # bottom margin
            t=0,  # top margin
        ),
        height=450
    )
    fig = go.Figure(layout=layout)
    fig.add_trace(go.Scatter3d(name='',
                               x=xs_cost,
                               y=ys_availability,
                               z=zs_performance,
                               customdata=customdata,
                               hovertemplate=hovertemplate, marker=dict(color='red', opacity=1.0),
                               mode='markers'))
    fig.update_scenes(xaxis={'title_text': 'Cost (USD)'},
                      yaxis={'title_text': 'Data Migration (%)'},
                      zaxis={'title_text': 'Number of Inter-cloud Links'},
                      aspectmode='cube')
    fig.update_layout(showlegend=False)

    return fig, [], {'display': 'Block'}, {'display': 'None'}, {'display': 'None'}, {'display': 'Block'}


# Run the server
if __name__ == "__main__":
    app.run_server(port=2023, host='0.0.0.0')
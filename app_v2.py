from core.recommender.nsga2api import NSGA2Recommender
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
from lib_availability import AvailabilityEstimator
from lib_cost import CostEstimator

# API button

performance_est = PerformanceEstimator(experiment_id='202207302259_202207310221')
availability_est = AvailabilityEstimator()
cost_est = CostEstimator()
# exp = Experiment(path='experiments/202207012101_202207012350/cadvisor+istio.json')
exp = Experiment(path='experiments/story/cadvisor+istio.json')

app = dash.Dash(__name__, meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}])
app.title = "API-aware Microservice Placement for Cloud Migration"

server = app.server
app.config.suppress_callback_exceptions = True
onprem_cpu_upper_limit = int(
    np.ceil(max(np.sum(np.asarray([microservice.cpu for microservice in exp.microservices.values()]), axis=0))))
onprem_memory_upper_limit = int(
    np.ceil(max(np.sum(np.asarray([microservice.memory for microservice in exp.microservices.values()]), axis=0))))
onprem_disk_upper_limit = int(
    np.ceil(max(np.sum(np.asarray([microservice.disk_usage for microservice in exp.microservices.values()]), axis=0))))
exp.config_onprem.LIMIT_CPU_CORE = onprem_cpu_upper_limit
exp.config_onprem.LIMIT_MEMORY_GB = onprem_memory_upper_limit
exp.config_onprem.LIMIT_DISK_GB = onprem_disk_upper_limit


def get_resource_figure(resource_type):
    layout = go.Layout(margin=go.layout.Margin(l=0, r=0, b=0, t=0), height=150, paper_bgcolor='rgba(0,0,0,0)', )
    fig = go.Figure(layout=layout)
    for msvc, microservice in exp.microservices.items():
        if resource_type == 'cpu':
            fig.add_trace(go.Scatter(name=msvc, x=exp.timestamps_dt, y=microservice.cpu, stackgroup='cpu'))
        if resource_type == 'memory':
            fig.add_trace(go.Scatter(name=msvc, x=exp.timestamps_dt, y=microservice.memory, stackgroup='memory'))
        if resource_type == 'disk':
            fig.add_trace(
                go.Scatter(name=msvc, x=exp.timestamps_dt, y=microservice.disk_usage, stackgroup='disk_usage'))

    fig.update_yaxes(title_text={'cpu': 'cores', 'memory': 'GB', 'disk': 'GB'}[resource_type])
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
    return html.Div(
        id="control-card",
        children=[
            html.P("Budget (USD)"),
            dcc.Input(id='budget-input', type='number', min=0, step=1, placeholder="Unlimited"),
            html.Div(),

            html.Br(),
            html.P("Critical APIs"),
            dcc.Dropdown(id="api-select", options=[{"label": v, "value": k} for k, v in READABLE_NAME.items()],
                         multi=True, disabled=False),

            html.Br(),
            html.P("On-prem Placement Constraints"),
            dcc.Dropdown(id="constraint-select", options=[{"label": i, "value": i} for i in exp.msvcs],
                         value=['nginx-thrift', 'media-frontend'], multi=True, ),

            html.Br(),
            html.P("On-prem CPU Limit (Cores)"),
            dcc.Slider(0, onprem_cpu_upper_limit, 1, value=4, id='cpu-slider'),
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
            html.Div(id="reset-btn-outer", style={'text-align': 'center'},
                     children=html.Button(id="reset-btn", children="Recommend", n_clicks=0)),
            html.Br(),

            html.Hr(),
            html.Div(children=[
                'Ka-Ho Chow (', html.A('khchow@gatech.edu', href='mailto:khchow@gatech.edu'), ')', html.Br(),
                'Mentor: Umesh Deshpande', html.Br(),
                'Manager: Veera Deenadayalan', html.Br()
            ], style={'margin-bottom': '2rem', 'margin-top': '2rem'})
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
        html.Div(id="banner", className="banner", children=[html.H5(app.title)]),
        # Left column
        html.Div(id="left-column", className="three columns", children=[generate_control_card()]),
        # Right column
        html.Div(id="right-column", className="nine columns", children=[
            dcc.Loading(id="loading-2", children=[html.Div([html.Div(id="loading-output-2")])], type="circle",
                        fullscreen=True),
            html.Div(id="patient_volume_card", children=[html.B("Recommended Plans"), html.Hr(),
                                                         html.Div(id='tradeoff_graph_msg', children=[
                                                             'Use the control panel to select your preference and then click "RECOMMEND"']),
                                                         html.Div(id='tradeoff_graph_click', style={'display': 'None'},
                                                                  children=[
                                                                      'Click a node below to see the migration summary.']),
                                                         html.Div(id='tradeoff_graph_div', style={'display': 'None'},
                                                                  children=dcc.Graph(id="tradeoff_graph")),
                                                         html.Div(id='tradeoff_list_div'),
                                                         html.Div(id='no_solution_msg', style={'display': 'None'},
                                                                  children=['No placement plan found. Please relax the constraints and try again.']),
                                                         html.Br()]),
            html.Div(id="patient_volume_rcard", children=[
                html.B("Migration Summary"),
                html.B(id='selected-option'),
                html.Hr(),
                html.Img(src=app.get_asset_url("legend.png"), style={'width': '100%', 'padding-top': '10px'}),
                dcc.Loading(id="loading-1", children=[html.Div([html.Div(id="loading-output-1")])], type="circle"),
                html.Div(id="network"),
                html.Hr(),
                html.Div(id="placement-summary", style={'margin-top': '6px'}),
                html.Div(id='api-summary', style={'margin-top': '6px'}),
                html.Br(),
            ])]),
    ],
)


@app.callback(
    [Output('network', 'children'), Output('loading-output-1', 'children'), Output('placement-summary', 'children'),
     Output('api-summary', 'children'), Output('selected-option', 'children')],
    Input("tradeoff_graph", 'clickData'))
def display_click_data(clickData):
    offloaded_mids = clickData['points'][0]['customdata'][5] if clickData is not None else set()
    cost = clickData['points'][0]['customdata'][6] if clickData is not None else 0.
    _performance = clickData['points'][0]['customdata'][8] if clickData is not None else 0.
    plan_id = clickData['points'][0]['customdata'][9] if clickData is not None else -1
    performance = performance_est.estimate(plan=set(offloaded_mids), detailed=True)
    availability = availability_est.estimate(plan=set(offloaded_mids), detailed=True)

    elements = []
    for mid in exp.microservices:
        if mid == 'istio-ingressgateway':
            continue
        element_class = ['onprem', 'cloud'][mid in offloaded_mids]
        if mid in ['media-memcached', 'url-shorten-memcached']:
            element_class = 'remove'
        elements.append({'data': {'id': mid, 'label': mid},
                         'classes': element_class})
    for mid_from, microservice in exp.microservices.items():
        for mid_to in microservice.outbound_to:
            if 'istio-ingressgateway' in (mid_from, mid_to):
                continue
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
    fig = make_subplots(rows=3, cols=2, specs=[[{}, {}], [{}, {}], [{}, {}]], subplot_titles=("On-Prem", "Cloud"))

    microservices = exp.microservices
    timestamps_dt = exp.timestamps_dt
    t_now = exp.now

    cpu, memory, disk = None, None, None
    for mid, microservice in microservices.items():
        col = 2 if mid in offloaded_mids else 1
        fig.add_trace(go.Scatter(name=mid, x=timestamps_dt[t_now:], y=microservice.cpu[t_now:], stackgroup='cpu'),
                      row=1, col=col)
        fig.add_trace(go.Scatter(name=mid, x=timestamps_dt[t_now:], y=microservice.memory[t_now:], stackgroup='memory'),
                      row=2, col=col)
        fig.add_trace(
            go.Scatter(name=mid, x=timestamps_dt[t_now:], y=microservice.disk_usage[t_now:], stackgroup='disk'), row=3,
            col=col)
        if col == 1:
            if cpu is None:
                cpu = microservice.cpu[t_now:]
                memory = microservice.memory[t_now:]
                disk = microservice.disk_usage[t_now:]
            else:
                cpu = cpu + microservice.cpu[t_now:]
                memory = memory + microservice.memory[t_now:]
                disk = disk + microservice.disk_usage[t_now:]

    api_summary = []
    if clickData is None:
        placement_summary = ['Default Placement: All components are assigned to the on-prem cluster.']

        for api, apir in READABLE_NAME.items():
            png_name = 'api-pos.png'
            api_summary.append(html.Div(className='api-div', children=[
                html.Img(src=app.get_asset_url(png_name), style={'height': '16px', 'padding-right': '4px'}),
                '%s: %.1fms' % (apir, np.mean([tup[0] for tup in performance[api]]))
            ]))
    else:
        placement_summary = ['Cost: USD %.1f | API Disruption: %d | Performance Impact Factor: %.1fx' % (
        cost, len(availability), _performance)]

        for api, apir in READABLE_NAME.items():
            png_name = 'api-pos.png'
            if api in availability:
                png_name = 'api-neg.png'
            elif np.mean([tup[0] for tup in performance[api]]) != np.mean([tup[1] for tup in performance[api]]):
                png_name = 'api-mid.png'
            api_summary.append(html.Div(className='api-div', children=[
                html.Img(src=app.get_asset_url(png_name), style={'height': '16px', 'padding-right': '4px'}),
                '%s: %.1fms -> %.1fms (%.1fx)' % (
                    apir,
                    np.mean([tup[0] for tup in performance[api]]),
                    np.mean([tup[1] for tup in performance[api]]),
                    np.mean([tup[1] for tup in performance[api]]) / np.mean([tup[0] for tup in performance[api]])
                )
            ]))
    selected_option = '' if plan_id < 0 else ' (Option #%d)' % (plan_id + 1)
    return network, [], placement_summary, api_summary, selected_option


@app.callback(
    [Output("tradeoff_graph", "figure"), Output('loading-output-2', 'children'),
     Output("tradeoff_graph_div", "style"), Output("tradeoff_graph_msg", "style"), Output("no_solution_msg", "style"),
     Output('tradeoff_graph_click', 'style'), Output('tradeoff_list_div', 'children')],
    Input("reset-btn", "n_clicks"),
    [State('budget-input', 'value'), State('constraint-select', 'value'), State('api-select', 'value'),
     State('cpu-slider', 'value'), State('memory-slider', 'value'), State('disk-slider', 'value')]
)
def update_table(reset_click, budget, constraint, critical_apis, cpu, memory, disk):
    if reset_click == 0:
        return go.Figure(), [], {'display': 'None'}, {'display': 'Block'}, {'display': 'None'}, {'display': 'None'}, []
    if critical_apis is None:
        critical_apis = ()
    exp.config_cloud.BUDGET = budget if budget is not None else 100000
    exp.constraints = constraint if constraint is not None else []
    exp.config_onprem.LIMIT_CPU_CORE = cpu
    exp.config_onprem.LIMIT_MEMORY_GB = memory
    exp.config_onprem.LIMIT_DISK_GB = disk

    plans = NSGA2Recommender.run(exp)
    if len(plans) == 0:
        return go.Figure(), [], {'display': 'None'}, {'display': 'None'}, {'display': 'Block'}, {'display': 'None'}

    tradeoff_list = []
    xs_cost = []
    ys_availability = []
    zs_performance = []
    customdata = []
    for plan_id, plan in enumerate(plans):
        onprem_msvcs = plan.onprem_msvcs
        cloud_msvcs = plan.cloud_msvcs
        c = cost_est.estimate(plan, critical_apis=critical_apis)
        a = availability_est.estimate(plan, critical_apis=critical_apis)
        p = performance_est.estimate(plan, critical_apis=critical_apis)
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
                           c, a, p, plan_id))

    for plan_id in range(len(xs_cost)):
        c = xs_cost[plan_id]
        a = ys_availability[plan_id]
        p = zs_performance[plan_id]

        children = [html.Div(html.B('Option #%d' % (plan_id + 1)), style={'display': 'inline-block'})]
        if np.round(c, 1) == min(np.round(xs_cost, 1)):
            children.append(html.Div(className='cost-opt', children='Cheapest', style={'display': 'inline-block', 'float': 'right'}))
        if a == min(ys_availability):
            children.append(html.Div(className='availability-opt', children='Least Disruptive', style={'display': 'inline-block', 'float': 'right'}))
        if np.round(p, 1) == min(np.round(zs_performance, 1)):
            children.append(html.Div(className='perf-opt', children='Best Performance', style={'display': 'inline-block', 'float': 'right'}))
        children += [html.Br(), 'Cost: USD %.1f' % c]
        if len(critical_apis) == 0:
            children += [html.Br(), 'API Disruption: %d' % a]
        else:
            api_offline = availability_est.estimate(plans[plan_id], critical_apis=critical_apis, detailed=True)
            children += [html.Br(),
                         'Critical API Disruption: %d' % len(set(api_offline).intersection(critical_apis)), html.Br(),
                         'Non-critical API Disruption: %d' % len(set(api_offline).difference(critical_apis)), ]
        children += [html.Br(), 'Performance Impact Factor: %.1fx' % p]
        tradeoff_list.append(html.Div(className='tradeoff_list_item', children=children))

    xs_cost = np.asarray(xs_cost)
    ys_availability = np.asarray(ys_availability)
    zs_performance = np.asarray(zs_performance)

    hovertemplate = '<b>[CLICK TO SEE THE DETAILS]</b></br></br>' \
                    '<b>Cost: USD %{x:.1f}</b><br>' \
                    '<b>API Disruption Index: %{y:.0f}</b><br>' \
                    '<b>Performance Impact Factor: %{z:.1f}x</b><br><br><b>===== Migration Plan =====</b><br>' \
                    'Keep %{customdata[2]:d} components on-prem:<br>' \
                    '%{customdata[0]}' \
                    '<br>Offload %{customdata[3]:d} components (%{customdata[4]:d} stateful) to the cloud:<b></b><br>' \
                    '%{customdata[1]}'

    layout = go.Layout(margin=go.layout.Margin(l=0, r=0, b=0, t=0), height=450)
    fig = go.Figure(layout=layout)
    fig.add_trace(go.Scatter3d(name='',
                               x=xs_cost,
                               y=ys_availability,
                               z=zs_performance,
                               text=['#%d' % (ii + 1) for ii in range(len(xs_cost))],
                               customdata=customdata,
                               hovertemplate=hovertemplate, marker=dict(color='red', opacity=1.0),
                               mode='markers+text'))
    fig.update_scenes(xaxis={'title_text': 'Cost (USD)'},
                      yaxis={'title_text': 'API Disruption Index'},
                      zaxis={'title_text': 'Performance Impact Factor'},
                      aspectmode='cube')
    fig.update_layout(showlegend=False)

    return fig, [], {'display': 'Block'}, {'display': 'None'}, {'display': 'None'}, {'display': 'Block'}, tradeoff_list


# Run the server
if __name__ == "__main__":
    app.run_server(port=2024, host='0.0.0.0')

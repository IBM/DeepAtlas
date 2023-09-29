from utils.figures import generate_learning_traffic_figure, generate_query_traffic_figure
from utils.figures import generate_timeseries_figure, generate_aggr_timeseries_figure
from utils.constants import READABLE_NAME
from utils.data import DataLoader
from core.nsga2api import NSGA2Recommender
from core.experiment import Experiment, format_experiment
from dash.dependencies import Input, Output, State
from dash import html
from dash import dcc
from plotly.subplots import make_subplots
import plotly.graph_objs as go
import dash_cytoscape as cyto
import numpy as np
import dash
import copy


dataloader = DataLoader(path='./assets/cases.pkl')
components = ['nginx-thrift', 'compose-post-service', 'post-storage-service', 'post-storage-mongodb',
              'user-timeline-service', 'user-timeline-mongodb', 'media-frontend', 'media-mongodb']
exp = Experiment(path='experiments/cadvisor+istio.json', experiment_id='demo')
app = dash.Dash(__name__, meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
                suppress_callback_exceptions=True)
app.title = "Atlas: Hybrid Cloud Migration Advisor for Interactive Microservices"


def generate_simulation_card():
    return html.Div(
        id="simulation-card",
        children=[
            html.Div(html.B("Simulation Panel"), style={'text-align': 'center'}),
            html.Hr(style={'margin-top': 24, 'margin-bottom': 24}),

            html.P("Traffic Shape"),
            dcc.Dropdown(id="shape-dropdown", multi=False, value='waves', disabled=False, options=[
                {'label': 'Two peak hours per day', 'value': 'waves'},
                {'label': 'Roughly stable', 'value': 'steps'}
            ]),
            html.Div('Description: Select the workload shape to be served', className='simulation-desc'),
            html.P("User Scale"),
            dcc.Dropdown(id="scale-dropdown", multi=False, value=3, disabled=False),
            html.Div('Description: Select the scale of users to be served', className='simulation-desc'),
            html.P("API Composition"),
            dcc.Dropdown(id="composition-dropdown", multi=False, value='70_10_20', disabled=False),
            html.Div('Description: Select the expected composition of API requests', className='simulation-desc'),

            html.Div(style={'text-align': 'center'},
                     children=html.Button(id="simu-estimate-btn", children="Estimate", n_clicks=0)),

            html.Hr(style={'margin-top': 24, 'margin-bottom': 24}),
            html.P("On-prem CPU Limit (Cores)"),
            dcc.Slider(0, 8, 1, value=2, id='cpu-slider'),
            html.Div(style={'margin-bottom': 12}),

            html.P("On-prem Memory Limit (GB)"),
            dcc.Slider(0, 16, 2, value=16, id='memory-slider'),
            html.Div(style={'margin-bottom': 12}),

            html.P("On-prem Storage Limit (GB)"),
            dcc.Slider(0, 32, 4, value=20, id='storage-slider'),
            html.Div(style={'margin-bottom': 12}),
        ],
    )


def generate_resource_card():
    return [html.Div(children=[
        html.Div(id='resrc-dashboard-top', children=[
            html.Div(style={'width': '59.5%', 'float': 'left'},
                     children=[
                         html.B("API Traffic - Application Learning"),
                         html.Hr(),
                         dcc.Graph(id='learning-traffic-graph',
                                   figure=generate_learning_traffic_figure(dataloader)),
                     ]),
            html.Div(style={'width': '39.5%', 'float': 'left', 'margin-left': '1%'},
                     children=[
                         html.B("API Traffic - Query (From the Simulation Setting)"),
                         html.Hr(),
                         dcc.Graph(id='query-traffic-graph'),
                     ]),
            html.Div(style={'color': 'white'}, children='.')
        ]),
        ################################################################################################################
        html.Hr(style={'margin-bottom': 12}),
        ################################################################################################################
        html.Div(id='resrc-dashboard-bottom', style={'margin-bottom': '12px'}, children=[
            html.Div(id="metric-selector", style={'text-align': 'left'}, children=[
                html.Div(style={'display': 'inline-block', 'float': 'left', 'font-weight': 'bold'},
                         children='Resource: '),
                html.Div(style={'display': 'inline-block'},
                         children=dcc.RadioItems(id='resrc-radio', labelStyle={'display': 'inline-block'}, options=[
                             {'label': 'CPU', 'value': 'cpu'},
                             {'label': 'Memory', 'value': 'memory'},
                             {'label': 'Storage', 'value': 'usage'}], value='cpu'))]),
            html.Div(id="resrc-fine", style={'width': '66.5%', 'float': 'left'}),
            html.Div(id="resrc-aggr", style={'width': '31.5%', 'float': 'left',
                                             'margin-bottom': '12px', 'margin-left': '0%', 'padding-left': '12px',
                                             'text-align': 'center', 'border-left': '1px solid #EAEAEA'},
                     children=[html.B("On-prem Usage"), dcc.Graph(style={'height': '300px'}, id='resrc-aggr-graph')]),
        ]),
    ])]


def generate_migration_card():
    return [html.Div(children=[
        html.Div(id='migration-dashboard-top', children=[
            html.Div(style={'float': 'left', 'width': '17%'}, children=[
                html.P(html.B("Budget (USD)")),
                dcc.Input(id='budget-input', type='number', min=0, step=1, placeholder="Unlimited", style={'width': '100%'}),
            ]),
            html.Div(style={'float': 'left', 'width': '30%', 'margin-left': '1%'}, children=[
                html.P(html.B("Critical APIs")),
                dcc.Dropdown(id="api-select", multi=True, disabled=False, options=[{"label": v, "value": k} for k, v in READABLE_NAME.items()]),
            ]),
            html.Div(style={'float': 'left', 'width': '30%', 'margin-left': '1%'}, children=[
                html.P(html.B("On-prem Placement Constraints")),
                dcc.Dropdown(id="constraint-select", multi=True, value=['user-mongodb', 'post-storage-mongodb'],
                             options=[{"label": i, "value": i} for i in exp.msvcs]),
            ]),
            html.Div(style={'float': 'left', 'width': '20%', 'margin-left': '1%', 'padding-top': '32px'}, children=[
                html.Div(style={'text-align': 'center'},
                         children=html.Button(id="recmd-btn", children="Recommend", n_clicks=0)),
            ]),
            html.Div(style={'color': 'white'}, children='.')
        ]),
        ################################################################################################################
        html.Div(id='migration-dashboard-bottom', style={'margin-bottom': '12px', 'padding-bottom': '12px'}, children=[
            html.Div(id="patient_volume_card", children=[
                dcc.Loading(
                    id="migration-loading",
                    type="default",
                    children=html.Div(id="loading-output")
                ),
                html.B("Recommended Plans"), html.Hr(),
                html.Div(id='tradeoff_graph_msg', children=['Use the control panel to select your preference and then click "RECOMMEND"']),
                html.Div(id='tradeoff_graph_click', style={'display': 'None'}, children=['Click a node below to see the migration summary.']),
                html.Div(id='tradeoff_graph_div', style={'display': 'None'}, children=dcc.Graph(id="tradeoff_graph")),
                html.Div(id='tradeoff_list_div'),
                html.Div(id='no_solution_msg', style={'display': 'None'}, children=['No placement plan found. Please relax the constraints and try again.']),
                html.Br()
            ]),
            html.Div(id="patient_volume_rcard", children=[
                html.B("Migration Summary"),
                html.B(id='selected-option'),
                html.Hr(),
                html.Img(src=app.get_asset_url("legend.png"), style={'width': '100%', 'padding-top': '10px'}),
                html.Div(id="network"),
                html.Hr(),
                html.Div(id="placement-summary", style={'margin-top': '6px'}),
                html.Div(id='api-summary', style={'margin-top': '6px'}),
                html.Br(),
            ])
        ]),
    ])]


@app.callback(
    [Output("tradeoff_graph", "figure"),
     Output("tradeoff_graph_div", "style"), Output("tradeoff_graph_msg", "style"), Output("no_solution_msg", "style"),
     Output('tradeoff_graph_click', 'style'), Output('tradeoff_list_div', 'children'), Output('loading-output', 'children')],
    Input("recmd-btn", "n_clicks"),
    [State('budget-input', 'value'), State('constraint-select', 'value'), State('api-select', 'value'),
     State('cpu-slider', 'value'), State('memory-slider', 'value'), State('storage-slider', 'value')]
)
def update_table(reset_click, budget, constraint, critical_apis, cpu, memory, disk):
    if reset_click == 0:
        return go.Figure(), {'display': 'None'}, {'display': 'Block'}, {'display': 'None'}, {'display': 'None'}, [], []
    if critical_apis is None:
        critical_apis = ()
    exp.config_cloud.BUDGET = budget if budget is not None else 100000
    exp.constraints = constraint if constraint is not None else []
    exp.config_onprem.LIMIT_CPU_CORE = cpu
    exp.config_onprem.LIMIT_MEMORY_GB = memory
    exp.config_onprem.LIMIT_DISK_GB = disk

    plans = NSGA2Recommender.run(exp, critical_apis=critical_apis)
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
        c = exp.cost_est.estimate(plan, critical_apis=critical_apis)
        a = exp.availability_est.estimate(plan, critical_apis=critical_apis)
        p = exp.performance_est.estimate(plan, critical_apis=critical_apis)
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
            children += [html.Br(), 'Performance Impact Factor: %.1fx' % p]
        else:
            api_offline = exp.availability_est.estimate(plans[plan_id], critical_apis=critical_apis, detailed=True)
            children += [html.Br(),
                         'Critical API Disruption: %d' % len(set(api_offline).intersection(critical_apis)), html.Br(),
                         # 'Non-critical API Disruption: %d' % len(set(api_offline).difference(critical_apis)),
                         ]
            children += ['Critical API Performance Impact Factor: %.1fx' % p]
        tradeoff_list.append(html.Div(className='tradeoff_list_item', children=children))

    xs_cost = np.asarray(xs_cost)
    ys_availability = np.asarray(ys_availability)
    zs_performance = np.asarray(zs_performance)

    hovertemplate = '<b>[CLICK TO SEE THE DETAILS]</b></br></br>' \
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

    return fig, {'display': 'Block'}, {'display': 'None'}, {'display': 'None'}, {'display': 'Block'}, tradeoff_list, []


@app.callback(
    [Output('network', 'children'), Output('placement-summary', 'children'),
     Output('api-summary', 'children'), Output('selected-option', 'children')],
    Input("tradeoff_graph", 'clickData'),
    State('api-select', 'value')
)
def display_click_data(clickData, critical_apis):
    if critical_apis is None:
        critical_apis = ()
    offloaded_mids = clickData['points'][0]['customdata'][5] if clickData is not None else set()
    cost = clickData['points'][0]['customdata'][6] if clickData is not None else 0.
    _performance = clickData['points'][0]['customdata'][8] if clickData is not None else 0.
    plan_id = clickData['points'][0]['customdata'][9] if clickData is not None else -1
    performance = exp.performance_est.estimate(plan=set(offloaded_mids), detailed=True)
    availability = exp.availability_est.estimate(plan=set(offloaded_mids), detailed=True)

    elements = []
    for mid in list(exp.microservices.keys()) + ['media-memcached', 'url-shorten-memcached']:
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
        ava_c = len(set(critical_apis).intersection(availability))
        ava_nc = len(availability)-len(set(critical_apis).intersection(availability))
        perf_c = 0
        if len(critical_apis) > 0:
            perf_c = np.mean([np.mean([tup[1] for tup in v]) / np.mean([tup[0] for tup in v]) for k, v in performance.items() if k in critical_apis])
        perf_nc = 0
        if len(critical_apis) != 9:
            perf_nc = np.mean([np.mean([tup[1] for tup in v]) / np.mean([tup[0] for tup in v]) for k, v in performance.items() if k not in critical_apis])
        if len(critical_apis) == 0:
            placement_summary = ['[Cost] USD %.1f' % cost, html.Br(),
                                 '[API Disruption] %d' % ava_nc, html.Br(),
                                 '[API Performance Impact] %.1fx' % perf_nc]
        else:
            placement_summary = ['[Cost] USD %.1f' % cost, html.Br(),
                                 '[API Disruption] Critical: %d | Non-critical: %d' % (ava_c, ava_nc), html.Br(),
                                 '[API Performance Impact] Critical: %.1fx | Non-critical: %.1fx' % (perf_c, perf_nc)]

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
    return network, placement_summary, api_summary, selected_option


@app.callback(
    [Output('query-traffic-graph', 'figure'), Output("resrc-fine", "children"), Output("resrc-aggr-graph", "figure")],
    [Input("simu-estimate-btn", "n_clicks"), Input('resrc-radio', 'value'),
     Input('cpu-slider', 'value'),
     Input('memory-slider', 'value'),
     Input('storage-slider', 'value')],
    [State("shape-dropdown", "value"),
     State("scale-dropdown", "value"),
     State("composition-dropdown", "value")]
)
def click_estimate(est_click, selected_metric, cpu_limit, memory_limit, storage_limit,
                   selected_load_shape, selected_multiplier, selected_composition):
    global exp

    exp.config_onprem.LIMIT_CPU_CORE = cpu_limit
    exp.config_onprem.LIMIT_MEMORY_GB = memory_limit
    exp.config_onprem.LIMIT_DISK_GB = storage_limit
    component2metrics = dataloader.get_component2metrics(selected_load_shape, selected_multiplier, selected_composition)
    exp = format_experiment(exp, component2metrics)
    query_traffic_figure = generate_query_traffic_figure(dataloader, selected_composition, selected_multiplier, selected_load_shape)
    aggr_usage_figure = generate_aggr_timeseries_figure(component2metrics, selected_metric,
                                                        {'cpu': cpu_limit, 'memory': memory_limit, 'usage': storage_limit})
    children = []
    for component in components:
        metadata = component2metrics[component] if component2metrics is not None else None
        fig_line = generate_timeseries_figure(metadata, selected_metric)
        name = {'nginx-thrift': 'NGINX Thrift',
                 'media-frontend': 'Media Frontend',
                 'media-mongodb': 'Media MongoDB',
                 'post-storage-service': 'Post Storage Service',
                 'post-storage-mongodb': 'Post Storage MongoDB',
                 'compose-post-service': 'Compose Post Service',
                 'user-timeline-service': 'User Timeline Service',
                 'user-timeline-mongodb': 'User Timeline MongoDB'}[component]
        icon_path = './assets/component_container.png'
        if 'mongodb' in component:
            icon_path = './assets/component_mongodb.png'
        elif 'nginx' in component or 'frontend' in component:
            icon_path = './assets/component_nginx.png'
        children.append(
            html.Div(className='component', children=[
                html.Div(className='component-logo', style={'height': 180}, children=[
                    html.Img(src=icon_path, style={'margin-top': '30px', 'width': '80px'}),
                    html.Div(style={'display': 'block'}, children=html.B(name))
                ]),
                html.Div(className='component-ts', children=dcc.Graph(id='graph-%s' % component, figure=fig_line))
            ])
        )
    resrc_fine_children = [html.Div(children)]
    return query_traffic_figure, resrc_fine_children, aggr_usage_figure


@app.callback([Output('scale-dropdown', 'options'), Output('composition-dropdown', 'options')],
              [Input('shape-dropdown', 'value')])
def set_load_shape(selected_load_shape):
    _min, _max = 1, 1
    _compositions = copy.deepcopy(DataLoader.compositions['seen'])

    if selected_load_shape == 'waves':
        _max = 3
        _compositions += DataLoader.compositions['unseen']
    _compositions = sorted(_compositions, key=lambda x: (-max(x), np.argmax(x)))
    if (20, 10, 70) in _compositions:
        _compositions.remove((20, 10, 70))
        _compositions = [(20, 10, 70)] + _compositions
    if (70, 10, 20) in _compositions:
        _compositions.remove((70, 10, 20))
        _compositions = [(70, 10, 20)] + _compositions
    if selected_load_shape != 'waves':
        if (30, 10, 60) in _compositions:
            _compositions.remove((30, 10, 60))
            _compositions = [(30, 10, 60)] + _compositions
        if (60, 10, 30) in _compositions:
            _compositions.remove((60, 10, 30))
            _compositions = [(60, 10, 30)] + _compositions
    options_scale = [{'label': '%dx more users' % d, 'value': d} for d in range(_min, _max+1)]
    options_composition = [{'label': 'compose:%d%% | read:%d%% | upload:%d%%' % (composition[0], composition[2], composition[1]),
                            'value': '_'.join(map(str, composition))} for composition in _compositions]
    return options_scale, options_composition


@app.callback([Output('dashboard-content', 'children')], [Input('dashboard-tabs', 'value')])
def render_content(tab):
    return generate_resource_card() if tab == 'dashboard-tab-resrc' else generate_migration_card()


app.layout = html.Div(
    id="app-container",
    children=[
        # Banner
        html.Div(id="banner", className="banner", children=[html.H5(app.title)]),
        # Left column
        html.Div(id="left-column", className="three columns", children=[generate_simulation_card()]),
        # Right column
        html.Div(id="right-column", className="nine columns", children=[
            dcc.Tabs(id="dashboard-tabs", value='dashboard-tab-resrc', children=[
                            dcc.Tab(label='Resource Dashboard', value='dashboard-tab-resrc'),
                            dcc.Tab(label='Migration Dashboard', value='dashboard-tab-migration'),
                        ]),
            html.Div(id='dashboard-content')
        ]),
    ],
)

# Run the server
if __name__ == "__main__":
    app.run_server(debug=False, port=8052)



from plotly.subplots import make_subplots
from core.moo import is_pareto
from dash import dcc
from dash import html
import plotly.graph_objects as go
import dash_cytoscape as cyto
import numpy as np
import dash


class DashVis_v1:
    @staticmethod
    def run(plans, exp):
        xs_cost = []
        ys_availability = []
        zs_performance = []
        customdata = []
        for plan in plans:
            onprem_msvcs = plan.onprem_msvcs
            cloud_msvcs = plan.cloud_msvcs

            xs_cost.append(plan.cost_model())
            ys_availability.append(plan.availability_model())
            zs_performance.append(plan.performance_model())

            c1 = '<br>'.join(['   %d) %s%s' % (
                num + 1, msvc,
                '  (Stateful: %.4fGB)' % (max(exp.microservices[msvc].disk_usage[:exp.now])) if exp.microservices[
                    msvc].is_stateful else '') for num, msvc in enumerate(onprem_msvcs)])
            c2 = '<br>'.join(['   %d) %s%s' % (
                num + 1, msvc,
                '  (Stateful: %.4fGB)' % (max(exp.microservices[msvc].disk_usage[:exp.now])) if exp.microservices[
                    msvc].is_stateful else '') for num, msvc in enumerate(cloud_msvcs)])
            customdata.append((c1, c2, len(onprem_msvcs), len(cloud_msvcs),
                               (sum(exp.microservices[msvc].is_stateful for msvc in cloud_msvcs)), cloud_msvcs))

        xs_cost = np.asarray(xs_cost)
        ys_availability = np.asarray(ys_availability)
        zs_performance = np.asarray(zs_performance)
        M = np.asarray([xs_cost, ys_availability, zs_performance]).transpose()
        pareto_ind = is_pareto(M, maximise=False)

        hovertemplate = '<b>Cost: USD %{x:.2f}</b><br>' \
                        '<b>Data Migration: %{y:.4f}%</b><br>' \
                        '<b>Intercloud Links: %{z}</b><br><br><b>===== Placement Plan =====</b><br>' \
                        'Keep %{customdata[2]:d} components on-prem:<br>' \
                        '%{customdata[0]}' \
                        '<br>Offload %{customdata[3]:d} components (%{customdata[4]:d} stateful) to the cloud:<b></b><br>' \
                        '%{customdata[1]}'
        customdata_opt = [c for i, c in enumerate(customdata) if pareto_ind[i]]
        customdata_nopt = [c for i, c in enumerate(customdata) if not pareto_ind[i]]

        fig = make_subplots(
            rows=4, cols=2, column_widths=[0.4, 0.6],
            specs=[[{}, {"rowspan": 4, 'type': 'scene'}], [{}, {}], [{}, {}], [{}, {}]],
            subplot_titles=(
                "CPU Usage", "Placement Plans (Hover and Click to See the Placement)", "Memory Usage", "", "Disk Usage", "",
                "IOps Usage"))

        microservices = exp.microservices
        timestamps_dt = exp.timestamps_dt
        t_now = exp.now

        for mid, microservice in microservices.items():
            fig.add_trace(go.Scatter(name=mid, x=timestamps_dt, y=microservice.cpu, stackgroup='cpu'), row=1, col=1)
            fig.add_trace(go.Scatter(name=mid, x=timestamps_dt, y=microservice.memory, stackgroup='memory'), row=2, col=1)
            fig.add_trace(go.Scatter(name=mid, x=timestamps_dt, y=microservice.disk_usage, stackgroup='disk'), row=3, col=1)
            fig.add_trace(go.Scatter(name=mid, x=timestamps_dt, y=microservice.iops, stackgroup='iops'), row=4, col=1)
        fig.update_yaxes(title_text="Cores", row=1, col=1)
        fig.add_shape(type="rect", x0=timestamps_dt[t_now], x1=timestamps_dt[-1], y0=0, y1=exp.config_onprem.LIMIT_CPU_CORE,
                      line=dict(width=0), fillcolor="green", opacity=0.2, row=1, col=1)

        fig.update_yaxes(title_text="GB", row=2, col=1)
        fig.add_shape(type="rect", x0=timestamps_dt[t_now], x1=timestamps_dt[-1], y0=0, y1=exp.config_onprem.LIMIT_MEMORY_GB,
                      line=dict(width=0), fillcolor="green", opacity=0.2, row=2, col=1)
        fig.update_yaxes(title_text="GB", row=3, col=1)
        fig.add_shape(type="rect", x0=timestamps_dt[t_now], x1=timestamps_dt[-1], y0=0, y1=exp.config_onprem.LIMIT_DISK_GB,
                      line=dict(width=0), fillcolor="green", opacity=0.2, row=3, col=1)
        fig.update_yaxes(title_text="IOps", row=4, col=1)
        fig.add_vline(x=timestamps_dt[t_now], line_width=1, line_dash="dot", line_color="red", row=1, col=1)
        fig.add_vline(x=timestamps_dt[t_now], line_width=1, line_dash="dot", line_color="red", row=2, col=1)
        fig.add_vline(x=timestamps_dt[t_now], line_width=1, line_dash="dot", line_color="red", row=3, col=1)
        fig.add_vline(x=timestamps_dt[t_now], line_width=1, line_dash="dot", line_color="red", row=4, col=1)

        fig.add_trace(go.Scatter3d(name='',
                                   x=xs_cost[np.logical_not(pareto_ind)],
                                   y=ys_availability[np.logical_not(pareto_ind)],
                                   z=zs_performance[np.logical_not(pareto_ind)],
                                   customdata=customdata_nopt,
                                   hovertemplate=hovertemplate, marker=dict(color='orange', opacity=0.2),
                                   mode='markers'), row=1, col=2)
        fig.add_trace(go.Scatter3d(name='',
                                   x=xs_cost[pareto_ind],
                                   y=ys_availability[pareto_ind],
                                   z=zs_performance[pareto_ind],
                                   customdata=customdata_opt,
                                   hovertemplate=hovertemplate, marker=dict(color='red', opacity=1.0),
                                   mode='markers'), row=1, col=2)
        fig.update_scenes(xaxis={'title_text': 'Cost (USD)'},
                          yaxis={'title_text': 'Data Migration (%)'},
                          zaxis={'title_text': 'Number of Inter-cloud Links'},
                          aspectmode='cube')

        title = "API-aware Microservice Placement for Hybrid Multi-cloud | " \
                "[On-prem Limit] CPU: %d cores | Memory: %d GB | Storage: %d GB" % (exp.config_onprem.LIMIT_CPU_CORE,
                                                                                    exp.config_onprem.LIMIT_MEMORY_GB,
                                                                                    exp.config_onprem.LIMIT_DISK_GB)
        fig.update_layout(showlegend=False, title_text=title)

        elements = []
        for mid in microservices:
            elements.append({'data': {'id': mid, 'label': mid}, 'classes': 'onprem'})
        for mid_from, microservice in microservices.items():
            for mid_to in microservice.outbound_to:
                elements.append({'data': {'source': mid_from, 'target': mid_to}, 'classes': 'onprem'})

        app = dash.Dash()
        app.layout = html.Div(children=[
            html.Div(style={'float': 'left'}, children=dcc.Graph(id='basic', figure=fig, style={'width': '70vw',
                                                                                                'height': '100vh'})),
            html.Div(style={'float': 'left'}, id='network', children=[
                cyto.Cytoscape(
                    elements=elements,
                    layout={'name': 'breadthfirst', 'roots': '#nginx-thrift, #media-frontend'},
                    style={'width': '30vw', 'height': '100vh'},
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
                                'background-color': 'orange',
                                'line-color': 'orange'
                            }
                        },
                        {
                            'selector': '.cloud',
                            'style': {
                                'background-color': 'red',
                                'line-color': 'red',
                                'shape': 'star'
                            }
                        }
                    ]
                )
            ]),

        ])
        from dash.dependencies import Input, Output

        @app.callback(
            Output('network', 'children'),
            Input('basic', 'clickData'))
        def display_click_data(clickData):
            offloaded_mids = clickData['points'][0]['customdata'][-1] if clickData is not None else []
            elements = []
            for mid in microservices:
                elements.append({'data': {'id': mid, 'label': mid},
                                 'classes': ['onprem', 'cloud'][mid in offloaded_mids]})
            for mid_from, microservice in microservices.items():
                for mid_to in microservice.outbound_to:
                    elements.append({'data': {'source': mid_from, 'target': mid_to},
                                     'classes': ['intra', 'inter'][
                                         (mid_from in offloaded_mids) != (mid_to in offloaded_mids)]})

            return cyto.Cytoscape(
                elements=elements,
                layout={'name': 'breadthfirst', 'roots': '#nginx-thrift, #media-frontend'},
                style={'width': '27vw', 'height': '100vh'},
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

        app.run_server(debug=True)

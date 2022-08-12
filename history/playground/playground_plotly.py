from dash import Dash, html
import dash_cytoscape as cyto

app = Dash(__name__)

app.layout = html.Div([
    html.P("Dash Cytoscape:"),
    cyto.Cytoscape(
        id='cytoscape',
        elements=[
            {'data': {'id': 'client', 'label': 'Client'}},
            {'data': {'source': 'client', 'target': 'thrift-frontend'}},
            {'data': {'source': 'client', 'target': 'media-frontend'}},
            {'data': {'id': 'media-frontend', 'label': 'Media NGINX'}},
            {'data': {'id': 'media-mongodb', 'label': 'Media MongoDB'}},
            # {'data': {'source': 'media-frontend', 'target': 'media-mongodb'}},
            {'data': {'id': 'thrift-frontend', 'label': 'Frontend NGINX'}},
            {'data': {'source': 'thrift-frontend', 'target': 'user-service'}},
            {'data': {'source': 'thrift-frontend', 'target': 'compose-post-service'}},
            {'data': {'source': 'thrift-frontend', 'target': 'home-timeline-service'}},
            {'data': {'source': 'thrift-frontend', 'target': 'user-timeline-service'}},
            {'data': {'id': 'user-service', 'label': 'User Service'}},
            {'data': {'id': 'user-mongodb', 'label': 'User MongoDB'}},
            {'data': {'source': 'user-service', 'target': 'user-mongodb'}},
            {'data': {'id': 'social-graph-service', 'label': 'Social Graph Service'}},
            {'data': {'source': 'user-service', 'target': 'social-graph-service'}},
            {'data': {'id': 'social-graph-mongodb', 'label': 'Social Graph MongoDB'}},
            {'data': {'source': 'social-graph-service', 'target': 'social-graph-mongodb'}},
            {'data': {'id': 'compose-post-service', 'label': 'Compose Post Service'}},
            {'data': {'id': 'home-timeline-service', 'label': 'Home Timeline Service'}},
            {'data': {'source': 'home-timeline-service', 'target': 'post-storage-service'}},
            {'data': {'id': 'user-timeline-service', 'label': 'User Timeline Service'}},
            {'data': {'id': 'user-timeline-mongodb', 'label': 'User Timeline MongoDB'}},
            {'data': {'source': 'user-timeline-service', 'target': 'user-timeline-mongodb'}},
            {'data': {'id': 'post-storage-service', 'label': 'Post Storage Service'}},
            {'data': {'source': 'user-timeline-service', 'target': 'post-storage-service'}},
            {'data': {'id': 'post-storage-mongodb', 'label': 'Post Storage MongoDB'}},
            {'data': {'source': 'post-storage-service', 'target': 'post-storage-mongodb'}},
        ],
        layout={'name': 'breadthfirst', 'roots': '[id = "client"]'},
        style={'width': '400px', 'height': '500px'}
    )
])


app.run_server(debug=True)
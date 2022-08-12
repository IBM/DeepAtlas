import pickle


with open('./experiments/202207221540_202207221911/edge_bytes.pkl', 'rb') as f:
    data = pickle.load(f)

for api, edges in data.items():
    print('=== %s ===' % api)
    for edge, num_bytes in edges.items():
        print('    > %s' % str(edge))
        print('        - Request : %.4f bytes' % num_bytes['request'])
        print('        - Response: %.4f bytes' % num_bytes['response'])

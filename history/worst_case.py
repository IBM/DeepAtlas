from constants import *
import pandas as pd

csv = pd.read_csv('enumerate.csv')
components = list(csv.columns)[11:]
csv['offloaded'] = sum(csv[component] for component in components)
# horrible = csv[csv['score-sum'] >= 200][csv['offloaded'] <= 5][csv['/wrk2-api/home-timeline/read'] > 1][csv['compose-post-service'] >= 1][csv['nginx-thrift'] >= 1]

horrible = csv[(csv['nginx-thrift'] == 1) &
               (csv['media-frontend'] == 1) &
               (csv['post-storage-service'] == 1) &
               (csv['social-graph-service'] == 1) &
               (csv['offloaded'] <= 5)]


for index, row in horrible.iterrows():
    print('========= Rank %d ===========' % (index + 1))
    for i in range(9):
        print('%s: %.1fx' % (READABLE_NAME[ID2API[i]], row.values[2+i]))
    print('Components:')
    for cid, component in enumerate(components):
        if row.values[11+cid]:
            print('  > %s' % component)
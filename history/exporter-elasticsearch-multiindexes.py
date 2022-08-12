from elasticsearch import Elasticsearch
from datetime import datetime
from tqdm import tqdm
import pickle
import os


ELASTICSEARCH_HOST = 'http://c4130-110233.wisc.cloudlab.us:32197'
ELASTICSEARCH_INDEXES = ['jaeger-span-2022-07-22', 'jaeger-span-2022-07-23']


es = Elasticsearch(hosts=[ELASTICSEARCH_HOST])


########################################################################################################################
# Stage 1: Get all trace IDs for sorting and searching
########################################################################################################################
def run_stage_1():
    def process_page_for_ids(index, page, traceID2time):
        for span in page['hits']['hits']:
            traceID = (index, span['_source']['traceID'])
            if traceID not in traceID2time:
                traceID2time[traceID] = float('inf')
            traceID2time[traceID] = min(traceID2time[traceID], span['_source']['startTime'])

        num_hits = len(page['hits']['hits'])
        num_total = page['hits']['total']
        return num_hits, num_total

    # Initialize the scroll
    traceID2time = {}
    num_processed = 0

    for ELASTICSEARCH_INDEX in ELASTICSEARCH_INDEXES:
        page = es.search(index=ELASTICSEARCH_INDEX, scroll='2m', size=1000, body={'query': {"match_all": {}}})
        num_hits, num_total = process_page_for_ids(ELASTICSEARCH_INDEX, page, traceID2time)
        num_processed += num_hits
        sid = page['_scroll_id']

        # Start scrolling
        while num_hits > 0:
            page = es.scroll(scroll_id=sid, scroll='2m')
            num_hits, num_total = process_page_for_ids(ELASTICSEARCH_INDEX, page, traceID2time)
            num_processed += num_hits

            print('Processed: %d/%d (%d%%) | %d traces | %s' % (
                num_processed, num_total, num_processed * 100 / num_total, len(traceID2time), ELASTICSEARCH_INDEX))
            sid = page['_scroll_id']

    # Generate experiment ID
    timestamp_list = list(traceID2time.values())
    timestamp_min, timestamp_max = min(timestamp_list), max(timestamp_list)
    dt_start = datetime.fromtimestamp(timestamp_min * 1e-6)
    dt_end = datetime.fromtimestamp(timestamp_max * 1e-6)
    experiment_id = '%04d%02d%02d%02d%02d_%04d%02d%02d%02d%02d' % (
        dt_start.year, dt_start.month, dt_start.day, dt_start.hour, dt_start.minute,
        dt_end.year, dt_end.month, dt_end.day, dt_end.hour, dt_end.minute
    )
    print('Experiment ID: %s' % experiment_id)
    os.makedirs('experiments/%s' % experiment_id)
    with open('experiments/%s/trace_ids.pkl' % experiment_id, 'wb') as o:
        pickle.dump(traceID2time, o)
    return experiment_id


########################################################################################################################
# Stage 2: Get all trace IDs for sorting and searching
########################################################################################################################
def run_stage_2(experiment_id):
    def es_query(query, index, size=1000):
        page = es.search(index=index, size=size, body={'query': query})
        return [record['_source'] for record in page['hits']['hits']]

    with open('experiments/%s/trace_ids.pkl' % experiment_id, 'rb') as o:
        traceID2time = pickle.load(o)
        traceID2time = sorted(list(traceID2time.items()), key=lambda tup: (tup[1], tup[0]))

    buckets = []
    for traceID, timestamp in traceID2time:
        dt = datetime.fromtimestamp(timestamp / 1e6)
        dt_id = datetime(dt.year, dt.month, dt.day, dt.hour, dt.minute)
        if len(buckets) == 0 or buckets[-1][0] != dt_id:
            buckets.append((dt_id, []))
        buckets[-1][1].append(traceID)

    print('Number of Buckets: %d' % len(buckets))
    os.makedirs('experiments/%s/traces' % experiment_id, exist_ok=True)
    for i, (dt, traces) in enumerate(buckets):
        bucket_data = {}
        pbar = tqdm(traces)
        pbar.set_description('%d/%d' % (i + 1, len(buckets)))
        for index, traceID in pbar:
            # Initialize the scroll
            results = es_query(query={'match': {'traceID': traceID}}, index=index)
            results = sorted(results, key=lambda record: record['startTime'])
            bucket_data[traceID] = results
        with open('experiments/%s/traces/%d_%04d%02d%02d%02d%02d.pkl' % (
                experiment_id, i, dt.year, dt.month, dt.day, dt.hour, dt.minute), 'wb') as o:
            pickle.dump(bucket_data, o)


if __name__ == '__main__':
    # experiment_id = run_stage_1()
    experiment_id = '202207221540_202207221911'
    run_stage_2(experiment_id)


es.close()

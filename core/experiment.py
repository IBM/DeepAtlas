from core.application import Microservice
from datetime import datetime
from core.config import *
import json


class Experiment:
    def __init__(self, path, speedup_factor=144, ts_offset=1641024000, ignore=False):
        with open(path) as f:
            data = json.load(f)
        self.microservices = {k: Microservice(config=v) for k, v in data['components'].items()}
        if ignore:
            self.microservices = {k: v for k, v in self.microservices.items() if k not in {'url-shorten-memcached', 'media-memcached'}}
        self.msvcs = tuple(self.microservices.keys())
        self.step_size = data['step'] * speedup_factor
        self.timestamps = data['timestamps']
        self.timestamps_dt = [datetime.fromtimestamp(ts_offset + t * self.step_size) for t in range(len(self.timestamps))]
        self.now = 28 * 60 // 5
        self.config_onprem = OnPremConfig()
        self.config_cloud = CloudConfig()
        self.constraints = []

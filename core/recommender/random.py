from core.application import PlacementPlan
from tqdm import tqdm
import random


class RandomRecommender(object):
    @staticmethod
    def run(exp, num_runs=1000):
        movable_msvcs = [msvc for msvc in exp.msvcs if msvc not in exp.constraints]

        recommended_plans = []
        chosen = set()
        # while True:
        for _ in range(num_runs):
            sample_size = random.choice(range(1, 1 + len(movable_msvcs)))
            cloud_msvcs = random.sample(movable_msvcs, k=sample_size)

            mapping = {msvc: PlacementPlan.CLOUD if msvc in cloud_msvcs else PlacementPlan.ONPREM for msvc in exp.msvcs}
            plan = PlacementPlan(mapping, exp)
            if plan.onprem_msvcs not in chosen and plan.is_feasible:# and (exp.config_cloud.BUDGET is None or plan.cost_model() <= exp.config_cloud.BUDGET):
                recommended_plans.append(plan)
                chosen.add(plan.onprem_msvcs)
                print(len(recommended_plans))
            # if len(recommended_plans) == num_runs:
            #     break
        return recommended_plans

import matplotlib.pyplot as plt
from pymoo.core.duplicate import ElementwiseDuplicateElimination
from pymoo.core.problem import ElementwiseProblem
from pymoo.visualization.scatter import Scatter
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.core.crossover import Crossover
from pymoo.core.sampling import Sampling
from pymoo.core.mutation import Mutation
from pymoo.optimize import minimize
from core.recommender import PlacementPlan
import numpy as np
from core.moo import is_pareto
from pyrecorder.recorder import Recorder
from pyrecorder.writers.video import Video
import string

from core.experiment import Experiment
from core.recommender import RandomRecommender
from core.visualize import DashVis_v1


exp = Experiment(path='./data/20220617-metrics-istio.json')
print('Number of Components       : %d' % len(exp.msvcs))
print('Number of Placement Choices: %d' % (2 ** len(exp.msvcs)))


class MPProblem(ElementwiseProblem):
    def __init__(self, experiment):
        super().__init__(n_var=len(experiment.msvcs), n_obj=2, n_constr=4)
        self.experiment = experiment

    def _evaluate(self, x, out, *args, **kwargs):
        msvcs = self.experiment.msvcs
        mapping = {msvcs[ind]: location for ind, location in enumerate(x)}
        plan = PlacementPlan(mapping, self.experiment)

        cost = plan.cost_model()
        performance = plan.performance_model()
        availability = plan.availability_model()

        out["F"] = [cost, availability]
        out['G'] = [plan.onprem_usage_max_cpu - self.experiment.config_onprem.LIMIT_CPU_CORE,
                    plan.onprem_usage_max_memory - self.experiment.config_onprem.LIMIT_MEMORY_GB,
                    plan.onprem_usage_max_disk - self.experiment.config_onprem.LIMIT_DISK_GB,
                    cost - self.experiment.config_cloud.BUDGET]


class MPCrossover(Crossover):
    def __init__(self):

        # define the crossover: number of parents and number of offsprings
        super().__init__(2, 2)

    def _do(self, problem, X, **kwargs):

        # The input of has the following shape (n_parents, n_matings, n_var)
        _, n_matings, n_var = X.shape

        # The output owith the shape (n_offsprings, n_matings, n_var)
        # Because there the number of parents and offsprings are equal it keeps the shape of X
        Y = np.full_like(X, None, dtype=object)

        # for each mating provided
        for k in range(n_matings):

            # get the first and the second parent
            a, b = X[0, k], X[1, k]

            # prepare the offsprings
            off_a = []
            off_b = []

            for i in range(len(problem.experiment.msvcs)):
                if np.random.random() < 0.5:
                    off_a.append(a[i])
                    off_b.append(b[i])
                else:
                    off_a.append(b[i])
                    off_b.append(a[i])

            # join the character list and set the output
            Y[0, k, :], Y[1, k, :] = off_a, off_b

        return Y


class MPMutation(Mutation):
    def __init__(self):
        super().__init__()

    def _do(self, problem, X, **kwargs):
        # for each individual
        for i in range(len(X)):
            r = np.random.random()
            # with a probability of 40% - change the order of characters
            if r < 0.4:
                perm = np.random.permutation(len(problem.experiment.msvcs))
                X[i, :] = X[i][perm]
            # also with a probability of 40% - change a character randomly
            elif r < 0.8:
                prob = 1 / len(problem.experiment.msvcs)
                X[i, :] = [c if np.random.random() > prob else np.random.choice([PlacementPlan.CLOUD,
                                                                                 PlacementPlan.ONPREM]) for c in X[i]]
        return X


class MPSampling(Sampling):
    def _do(self, problem, n_samples, **kwargs):
        return np.random.choice([PlacementPlan.CLOUD, PlacementPlan.ONPREM], size=(n_samples, problem.n_var))


class MPDuplicateElimination(ElementwiseDuplicateElimination):
    def is_equal(self, a, b):
        return np.array_equal(a.X, b.X)


plans_random = RandomRecommender.run(exp, num_runs=1000)
M = np.asarray([(plan.cost_model(), plan.availability_model()) for plan in plans_random])
F_random = M[is_pareto(M)]
print('Number of Solutions by Random Search: %d' % np.sum(F_random))

algorithm = NSGA2(pop_size=30,
                  sampling=MPSampling(),
                  crossover=MPCrossover(),
                  mutation=MPMutation(),
                  eliminate_duplicates=MPDuplicateElimination())

res = minimize(MPProblem(exp), algorithm, ('n_gen', 200), seed=1, verbose=True, save_history=True)
labels = ['Cost (USD)', 'Data Migration (%)']

with Recorder(Video("ga.mp4")) as rec:
    # for each algorithm object in the history
    for i, entry in enumerate(res.history):
        sc = Scatter(title=("Generation %s" % entry.n_gen), labels=labels, xlim=(25, 275), ylim=(0, 100))
        for j in range(i):
            sc.add(res.history[j].pop.get('F'), color='lightgrey')
        sc.add(entry.pop.get("F"), color='red')
        sc.do()
        # finally record the current visualization to the video
        rec.record()

import numpy as np
from optimizer.algorithms import Random_
from test_functions import sphere as test_function

np.random.seed(42)

constraints = ((0, 1), (0, 1), (0, 1))
results = []
parameters = []
optimum = 999


algorithm = Random_()

while optimum > 1:
    vector = algorithm.optimize(parameters=parameters,
                                results=results, constraints=constraints)
    parameters.append(vector)
    new_result = test_function(vector)
    results.append(new_result)
    optimum = np.amin(results)

print("Function calls: " + str(len(results)) + "\n"
      "Best result: " + str(optimum) + "\n"
      "Best parameters: " + str(parameters[np.argmin(results)]) + "\n"
      "Global optimum: f(x*) = 0 for x* = (0.5,...,0.5)")

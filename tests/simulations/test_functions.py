import numpy as np

""" Test functions for optimization problems.
    Functions assume vector has min-max of [0, 1] """


def sphere(vector):
    """
    Python implementation of sphere function. Dimensions: d
    Input Domain: hypercube xi ∈ [-5.12, 5.12], for all i = 1, …, d. 
    Global optimum: f(x*) = 0 for x* = (0.5,...,0.5)
    Details: https://www.sfu.ca/~ssurjano/spheref.html
    """
    # rescale onto [-5, 5]
    vector = 10 * vector - 5
    result = np.sum(vector**2)
    return round(result, 2)


def rosenbrock(vector):
    """
    Python implementation of rosenbrock function.
    Dimensions: d. The function is unimodal, and the global minimum lies in 
    a narrow, parabolic valley. Input Domain: hypercube xi ∈ [-5, 10], 
    for all i = 1, …, d, or xi ∈ [-2.048, 2.048], for all i = 1, …, d.
    Global Minimum: f(x*) = 0 for x* = (1,...,1)
    Details: https://en.wikipedia.org/wiki/Rosenbrock_function
    """
    result = []
    # rescale onto [-2, 2]
    vector = 4 * vector - 2
    for idx, v in enumerate(vector[:-1]):
        result += 100 * (vector[idx + 1] - v**2) ** 2 + (1 - v) ** 2
    return round(result, 2)


def styblinski_tank(vector):
    """
    Python implementation of Styblinski-Tank function.
    Dimensions: d. The function is usually evaluated on the hypercube 
    xi ∈ [-5, 5],, for all i = 1, …, d. Global Minimum: 39.16 * d
    Details: https://www.sfu.ca/~ssurjano/stybtang.html
    """
    # rescale onto [-5, 5]
    vector = 10 * vector - 5
    result = 0.5 * np.sum(vector**4.0 - 16*vector**2.0 + 5.0*vector)
    return round(result, 2)


def himmelblau(vector):
    """
    Python implementation of Himmelblau function. 
    Details: https://en.wikipedia.org/wiki/Himmelblau%27s_function
    """
    assert len(vector) == 2, "Function only defined for 2 dimensions."
    # rescale onto [-5, 5]
    vec = 10 * vector - 5
    result = (vec[0]**2 + vec[1] - 11)**2 + (vec[0] + vec[1]**2 - 7)**2
    return round(result, 2)


def schwefel(vector):
    """
    Python implementation of Schwefel function.
    Dimensions: d. Complex, many local minima.
    Input Domain: hypercube xi ∈ [-500, 500], for all i = 1, …, d.
    Global Minimum: f(x*) = 0, for x* = (420.9687,...,420.9687
    Details: https://www.sfu.ca/~ssurjano/schwef.html
    """
    # rescale onto [-500, 500]
    vector = 1000 * vector - 500
    dims = len(vector)
    result = 418.9829 * dims - np.sum(vector*np.sin(np.sqrt(abs(vector))))
    return round(result, 2)


def noise(factor):
    return factor * np.random.randn()

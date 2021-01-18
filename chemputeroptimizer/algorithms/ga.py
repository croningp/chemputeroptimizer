"""Genetic Algorithm"""

import random

import numpy as np

from ..algorithms import AbstractAlgorithm


class GA(AbstractAlgorithm):
    """
    Custom generational genetic algorithm for sequential optimization of
    mixed integer non-linear problems with truncation selection,
    single point crossover, and random reset mutation.

    Hyperparameters:
        pop_size (int): Population size
        mutation_rate (float): Probability (0 to 1) of mutating a gene

    Other Attributes:
        num_genes (int): Number of genes
        offspring (np.array): Array with offspring
        mutated (np.array): Array with mutated individuals
        suggestions (np.array): Array of suggested points
        elit (np.array): Best parameters obtained so far
        elit_results (float): Best result obtained so far
        counter (int): Used to trigger restart in case of premature convergence
    """

    DEFAULT_CONFIG = {
        "pop_size": 8,
        "mutation_rate": 0.3
    }

    def __init__(self, dimensions=None, config=None):
        self.name = 'GA'
        self.pop_size = None
        self.num_parents = None
        self.mutation_rate = None
        super().__init__(dimensions, config)

        for key, value in self.config.items():
            setattr(self, key, value)

        self.num_parents = int(self.pop_size / 2)
        self.num_genes = len(dimensions)
        self.population = None
        self.parents = None
        self.offspring = None
        self.mutated = None
        self.suggestions = None
        self.elit = None
        self.elit_result = None
        self.counter = 0
        self.generation = 0

    def initialise(self):
        """Initialise population via random sampling."""
        self.population = np.empty((0, self.num_genes))

        ind = np.empty((1, self.num_genes))
        for _ in range(self.pop_size):
            for gene, bounds in enumerate(self.dimensions):
                if isinstance(bounds[0], float):
                    rand_num = np.around(np.random.uniform(low=bounds[0], high=bounds[1]), 2)
                elif isinstance(bounds[0], int):
                    rand_num = np.random.randint(low=bounds[0], high=bounds[1]+1)
                ind[0][gene] = rand_num
            self.population = np.vstack((self.population, ind))

        return self.population

    def selection(self, fitness, params):
        """select parents for crossover"""

        self.parents = np.empty((0, self.num_genes))

        # sort unique solutions by fitness (minimum)
        fit_idx = np.argsort(fitness, axis=0).flatten().tolist()

        # truncation selection
        self.parents = params[fit_idx[:self.num_parents]]

        return self.parents

    def crossover(self):
        """Produce offspring from parents"""

        self.offspring = np.empty((0, self.num_genes))
        parents = self.parents.copy()

        while len(parents) > 1:

            # ensure random pairing
            np.random.shuffle(parents)

            # random crossover point
            crossover_point = np.random.randint(1, self.num_genes)

            # draw parents without replacement
            parent1, parents = parents[-1], parents[:-1]
            parent2, parents = parents[-1], parents[:-1]

            # produce two offspring per pair of parents
            child1 = np.hstack((parent1[:crossover_point], parent2[crossover_point:]))
            child2 = np.hstack((parent2[:crossover_point], parent1[crossover_point:]))

            self.offspring = np.vstack((self.offspring, child1, child2))

        return self.offspring

    def mutation(self):
        """Mutate individuals"""

        self.mutated = np.empty((0, self.num_genes))

        individuals = np.vstack((self.parents, self.offspring))

        for _ in range(individuals.size):
            if (np.random.rand() < self.mutation_rate):
                # select individual
                rand_ind = random.randrange(0, individuals.shape[0])
                # select gene
                rand_gene = random.randrange(0, self.num_genes)
                # select random reset
                if isinstance(self.dimensions[rand_gene][0], float):
                    rand_num = np.around(np.random.uniform(
                        low=self.dimensions[rand_gene][0],
                        high=self.dimensions[rand_gene][1]), 2)
                elif isinstance(self.dimensions[rand_gene][0], int):
                    rand_num = np.random.randint(
                        low=self.dimensions[rand_gene][0],
                        high=self.dimensions[rand_gene][1]+1)

                # mutate individual
                individuals[rand_ind, rand_gene] = rand_num

        self.mutated = individuals

        return self.mutated

    def update(self):
        """Update the population with mutated individuals and elit"""

        self.population = np.empty((0, self.num_genes))

        # handle premature convergence
        if self.counter > 1000:
            print(f"Genetic algorithm converged.")
            print(f"Best result: {self.elit_result} for {self.elit}")
            print(f"Randomly reset population with elit.")
            restart = self.initialise()
            self.population = np.vstack((restart[:-1], self.elit))

        else:
            # carry over elit to next generation
            self.population = np.vstack((self.mutated, self.elit))

        return self.population

    def suggest(self, parameters=None, results=None, constraints=None):
        """Suggest next point to evaluate"""

        if constraints is None:
            constraints = self.dimensions

        if self.population is None:
            # initialise GA
            self.suggestions = self.initialise()

        if results.size != 0:
            # remember best solution
            self.elit = parameters[np.argmin(-results)]
            self.elit_result = np.amin(-results)

        self.logger.debug('GA optimizer for the following parameters: \n\
                          parameters: %s\nresults: %s\nconstraints: %s\n',
                          parameters, results, constraints)

        # perform genetic operation until new suggestions are found
        while self.suggestions is None or self.suggestions.size == 0:

            # find fitness values for parameters in population
            fitness = np.empty((0, results.shape[1]))
            params = np.empty((0, self.num_genes))
            for idx, val in enumerate(parameters):
                if np.any(np.all(val == self.population, axis=1)):
                    row = np.where(np.all(val == self.population, axis=1))
                    params = np.vstack((params, self.population[row]))
                    fitness = np.vstack((fitness, -results[idx]))

            # genetic operations
            self.generation += 1
            self.selection(fitness, params)
            self.crossover()
            self.mutation()
            self.update()
            self.suggestions = self.population

            # drop duplicates
            self.suggestions = np.unique(self.suggestions, axis=0)

            # drop previously evaluated points
            self.suggestions = np.array(
                [i for i in self.suggestions.tolist() if i not in parameters.tolist()])

            # counter to check for premature convergence
            if self.suggestions.size == 0:
                self.counter += 1
            else:
                self.counter = 0

        next_, self.suggestions = self.suggestions[-1], self.suggestions[:-1]

        return next_

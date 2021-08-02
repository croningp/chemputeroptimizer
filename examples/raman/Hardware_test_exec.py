#%%
import os
from chemputeroptimizer import ChemputerOptimizer
from chempiler import Chempiler
import ChemputerAPI
import AnalyticalLabware
#%%
HERE = os.path.abspath(os.path.dirname(__file__))

CONFIG = 'optimizer_config.json'
PROCEDURE =  'Procedure_attempt_opt.xdl' #,os.path.join(HERE, 'xdl',
GRAPH = 'optim_graph.json' # )os.path.join(HERE, 'graph', 

#%%
print(PROCEDURE)
print(GRAPH)

#%%
co = ChemputerOptimizer(
    PROCEDURE,
    GRAPH,
    interactive=False,
)
#%%
c = Chempiler(
    experiment_code='ABC',
    graph_file=GRAPH,
    output_dir='output',
    simulation=False,
    device_modules=[ChemputerAPI, AnalyticalLabware.devices]
)
#%%
co.prepare_for_optimization(opt_params=CONFIG)
#%%
co.optimize(c)

# %%
c['Raman'].set_integration_time(2)

# %%
c['Raman'].get_spectrum()
c['Raman'].spectrum.show_spectrum()
# %%
c['Raman'].spectrum.save_data()
# %%
c.move("water", "reactor", 25)
c.stirrer.stir("reactor")
c.stirrer.set_stir_rate("reactor", 500)
c.wait(100)
c.stirrer.stop_stir("reactor")
c.move("reactor", "waste_3", 'all')
# %%
c.stirrer.stir("reactor")
c.stirrer.set_stir_rate("reactor", 500)
print("Done!")
# %%
c.move("water", "waste_1", 15)


# %%

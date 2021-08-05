#!/usr/bin/env python
# coding: utf-8

# In[1]:


import json
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd

from AnalyticalLabware.devices import SpinsolveNMRSpectrum


# In[2]:


# loading all the data
DATA_PATH = r'\\SCAPA4\scapa4\group\Artem Leonov\Data\unknown trifluoromethylation'
path = Path(DATA_PATH)


# In[3]:


df = pd.read_csv(path.joinpath('trifluoromethylation_B_data annotated.csv'))


# In[4]:


df


# In[5]:


spec_paths = [
    p for p in path.joinpath('nmr_data').iterdir() if int(p.stem) in df['spec file'].to_list()
]


# In[42]:


specs = {}
for spec_path in spec_paths:
    spec = SpinsolveNMRSpectrum(False)
    spec.load_data(spec_path)
    spec.reference_spectrum(-113.15, 'closest')
    specs[spec_path.stem] = spec


# In[7]:


specs


# In[8]:


regs_params = [False, True, False, .1, .1]


# In[277]:


specs_regs = {}
for key, spec in specs.items():
    if key in ['1626813487', '1619429009']:
        continue
    regs = spec.generate_peak_regions(*regs_params)
    regs_x = []
    regs_y = []
    for reg in regs:
        reg_x = np.around(spec.x[reg[0]:reg[1]], 3).tolist()
        reg_y = np.around(spec.y[reg[0]:reg[1]].real, 3).tolist()
        regs_x.append(reg_x)
        regs_y.append(reg_y)
    specs_regs[key] = {'x': regs_x, 'y': regs_y}


# In[278]:


fig, ax = plt.subplots(figsize=(20, 12))

for key, regs in specs_regs.items():
    for xs, ys in zip(regs['x'], regs['y']):
        ax.scatter(xs, np.full_like(xs, int(key)), color='xkcd:grey', alpha=.2)
ax.invert_xaxis()


# In[279]:


all_regs_xs = []
for key, regs in specs_regs.items():
    for xs in regs['x']:
        all_regs_xs.extend(xs)


# In[280]:


len(all_regs_xs)


# In[281]:


len(set(all_regs_xs))


# In[282]:


xs_count = []
for x in set(all_regs_xs):
    xs_count.append((x, all_regs_xs.count(x)))


# In[283]:


xs_count[0]


# In[284]:


fig, ax = plt.subplots(figsize=(20, 12))

spec = specs['1619198007']

ax.scatter(
    [x_count[0] for x_count in xs_count],
    [x_count[1] for x_count in xs_count],
    alpha=.5
)
ax.plot(spec.x, spec.y.real/spec.y.real.mean()/2, alpha=.6)

ax.invert_xaxis()


# In[285]:


fig, ax = plt.subplots(figsize=(20, 12))

spec = specs['1619198007']

for value in range(10):
    xs_valid = [
        x_count[0] for x_count in xs_count
        if x_count[1] > value
    ]
    ax.scatter(
        xs_valid,
        np.full_like(xs_valid, value*10),
        alpha=.5,
        label=value
    )
    
ax.plot(spec.x, spec.y.real/spec.y.real.mean()/2, alpha=.6)

ax.legend()
ax.invert_xaxis()


# In[286]:


xs_valid = [
    x_count[0] for x_count in xs_count
    if x_count[1] > 0
]


# In[287]:


xs_valid.sort()
xsv = np.array(xs_valid)


# In[288]:


np.mean(np.diff(xsv))


# In[289]:


# getting coordinates of points with large diff
np.argwhere(np.diff(xsv) > np.mean(np.diff(xsv)))


# In[290]:


# splitting array by the coordinates
true_regions = np.split(xsv, np.argwhere(np.diff(xsv) > np.mean(np.diff(xsv))).flatten() + 1)


# In[291]:


for key, spec in specs.items():
    fig, ax = plt.subplots(figsize=(16, 10))
    
    ax.plot(spec.x, spec.y.real)
    
    for tr in true_regions[::-1]:
        xtr = spec.x[np.where((spec.x > tr[0]) & (spec.x < tr[-1]))]
        ytr = spec.y[np.where((spec.x > tr[0]) & (spec.x < tr[-1]))]
        area = spec.integrate_area((tr[-1], tr[0]))
        ax.scatter(xtr, ytr.real, label=area)
        
    
    ax.invert_xaxis()
    ax.legend()
    
    fig.savefig(f'{key} common regions (1).png', dpi=300)
#     break


# In[292]:


# building final data table
results = {}
for key, spec in specs.items():
    results[key] = {}
    for tr in true_regions[::-1]:
        xtr = spec.x[np.where((spec.x > tr[0]) & (spec.x < tr[-1]))]
        ytr = spec.y[np.where((spec.x > tr[0]) & (spec.x < tr[-1]))]
        area = spec.integrate_area((tr[-1], tr[0]))
        results[key].update({
            f'{tr[-1]}_{tr[0]}': area
        })


# In[293]:


results = {}

for tr in true_regions[::-1]:
    result_key = f'spectrum_integration-area_{tr[-1]}..{tr[0]}'
    results[result_key] = {}
    
    for key, spec in specs.items():
        xtr = spec.x[np.where((spec.x > tr[0]) & (spec.x < tr[-1]))]
        ytr = spec.y[np.where((spec.x > tr[0]) & (spec.x < tr[-1]))]
        area = spec.integrate_area((tr[-1], tr[0]))
        
        results[result_key].update({key: area})


# In[294]:


results


# In[295]:


dfi = df.set_index('spec file', drop=False)


# In[296]:


results_df = pd.DataFrame(results)


# In[297]:


results_df.index = results_df.index.astype('int64')


# In[298]:


dfi.index


# In[299]:


results_df.index


# In[300]:


full_df = pd.concat((dfi, results_df), axis=1)


# In[302]:


full_df.to_csv(path.joinpath('full_dataset (1).csv'), index=False)


# In[303]:


result_key


# In[304]:


full_df_cleared = full_df[(full_df['spec file'] != 1626813487) & (full_df['spec file'] != 1619429009)]


# In[305]:


full_df_cleared.describe()


# In[307]:


full_df_cleared[full_df.columns[:11].to_list() + [result_key]].info()


# In[311]:


import json


# In[316]:


new_experiments_folder = path.joinpath('individual optimization')
new_experiments_folder.mkdir(exist_ok=True)

optimization_config = {
    'max_iterations': 5,
    'target': {},
    'algorithm': {
        'name': 'smbo',
        'base_estimator': 'GP',
        'acq_func': 'LCB',
        'acq_func_kwargs': {'kappa': 0.1},
        'random_state': 42
    },
    'reference': -113.15,
    'batch_size': 1
}

i = 1
for result_key in results:
    experiment_folder = new_experiments_folder.joinpath(f'experiment {i}')
    experiment_folder.mkdir(exist_ok=True)
    
    optimization_config['target'] = {result_key: float('inf')}
    
    with open(experiment_folder.joinpath('optimization_config_exploitation.json'), 'w') as fobj:
        json.dump(optimization_config, fobj, indent=4)
    
#     full_df_cleared[full_df.columns[:11].to_list() + [result_key]].to_csv(experiment_folder.joinpath(f'result_table.csv'), index=False)
    i += 1


# In[276]:


full_df_cleared.iloc[:, -12:].describe()


# In[ ]:





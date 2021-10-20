"""
Script to plot the analysis of the novelty exploration.
"""

# pylint: skip-file

### IMPORTS
# stdlib
import argparse
from pathlib import Path

# data io
import pandas as pd

# plotting
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# analysis
import numpy as np
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split, GridSearchCV, cross_val_score
from sklearn.metrics import mean_squared_error

# misc
from tqdm import tqdm

### CONSTANTS
# Parameters for RF regressor optimization
RF_TUNED_PARAMS = [
    {
        'n_estimators': [500],
        'max_depth': [5],
        'min_samples_leaf': [1],
    }
]

### CLI ARGUMENTS
parser = argparse.ArgumentParser(
    description='Plotting the product analysis from novelty search'
)

parser.add_argument(
    '--data_path',
    help='path to the data table',
    type=str
)

parser.add_argument(
    '--output_dir',
    help='output directory to store plots',
    type=str
)

parser.add_argument(
    '--n_parameters',
    help='number of optimization parameters',
    type=int
)

parser.add_argument(
    '--n_results',
    help='number of resulting parameters',
    type=int
)

parser.add_argument(
    '--interactive',
    help='generate interactive plots using plotly',
    action='store_true'
)

parser.add_argument(
    '--features',
    help='perform feature analysis',
    action='store_true'
)

parser.add_argument(
    '--correlation',
    help='perform correlation analysis of the results',
    action='store_true'
)

args = parser.parse_args()

df = pd.read_csv(Path(args.data_path)).iloc[:-6, :]
output_dir = Path(args.output_dir)

### DATA ANALYSIS
# Slicing
X_full = df.iloc[:, :args.n_parameters]
Y_full = df.iloc[:, -args.n_results:]

# Scaling
x_s = StandardScaler().fit_transform(X_full)
y_s = StandardScaler().fit_transform(Y_full)

x_pca = PCA(2).fit_transform(x_s)

### PLOTTING
# matplotlib
print('Genering matplotlib images')
figures_path = output_dir.joinpath('Analysis plots')
figures_path.mkdir(parents=True, exist_ok=True)

i = 1
for result in tqdm(Y_full.columns):
    fig, ax = plt.subplots(figsize=(9, 7))

    img = ax.scatter(
        x_pca[:, 0],
        x_pca[:, 1],
        c=Y_full[result],
        label=result,
        s=80,
        alpha=.8
    )

    ax.set_title(result.split('_')[-1])

    fig.colorbar(img)

    fig.savefig(figures_path.joinpath(f'result {i}.png'), dpi=600)
    fig.savefig(figures_path.joinpath(f'result {i}.svg'))

    i += 1
    plt.close()
    # break

print('Images saved at {}'.format(figures_path.as_posix()))

# plotly
def gen_plotly_html():
    """Generate plotly img."""

    print('Generating plotly html image')

    # Subplot titles
    titles = [key.split('_')[-1] for key in Y_full.columns]

    # Highlight labels
    htls = ': %{}<br>'.join(X_full.columns) + ': %{}<br>'

    fig = make_subplots(
        rows=args.n_results,
        cols=1,
        shared_xaxes=True,
        shared_yaxes=False,
        subplot_titles=titles,
        vertical_spacing=0.01,
    )

    for y_i in range(y_s.shape[1]):
        fig.append_trace(
            go.Scatter(
                x=x_pca[:, 0],
                y=x_pca[:, 1],
                mode='markers',
                marker={
                    'size': 10,
                    'color': Y_full.to_numpy()[:, y_i] * 100,
                    'colorscale': 'Viridis',
                },
                customdata=X_full.to_numpy(),
                text=df['spec file'],
                hovertemplate='%{text} / %{marker.color:.2f}<br>' + htls.format(*[f'{{customdata[{i}]:.2f}}' for i in range(len(X_full.columns))])),
            col=1,
            row=y_i + 1,
        )

    fig.update_layout(
        width=350,
        height=args.n_results * 300,
        margin={
            'l': 10,
            'r': 10,
            'b': 10,
            't': 30
        },
        showlegend=False
    )

    fig.write_html(figures_path.joinpath('all results.html').as_posix())

def gen_correlation_plot():
    """Generate results correlation heatmap"""
    print('Generating correlation plot')

    fig, ax = plt.subplots(figsize=(15, 12))
    im = ax.imshow(Y_full.corr())

    # ticks
    ax.set_xticks(np.arange(len(Y_full.columns)))
    ax.set_yticks(np.arange(len(Y_full.columns)))

    # labels
    xlabels = [col[26:] for col in Y_full.columns]
    ylabels = [col[26:] for col in Y_full.columns]
    ax.set_xticklabels(xlabels, fontsize=20, rotation=45, rotation_mode='anchor', ha='right')
    ax.set_yticklabels(ylabels, fontsize=20)

    # annotations
    for j in range(len(xlabels)):
        for i in range(len(ylabels)):
            text = ax.text(j, i, np.around(Y_full.corr().to_numpy()[i][j], 2), fontsize=16, va='center', ha='center')

    ax.set_title('Result correlation', fontsize=28)

    fig.tight_layout()
    fig.savefig(figures_path.joinpath('results correlation.png'))
    fig.savefig(figures_path.joinpath('results correlation.svg'))

    plt.close()

def gen_features_plot():
    """Generate feature importances plot using RF regressor."""

    regressors = []
    feature_importances = []
    # Building regressors
    print('Building RF regressors')
    for y_i in tqdm(range(Y_full.shape[1])):
        X_train, X_test, y_train, y_test = train_test_split(x_s, y_s[:, y_i], test_size=0.3)
        rf = GridSearchCV(RandomForestRegressor(), param_grid=RF_TUNED_PARAMS)
        rf.fit(X_train, y_train)
        regressors.append(rf.best_estimator_)
        feature_importances.append(rf.best_estimator_.feature_importances_)

    # Plotting
    fig, ax = plt.subplots(figsize=(15,12))
    im = ax.imshow(feature_importances)

    # ticks
    ax.set_xticks(np.arange(len(X_full.columns)))
    ax.set_yticks(np.arange(len(Y_full.columns)))

    # labels
    xlabels = [col.split('-')[0] for col in X_full.columns]
    ylabels = [col.split('_')[-1] for col in Y_full.columns]
    ax.set_xticklabels(xlabels, fontsize=24, rotation=45, rotation_mode='anchor', ha='right')
    ax.set_yticklabels(ylabels, fontsize=24)

    # annotations
    for j in range(len(xlabels)):
        for i in range(len(ylabels)):
            text = ax.text(j, i, np.around(feature_importances[i][j], 2), fontsize=16, va='center', ha='center')

    ax.set_title('Feature importances', fontsize=28)
    fig.tight_layout()
    fig.savefig(figures_path.joinpath('feature importances.png'))
    fig.savefig(figures_path.joinpath('feature importances.svg'))

    plt.close()

if args.interactive:
    gen_plotly_html()

if args.features:
    gen_features_plot()

if args.correlation:
    gen_correlation_plot()

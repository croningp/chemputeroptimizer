from setuptools import setup, find_packages

setup(
    name="chemputeroptimizer",
    version="0.1.3",
    description="Package for running interactive chemical reaction optimization",
    author="Artem Leonov, Alex Hammer",
    author_email="artem.leonov@glasgow.ac.uk",
    packages=find_packages(),
    install_requires=[
        "xdl @ git+ssh://git@gitlab.com/croningroup/chemputer/xdl.git",
        "numpy",
        "scikit-learn==0.22.2.post1", # until resolved in scikit-optimize
        "scikit-optimize",
        "AnalyticalLabware @ git+ssh://git@gitlab.com/croningroup/chemputer/analyticallabware.git",
    ]
)

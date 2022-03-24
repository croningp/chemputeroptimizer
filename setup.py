from setuptools import setup, find_packages

setup(
    name="chemputeroptimizer",
    version="0.4.0",
    description="Package for running interactive chemical reaction optimization",
    author="Artem Leonov, Alex Hammer",
    author_email="artem.leonov@glasgow.ac.uk",
    packages=find_packages(),
    install_requires=[
        "xdl",
        "chemputerxdl",
        "chempiler",
        "numpy",
        "scikit-learn==0.22", # TODO remove when incompatibility problems are resolved between sklearn and skopt
        "scikit-optimize>=0.8",
        "pyDOE2",
        "AnalyticalLabware",
    ]
)

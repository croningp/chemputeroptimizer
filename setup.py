from setuptools import setup, find_packages

setup(
    name="chemputeroptimizer",
    version="0.4.3",
    description="Package for running interactive chemical reaction optimization",
    author="Artem Leonov, Alex Hammer",
    author_email="artem.leonov@glasgow.ac.uk",
    packages=find_packages(),
    install_requires=[
        "xdl",
        "chemputerxdl",
        "chempiler",
        "numpy",
        "scikit-learn",
        "scikit-optimize",
        "pyDOE2",
        "AnalyticalLabware",
    ]
)

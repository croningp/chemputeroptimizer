from setuptools import setup, find_packages

setup(
    name="optimizer",
    version="0.0.1",
    description="Package for running interactive chemical reaction optimization",
    packages=find_packages(),
    install_requires=[
        "XDL",
        "numpy",
    ]
)
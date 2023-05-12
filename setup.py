from setuptools import setup, find_packages

setup(
    name="dvc-matrix",
    version="0.0.1",
    packages=find_packages(),
    author="Gabriel Simmons",
    install_requires=["click", "pyyaml"],
    entry_points={
        "console_scripts": [
            "dvc-matrix = dvc_matrix.dvc_matrix:cli",
        ],
    },
)

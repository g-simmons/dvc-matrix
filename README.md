# DVC-Matrix

## Description

Translate parameter matrix specifications into DVC files. Run dvc stages over dense parameter grids.

## Installation

To install: 
```bash
git clone 
```

The available options are -f or --file to specify the path to the matrix file, -o or --output to specify the path to the output file, 

If no arguments are passed, the script will look for a file named dvc-matrix.yaml in the current directory and generate a new dvc.yaml file with the matrix expanded. If arguments are passed, the yamlgrid function will be called with the provided arguments and the resulting YAML will be printed to the console.

Here is an example usage to generate a new dvc.yaml file:
yaml

Here is an example usage to print the YAML output to the console:
python dvc_matrix.py --arg1=value1 --arg2=value2 
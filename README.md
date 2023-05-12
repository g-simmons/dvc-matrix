# DVC-Matrix

## Description

Translate parameter matrix specifications into DVC files. Run dvc stages over dense parameter grids.

An interim solution for this [DVC feature request](https://github.com/iterative/dvc/issues/5172a)

## Installation

To install: 
```bash
git clone https://github.com/g-simmons/dvc-matrix.git
cd dvc-matrix
pip install .
```

## Usage

### Convert dvc-matrix files to dvcfiles
The available options are `-f` or `--file` to specify the path to the dvc-matrix file, and `-o` or `--output` to specify the path to the output `dvc.yaml` file.


If no arguments are passed, the script will look for a file named dvc-matrix.yaml in the current directory and generate a new dvc.yaml file with the matrix expanded. If other arguments are passed, the yamlgrid function will be called with the provided arguments and the resulting YAML will be printed to the console.

Here is an example usage to convert a dvc-matrix file to a dvc.yaml file:

```bash
dvc-matrix -f dvc-matrix.yaml -o dvc.yaml
```

Note that if your dvc-matrix file is is the same directory as your dvc.yaml file, you can omit the `-f` and `-o` arguments.

```bash
dvc-matrix
```

### Create parameter grids from the command line

Here is an example usage to print the YAML output to the console:

```bash
dvc-matrix --lr=[0.0001,0.1] --epochs=[5,10,100]
```

Results:
```yaml
- epochs: '5'
  lr: '0.0001'
- epochs: '10'
  lr: '0.0001'
- epochs: '100'
  lr: '0.0001'
- epochs: '5'
  lr: '0.1'
- epochs: '10'
  lr: '0.1'
- epochs: '100'
  lr: '0.1'
```


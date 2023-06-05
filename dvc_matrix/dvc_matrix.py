import yaml
from itertools import product, starmap
from collections import namedtuple
import click
import dvc.api
import os
import json as jsonlib
import re
from rich.console import Console
from rich.table import Table
from prompt_toolkit import prompt
from prompt_toolkit.completion import FuzzyWordCompleter


def named_product(**items):
    items = {name: [str(item) for item in value] for name, value in items.items()}
    Product = namedtuple("Product", items.keys())
    return [x._asdict() for x in starmap(Product, product(*items.values()))]


def yamlgrid(**items):
    return yaml.dump(named_product(**items), default_flow_style=False)


def unformat(template, formatted):
    keys = re.findall(r"\${item.([a-z_-]+)}", template)
    pattern = re.sub(r"\${item.([a-z_-]+)}", r"([^/]+)", template)
    pattern = re.compile(pattern)
    match = pattern.search(formatted)
    values = match.groups()
    result = dict(zip(keys, values))

    return result


@click.group()
def cli():
    pass


def print_stage_list(stage_list):
    if len(stage_list) == 0:
        return
    console = Console()

    table = Table(show_header=True, header_style="bold magenta",show_lines=False,box=None)
    for key in stage_list[0].keys():
        table.add_column(key)
    for stage in stage_list:
        table.add_row(
            *[
                str("[green]" + value + "[/green]" if value == "ok" else value)
                for value in stage.values()
            ]
        )
    console.print(table)


@cli.command(
    name="run",
)
@click.pass_context
def run(ctx):
    dvcyaml, dvcmatrix, dvclock = load_dvc_files()

    stage_list = dvcmatrix["stages"]

    completer = FuzzyWordCompleter(stage_list)
    stage_name = prompt(
        "Select stage to run: ",
        completer=completer,
    )

    stage_list = get_stage_list(dvcyaml, dvcmatrix, dvclock, stage_name)
    print_stage_list(stage_list)

    # select from the stage list using fuzzy search

    def get_stage_key(stage):
        return " | ".join([f"{key}: {value}" for key, value in stage.items()])

    meta_dict = {get_stage_key(stage): str(stage) for stage in stage_list}

    # completer = FuzzyWordCompleter(words=meta_dict.keys(), meta_dict=meta_dict)
    completer = FuzzyWordCompleter(
        # words=[s["cmd"] for s in stage_list],
        words = [s["stage_name"] for s in stage_list],
        meta_dict={s["stage_name"]: get_stage_key(s) for s in stage_list},
    )

    stage_name = prompt(
        "Select stage to run: ",
        completer=completer,
    )
    # paste the selected command into the terminal and exit, so that the user can run it
    print([s["cmd"] for s in stage_list if s["stage_name"] == stage_name][0])


def get_status():
    # capture the output of "dvc status --json" CLI command
    status = os.popen("dvc status --json").read()

    status = os.popen("dvc status --json").read()
    status = jsonlib.loads(status)
    return status


# get the contents of dvc.lock
def get_lock_stages(stage_name, lock):
    lock_stages = {
        lock_name: lock_stage
        for lock_name, lock_stage in lock["stages"].items()
        if stage_name in lock_name
    }
    return lock_stages


def load_dvc_files():
    dvcyaml = yaml.safe_load(open("dvc.yaml", "r"))
    matrix = yaml.safe_load(open("dvc-matrix.yaml", "r"))
    lock = yaml.safe_load(open("dvc.lock", "r"))
    return dvcyaml, matrix, lock


def get_stages():
    stages_output = os.popen("dvc stage list --all").read()
    stages_output = stages_output.split("\n")
    stages_output = [s.split(" ") for s in stages_output if s]
    stages = {s[0]: s[3] for s in stages_output}
    return stages

#     print(f"Stage {yaml_name} not found in dvc.lock")
#     params = matrix["stages"][yaml_name]["foreach-matrix"]
#     param_combinations = named_product(**params)
#     stage_list = []
#     for i, combination in enumerate(param_combinations):
#         stage_dict = {}
#         stage_dict["stage_name"] = f"{yaml_name}@{i}"
#         stage_dict.update(combination)
#         stage_dict["status"] = "not run"
#         stage_dict["cmd"] = dvcyaml["stages"][yaml_name]["do"]["cmd"].replace("\\", "\\\n")
#         for key, val in combination.items():
#             stage_dict["cmd"] = stage_dict["cmd"].replace(
#                 f"${{item.{key}}}", val
#             )

#         stage_list.append(stage_dict)

#     stage_lists.append(stage_list)

def get_stage_list_from_matrix(stage_name, matrix):
    params = matrix["stages"][stage_name]["foreach-matrix"]
    global_vars = {}
    for var in matrix.get("vars", []):
        global_vars.update(var)
    
    vars = matrix["stages"][stage_name].get("vars", {})
    param_combinations = named_product(**params)
    stage_list = []
    for i, combination in enumerate(param_combinations):
        stage_dict = {}
        stage_dict["stage_name"] = f"{stage_name}@{i}"
        stage_dict.update(combination)
        stage_dict["status"] = "not run"
        if "do" in matrix["stages"][stage_name]:
            command_template = matrix["stages"][stage_name]["do"]["cmd"].replace("$","").replace("item.","").replace("\\", "\\\n\t")
            stage_dict["cmd"] = command_template.format(**combination, **vars, **global_vars)

        stage_list.append(stage_dict)

    return stage_list


def get_stage_list_from_lock(lock_stages, yaml, status):
    stage_list = []
    for stagename, lock_stage in lock_stages.items():
        formatted_command = lock_stage["cmd"]
        dvc_stage = yaml["stages"][stagename.split("@")[0]]
        if "do" not in dvc_stage:
            print(f"Stage {stagename} has no do section")
            continue
        command_template = dvc_stage["do"]["cmd"]
        params = unformat(command_template, formatted_command)
        stage_dict = {}
        stage_dict.update(params)
        stage_dict["stage_name"] = stagename
        stage_dict["cmd"] = formatted_command

        try:
            status[stagename]
            stage_dict["status"] = "changed"
        except KeyError:
            stage_dict["status"] = "ok"

        stage_list.append(stage_dict)

    return stage_list


def get_stage_list(yaml, matrix, lock, stage_name):
    lock_stages = get_lock_stages(stage_name, lock)
    status = get_status()

    if len(lock_stages) == 0:
        return get_stage_list_from_matrix(stage_name, matrix)
    else:
        return get_stage_list_from_lock(lock_stages, yaml, status)


@cli.command(
    name="status",
)
@click.option("--json", is_flag=True, help="Print status list as JSON")
@click.pass_context
def status(ctx, json):
    """
    This function displays the status of each combination of parameters in a foreach-matrix, using the output from dvc status CLI.
    """
    status = get_status()

    dvcyaml, matrix, lock = load_dvc_files()

    stage_lists = []
    # for stagename, lock_stage in lock["stages"].items():
    for yaml_name in dvcyaml["stages"]:
        stage_list = get_stage_list(dvcyaml, matrix, lock, yaml_name)
        if stage_list:
            stage_lists.append(stage_list)

    if json:
        print(jsonlib.dumps(stage_lists, indent=4))
    else:
        for stage_list in stage_lists:
            print_stage_list(stage_list)


@cli.command(
    name="update",
    context_settings=dict(
        ignore_unknown_options=True,
        allow_extra_args=True,
    ),
)
@click.option("-f", "--file", type=click.Path(exists=True), help="Path to matrix file")
@click.option("-o", "--output", type=click.Path(), help="Path to output file")
@click.pass_context
def update(ctx, file, output):
    if not ctx.args:
        if not file:
            file = "dvc-matrix.yaml"
        try:
            dvcyaml = yaml.safe_load(open(file, "r"))
        except FileNotFoundError:
            print(f"No matrix file found at {file}")
            return

        for _, stage in dvcyaml["stages"].items():
            if "foreach-matrix" in stage:
                args = stage["foreach-matrix"]
                stage["foreach"] = named_product(**args)
                del stage["foreach-matrix"]

        with open(output or "dvc.yaml", "w") as f:
            yaml.dump(
                dvcyaml,
                f,
                default_flow_style=False,
            )

        args = {
            arg.split("=")[0].replace("--", ""): arg.split("=")[1].split(",")
            for arg in ctx.args
        }
        if args:
            print(yamlgrid(**args))


if __name__ == "__main__":
    cli()

        # lock_stages = {
        #     lock_name: lock_stage
        #     for lock_name, lock_stage in lock["stages"].items()
        #     if yaml_name in lock_name
        # }

        # if len(lock_stages) == 0:


        # else:
        #     stage_list = []
        #     for stagename, lock_stage in lock_stages.items():
        #         dvc_stage = dvcyaml["stages"][stagename.split("@")[0]]
        #         if "do" not in dvc_stage:
        #             print(f"Stage {stagename} has no do section")
        #             continue

        #         # get stage parameters
        #         formatted_out = lock_stage["outs"][0]["path"]
        #         out_template = dvc_stage["do"]["outs"][0]
        #         params = unformat(out_template, formatted_out)

        #         stage_dict = {}
        #         stage_dict["stage_name"] = stagename
        #         stage_dict.update(params)

        #         if stagename not in status:
        #             stage_dict["status"] = "ok"
        #         elif "changed command" in status[stagename]:
        #             stage_dict["status"] = "changed command"
        #         else:
        #             stage_dict["status"] = ", ".join([key for key in ["changed outs", "changed deps"] if key in status[stagename]])

        #         stage_list.append(stage_dict)
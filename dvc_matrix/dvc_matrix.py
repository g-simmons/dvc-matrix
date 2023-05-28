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

    table = Table(show_header=True, header_style="bold magenta")
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
    name="status",
)
@click.option("--json", is_flag=True, help="Print status list as JSON")
@click.pass_context
def status(ctx, json):
    """
    This function displays the status of each combination of parameters in a foreach-matrix, using the output from dvc status CLI.
    """

    status = os.popen("dvc status --json").read()
    status = jsonlib.loads(status)

    dvcyaml = yaml.safe_load(open("dvc.yaml", "r"))
    matrix = yaml.safe_load(open("dvc-matrix.yaml", "r"))
    lock = yaml.safe_load(open("dvc.lock", "r"))

    stage_lists = []
    for yaml_name in dvcyaml["stages"]:

        lock_stages = {
            lock_name: lock_stage
            for lock_name, lock_stage in lock["stages"].items()
            if yaml_name in lock_name
        }

        if len(lock_stages) == 0:
            print(f"Stage {yaml_name} not found in dvc.lock")
            params = matrix["stages"][yaml_name]["foreach-matrix"]
            param_combinations = named_product(**params)
            stage_list = []
            for i, combination in enumerate(param_combinations):
                stage_dict = {}
                stage_dict["stage_name"] = f"{yaml_name}@{i}"
                stage_dict.update(combination)
                stage_dict["status"] = "not run"

                stage_list.append(stage_dict)

            stage_lists.append(stage_list)

        else:
            stage_list = []
            for stagename, lock_stage in lock_stages.items():
                dvc_stage = dvcyaml["stages"][stagename.split("@")[0]]
                if "do" not in dvc_stage:
                    print(f"Stage {stagename} has no do section")
                    continue

                # get stage parameters
                formatted_out = lock_stage["outs"][0]["path"]
                out_template = dvc_stage["do"]["outs"][0]
                params = unformat(out_template, formatted_out)

                stage_dict = {}
                stage_dict["stage_name"] = stagename
                stage_dict.update(params)

                if stagename not in status:
                    stage_dict["status"] = "ok"
                elif "changed command" in status[stagename]:
                    stage_dict["status"] = "changed command"
                else:
                    stage_dict["status"] = ", ".join([key for key in ["changed outs", "changed deps"] if key in status[stagename]])

                stage_list.append(stage_dict)

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

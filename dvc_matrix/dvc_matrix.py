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
    Product = namedtuple("Product", items.keys())
    return [x._asdict() for x in starmap(Product, product(*items.values()))]


def yamlgrid(**items):
    return yaml.dump(named_product(**items), default_flow_style=False)


def unformat(template, formatted):
    keys = re.findall(r"\${item.([a-z]+)}", template)
    pattern = re.sub(r"\${item.([a-z]+)}", r"([^/]+)", template)
    pattern = re.compile(pattern)
    match = pattern.search(formatted)
    values = match.groups()
    result = dict(zip(keys, values))

    return result


@click.group()
def cli():
    pass


def print_stage_list(stage_list):
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
    # capture the output of "dvc status --json" CLI command
    status = os.popen("dvc status --json").read()

    # parse the output as JSON
    status = jsonlib.loads(status)

    # capture the output of "dvc stage list --all" CLI command
    stages = os.popen("dvc stage list --all").read()

    # parse the output: each line has "<stage_name> Outputs <output_path>"

    # split the output by lines
    stages = stages.split("\n")

    stages = {s[0]: s[3] for s in [s.split(" ") for s in stages if s]}

    # get the contents of dvc.lock

    dvcyaml = yaml.safe_load(open("dvc.yaml", "r"))

    lock = yaml.safe_load(open("dvc.lock", "r"))
    stage_list = []
    for stagename, lock_stage in lock["stages"].items():
        # if stage and stage not in stagename:
        #     continue
        formatted_command = lock_stage["cmd"]
        command_template = dvcyaml["stages"][stagename.split("@")[0]]["do"]["cmd"]
        params = unformat(command_template, formatted_command)
        stage_dict = {}
        stage_dict["stage_name"] = stagename
        stage_dict.update(params)
        try:
            # stage_dict["status"] = status[stagename][0]["changed_outs"]
            status[stagename]
            stage_dict["status"] = "changed"
        except KeyError:
            stage_dict["status"] = "ok"

        stage_list.append(stage_dict)

    # Print stage_list as a nicely-formatted table

    if json:
        print(jsonlib.dumps(stage_list, indent=4))
    else:
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

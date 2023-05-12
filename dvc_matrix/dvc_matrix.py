import yaml
from itertools import product, starmap
from collections import namedtuple
import click


def named_product(**items):
    Product = namedtuple("Product", items.keys())
    return [x._asdict() for x in starmap(Product, product(*items.values()))]


def yamlgrid(**items):
    return yaml.dump(named_product(**items), default_flow_style=False)


@click.command(
    name="yamlgrid",
    context_settings=dict(
        ignore_unknown_options=True,
        allow_extra_args=True,
    ),
)
@click.option("-f", "--file", type=click.Path(exists=True), help="Path to matrix file")
@click.option("-o", "--output", type=click.Path(), help="Path to output file")
@click.pass_context
def cli(ctx, file, output):
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
            yaml.dump(dvcyaml, f, default_flow_style=False)
    else:
        args = {
            arg.split("=")[0].replace("--", ""): arg.split("=")[1].split(",")
            for arg in ctx.args
        }
        if args:
            print(yamlgrid(**args))


if __name__ == "__main__":
    cli()

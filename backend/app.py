"""CDK entry point for Axiom's backend infrastructure."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import aws_cdk as cdk

from stacks.backend_stack import AxiomBackendStack
from stacks.web_stack import AxiomWebStack

_ROOT = Path(__file__).parent


def _stage_shared_layer() -> None:
    """Copy axiom/ into layer/python/axiom and install its runtime deps.

    A Lambda layer for Python needs a `python/` directory at its zip root.
    axiom/ itself is pure Python, so a plain copy is enough for it. It also
    imports sympy, which isn't part of the Lambda runtime by default —
    sympy (and its one dependency, mpmath) are pure Python too, with no
    compiled extensions, so a plain `pip install --target` works without
    needing CDK's Docker-based cross-platform asset bundling.
    """
    sys.path.insert(0, str(_ROOT))
    from scripts.build_worked_examples import build as build_worked_examples

    build_worked_examples()  # regenerate axiom/data/worked_examples.json from the reviewed YAML

    layer_python = _ROOT / "layer" / "python"
    if layer_python.exists():
        shutil.rmtree(layer_python)
    layer_python.mkdir(parents=True, exist_ok=True)

    shutil.copytree(_ROOT / "axiom", layer_python / "axiom", ignore=shutil.ignore_patterns("__pycache__"))
    # `uv pip install`, not plain pip — a uv-managed venv has no pip module
    # of its own, and uv already resolves/downloads sympy for the project.
    subprocess.run(
        ["uv", "pip", "install", "--target", str(layer_python), "sympy"],
        check=True,
        capture_output=True,
    )


_stage_shared_layer()

app = cdk.App()

env = cdk.Environment(
    account=os.environ.get("CDK_DEFAULT_ACCOUNT"),
    region=os.environ.get("CDK_DEFAULT_REGION", "eu-west-1"),
)

AxiomBackendStack(app, "AxiomBackendStack", env=env)
AxiomWebStack(app, "AxiomWebStack", env=env)

app.synth()

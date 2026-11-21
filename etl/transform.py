"""Transform step: compose the staging and marts layers.

The cleaning logic now lives in ``etl.staging`` (1:1 cleaned sources) and the
dimensional modelling in ``etl.marts`` (star schema). This module keeps a
single convenient entry point, ``build_star_schema``, used by the pipeline
and the tests.
"""
from __future__ import annotations

import pandas as pd

from etl.marts import build_marts
from etl.staging import build_staging


def build_star_schema(raw: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """Raw tables -> staging -> marts (dimension + fact tables)."""
    staging = build_staging(raw)
    return build_marts(staging)

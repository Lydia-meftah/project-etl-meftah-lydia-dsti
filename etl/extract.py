"""Extract step: read raw CSVs into pandas DataFrames.

The extract step deliberately does **no** business logic. Its only job is
to load each raw source file into memory exactly as it is, so that the
transform step is the single place where cleaning rules live. This
separation is what makes each step independently testable.
"""
from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from etl.config import RAW_DIR, SOURCE_FILES

logger = logging.getLogger(__name__)


def extract_table(name: str, raw_dir: Path = RAW_DIR) -> pd.DataFrame:
    """Load one raw source table by its logical name.

    Parameters
    ----------
    name:
        Logical table name, one of the keys in ``SOURCE_FILES``.
    raw_dir:
        Directory holding the raw CSVs (overridable for tests).
    """
    if name not in SOURCE_FILES:
        raise KeyError(f"Unknown source table '{name}'. Known: {list(SOURCE_FILES)}")

    path = raw_dir / SOURCE_FILES[name]
    if not path.exists():
        raise FileNotFoundError(
            f"Raw file missing: {path}. Download the Olist dataset into {raw_dir} "
            "(see README)."
        )

    df = pd.read_csv(path)
    logger.info("Extracted %-22s %7d rows x %2d cols", name, len(df), df.shape[1])
    return df


def extract_all(raw_dir: Path = RAW_DIR) -> dict[str, pd.DataFrame]:
    """Load every configured source table into a dict keyed by logical name."""
    return {name: extract_table(name, raw_dir) for name in SOURCE_FILES}

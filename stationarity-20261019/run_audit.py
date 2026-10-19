"""Use the retained launcher/parser with an isolated calculation root."""

import importlib.util
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
driver = next(path for path in (
    ROOT.parent / "campaign.py",
    ROOT.parent / "validation-20261018/campaign.py",
    ROOT.parent / "cp2k-ot-metals-data/validation-20261018/campaign.py",
) if path.exists())
spec = importlib.util.spec_from_file_location("metal_campaign", driver)
campaign = importlib.util.module_from_spec(spec)
spec.loader.exec_module(campaign)
campaign.ROOT = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else ROOT
campaign.run(sys.argv[1], 1, None, 2, 1800, 4)

from __future__ import annotations

import json
from pathlib import Path


PLANNER_BUNDLES_PATH = Path(__file__).resolve().parent.parent / "config" / "planner_bundles.json"

EMPTY_CATALOG = {
    "campaignBundles": [],
    "adSetBundles": [],
    "audiencePresets": [],
    "datasetPresets": [],
    "budgetPresets": [],
    "placementPresets": [],
}


def load_planner_bundles(path=PLANNER_BUNDLES_PATH):
    planner_path = Path(path)
    if not planner_path.exists():
        return dict(EMPTY_CATALOG)
    return json.loads(planner_path.read_text(encoding="utf-8"))


def save_planner_bundles(catalog, path=PLANNER_BUNDLES_PATH):
    planner_path = Path(path)
    planner_path.parent.mkdir(parents=True, exist_ok=True)
    planner_path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")
    return planner_path


def planner_campaign_bundles(path=PLANNER_BUNDLES_PATH):
    return load_planner_bundles(path).get("campaignBundles", [])


def planner_adset_bundles(campaign_bundle_code=None, path=PLANNER_BUNDLES_PATH):
    bundles = load_planner_bundles(path).get("adSetBundles", [])
    if not campaign_bundle_code:
        return bundles
    return [bundle for bundle in bundles if bundle.get("campaignBundleCode") == campaign_bundle_code]


def planner_audience_presets(campaign_bundle_code=None, path=PLANNER_BUNDLES_PATH):
    catalog = load_planner_bundles(path)
    presets = catalog.get("audiencePresets", [])
    if not campaign_bundle_code:
        return presets
    campaign = next(
        (item for item in catalog.get("campaignBundles", []) if item.get("code") == campaign_bundle_code),
        None,
    )
    if not campaign:
        return []
    allowed_codes = set(campaign.get("allowedAudiencePresetCodes", []))
    return [preset for preset in presets if preset.get("code") in allowed_codes]

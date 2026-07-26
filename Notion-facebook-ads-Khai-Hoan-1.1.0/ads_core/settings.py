from pathlib import Path


NOTION_VERSION = "2022-06-28"
NOTION_DATA_SOURCE_VERSION = "2025-09-03"
APP_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SAMPLE_CSV = str(APP_ROOT / "sample" / "facebook_ads_template.csv")
DEFAULT_PARENT_PAGE_ID = ""
DEFAULT_DATA_SOURCE_ID = ""
STATE_FILE = ".sync_state.json"

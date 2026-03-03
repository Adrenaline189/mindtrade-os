import json
from pathlib import Path
from bot.config_runtime import RUNTIME_CONFIG

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_FILE = ROOT / 'data' / 'runtime_config.json'


def save_runtime_config() -> None:
    RUNTIME_FILE.parent.mkdir(parents=True, exist_ok=True)
    RUNTIME_FILE.write_text(json.dumps(RUNTIME_CONFIG, indent=2, ensure_ascii=False))


def load_runtime_config() -> None:
    if not RUNTIME_FILE.exists():
        return
    try:
        data = json.loads(RUNTIME_FILE.read_text())
    except Exception:
        return
    if not isinstance(data, dict):
        return
    # only update known keys to avoid accidental schema drift
    for k in list(RUNTIME_CONFIG.keys()):
        if k in data:
            RUNTIME_CONFIG[k] = data[k]

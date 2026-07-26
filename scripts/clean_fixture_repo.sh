set -e
cd "$(dirname "$0")/.."

rm -rf repos/fixture
rm -f data/logs/run_fixture.jsonl data/logs/fixture_files.json

python3 - << 'PYEOF'
import json
from pathlib import Path

manifest_path = Path("data/test_manifest.json")
manifest = json.loads(manifest_path.read_text())
manifest["repos"] = [r for r in manifest["repos"] if r["name"] != "fixture"]
manifest_path.write_text(json.dumps(manifest, indent=2))
print("removed 'fixture' from data/test_manifest.json")
PYEOF

echo "fixture repo removed"
echo "note: any tickets already created for 'fixture' are still in whatever backend was configured (data/issueloop.db by default) — delete manually if you want a clean slate"
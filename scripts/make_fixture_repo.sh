set -e
cd "$(dirname "$0")/.."

mkdir -p repos/fixture
cd repos/fixture
git init -q -b main 2>/dev/null || (git init -q && git checkout -q -b main)

cat > calc.py << 'PYEOF'
def add(a, b):
    return a - b  # bug: should be +
PYEOF

cat > test_calc.py << 'PYEOF'
from calc import add

def test_add():
    assert add(2, 3) == 5
PYEOF

git add -A
git -c user.email="fixture@issueloop.local" -c user.name="issueloop-fixture" commit -q -m "initial fixture"
cd - > /dev/null

python3 - << 'PYEOF'
import json
from pathlib import Path

manifest_path = Path("data/test_manifest.json")
manifest = json.loads(manifest_path.read_text())
manifest["repos"] = [r for r in manifest["repos"] if r["name"] != "fixture"]
manifest["repos"].append({
    "name": "fixture",
    "url": "local",
    "local_path": "./repos/fixture",
    "language": "python",
    "framework": "none",
    "default_branch": "main",
    "test_types": [
        {
            "id": "unit_tests",
            "description": "one test, one intentional bug",
            "command": "python3 -m pytest test_calc.py -q",
            "priority": 1,
            "blocking": True,
        }
    ],
})
manifest_path.write_text(json.dumps(manifest, indent=2))
print("registered 'fixture' in data/test_manifest.json")
PYEOF

echo "fixture repo ready at repos/fixture"
echo "next: python3 -m pip install pytest   (needed inside the fixture repo's test command)"
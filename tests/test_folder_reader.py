from pathlib import Path
from issueloop import folder_reader

def test_write_inventory_persists_file(tmp_path):
    repo = tmp_path / "some_repo"
    repo.mkdir()
    (repo / "a.py").write_text("print('hi')\n")

    out_file = folder_reader.write_inventory(repo)
    try:
        assert out_file.exists()
        assert out_file.name == "some_repo_files.json"

        import json
        inventory = json.loads(out_file.read_text())
        assert inventory["file_count"] == 1
        assert inventory["files"][0]["path"] == "a.py"
    finally:
        out_file.unlink(missing_ok=True)
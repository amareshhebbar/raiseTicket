import json
from issueloop import test_runner

def _write_fixture_manifest(tmp_path, monkeypatch):
    repo_dir = tmp_path / "repos" / "fixture"
    repo_dir.mkdir(parents=True)

    manifest = {
        "repos": [{
            "name": "fixture",
            "local_path": "repos/fixture",
            "default_branch": "main",
            "test_types": [
                {"id": "passing", "command": "python3 -c \"exit(0)\"", "priority": 1, "blocking": True},
                {"id": "failing", "command": "python3 -c \"exit(1)\"", "priority": 2, "blocking": True},
            ],
        }]
    }
    manifest_path = tmp_path / "data" / "test_manifest.json"
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_text(json.dumps(manifest))

    monkeypatch.setattr(test_runner, "ROOT", tmp_path)
    monkeypatch.setattr(test_runner, "MANIFEST_PATH", manifest_path)


def test_run_single_test_isolates_passing(tmp_path, monkeypatch):
    _write_fixture_manifest(tmp_path, monkeypatch)
    result = test_runner.run_single_test("fixture", "passing")
    assert result["exit_code"] == 0
    assert result["test_id"] == "passing"


def test_run_single_test_isolates_failing(tmp_path, monkeypatch):
    _write_fixture_manifest(tmp_path, monkeypatch)
    result = test_runner.run_single_test("fixture", "failing")
    assert result["exit_code"] != 0
    assert result["test_id"] == "failing"


def test_run_single_test_unknown_id_raises(tmp_path, monkeypatch):
    _write_fixture_manifest(tmp_path, monkeypatch)
    try:
        test_runner.run_single_test("fixture", "does_not_exist")
        assert False, "expected ValueError"
    except ValueError:
        pass
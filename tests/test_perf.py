import json

from buildcoach.cli import main


def test_demo_stays_inside_the_time_budget(tmp_path, capsys):
    assert main(["demo", "--output", str(tmp_path)]) == 0
    metric = json.loads((tmp_path / "metric.json").read_text(encoding="utf-8"))
    assert metric["occluded_completions"] == 0
    assert metric["contradictory_completions"] == 0
    assert metric["clear_correct_completions"] == 3
    # A laptop check of these 14 sessions should finish quickly. Five seconds
    # leaves room for a slower CI runner without hiding a hang.
    assert metric["elapsed_seconds"] < 5.0
    capsys.readouterr()

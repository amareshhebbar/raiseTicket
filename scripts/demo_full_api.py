import issueloop
from issueloop import llm as _llm

issueloop.use(database="local")


def _stub_chat(prompt, system=""):
    # stand-in for a real LLM call (ollama/anthropic/openai) so this demo
    # runs standalone; on your machine with ollama running, delete this
    # monkeypatch and issueloop.create_tickets() will call the real model
    if "ZeroDivisionError" in prompt:
        return '[{"summary": "divide() does not guard against a zero denominator"}]'
    if "IndexError" in prompt:
        return '[{"summary": "get_item() does not bounds-check the index"}]'
    if "JSONDecodeError" in prompt:
        return '[{"summary": "parse_config() does not handle malformed JSON input"}]'
    if "ValueError" in prompt:
        return '[{"summary": "to_int() does not handle non-numeric strings"}]'
    if "TypeError" in prompt:
        return '[{"summary": "concat() does not handle mixed str/int arguments"}]'
    return '[{"summary": "add() has a sign error, returns a - b instead of a + b"}]'


_llm.chat = _stub_chat

print("=== list_repos ===")
print(issueloop.list_repos())

print("\n=== health_check ===")
print(issueloop.health_check())

print("\n=== scan_repo ===")
inventory = issueloop.scan_repo("/home/gvamaresh/delete_this_2/buggy_project")
print(f"{inventory['file_count']} files, {inventory['language_breakdown']}")

print("\n=== run_tests ===")
for r in issueloop.run_tests("buggy"):
    status = "OK" if r["exit_code"] == 0 else "FAIL"
    print(f"[{status}] {r['test_id']}")

print("\n=== create_tickets ===")
created = issueloop.create_tickets("buggy")
print(f"created {len(created)} ticket(s)")
for t in created:
    print(f"  [{t['priority']}] {t['error_summary']}")

print("\n=== get_all_bugs ===")
for b in issueloop.get_all_bugs("buggy"):
    print(f"  {b['id'][:8]} [{b['status']}] {b['error_summary']}")

print("\n=== get_bug_count / get_bug_count_by_status ===")
print("total:", issueloop.get_bug_count("buggy"))
print("by status:", issueloop.get_bug_count_by_status("buggy"))

print("\n=== get_bugs_by_priority(blocking) ===")
for b in issueloop.get_bugs_by_priority("blocking", "buggy"):
    print(f"  {b['error_summary']}")

print("\n=== search_bugs('zero') ===")
for b in issueloop.search_bugs("zero", "buggy"):
    print(f"  {b['error_summary']}")

print("\n=== get_oldest_bug / get_newest_bug ===")
print("oldest:", issueloop.get_oldest_bug("buggy")["error_summary"])
print("newest:", issueloop.get_newest_bug("buggy")["error_summary"])

print("\n=== dispense + lifecycle (top_error -> resolve/fail/escalate/retry) ===")
first = issueloop.get_top_error("buggy")
print("dispensed:", first["error_summary"], "-> status:", first["status"])
issueloop.resolve(first["id"])
print("resolved:", issueloop.get_bug(first["id"])["status"])

second = issueloop.get_top_error("buggy")
print("dispensed:", second["error_summary"])
issueloop.fail(second["id"])
retried = issueloop.retry_bug(second["id"])
print("retried, attempts now:", issueloop.get_bug_attempts(second["id"]), "status:", retried["status"])

third = issueloop.get_top_error("buggy")
escalated = issueloop.escalate(third["id"], reason="needs a human to decide the right bounds-check behavior")
print("escalated:", escalated["status"], "-", escalated["escalation_summary"])

remaining = issueloop.get_unresolved_bugs("buggy")
print(f"\nbulk_resolve remaining {len(remaining)} unresolved bug(s)...")
issueloop.bulk_resolve([b["id"] for b in remaining])
print("resolved bugs now:", len(issueloop.get_resolved_bugs("buggy")))
print("needing human now:", len(issueloop.get_bugs_needing_human("buggy")))

print("\n=== get_database_stats ===")
print(issueloop.get_database_stats("buggy"))

print("\n=== export_bugs ===")
path = issueloop.export_bugs("buggy")
print("exported to:", path)

print("\n=== get_crash_log ===")
print(f"{len(issueloop.get_crash_log())} crash entries")

print("\n=== get_notification_config ===")
print(issueloop.get_notification_config())

print("\n=== live monitoring: watch_process ===")
import time
handle = issueloop.watch_process("buggy_live", "python3 -m pytest test_calc.py -q", cwd="/home/gvamaresh/delete_this_2/buggy_project", debounce_seconds=1.5)
print("active watchers:", issueloop.list_active_watchers())
time.sleep(3)
issueloop.stop_watch(handle)
print("active watchers after stop:", issueloop.list_active_watchers())

print("\n=== get_llm_provider_status ===")
print(issueloop.get_llm_provider_status())

print("\n=== get_token_consumption (stubbed chat doesn't record real usage) ===")
print(issueloop.get_token_consumption())
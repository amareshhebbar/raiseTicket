
import argparse
import json
import sys

import issueloop
from . import check_environment


def main():
    parser = argparse.ArgumentParser(prog="issueloop")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("check-env", help="verify ollama, models, and Supabase env are ready")

    p_scan = sub.add_parser("scan", help="build a file inventory for a repo")
    p_scan.add_argument("repo_path")

    p_test = sub.add_parser("test", help="run test_manifest.json commands for a repo, write log cache")
    p_test.add_argument("repo_name")

    p_tickets = sub.add_parser("tickets", help="create tickets from failing log entries")
    p_tickets.add_argument("repo_name")

    p_next = sub.add_parser("next", help="dispense the next ticket for a repo, one at a time")
    p_next.add_argument("repo_name")

    p_cleanup = sub.add_parser("cleanup", help="delete done/failed tickets older than N days")
    p_cleanup.add_argument("--days", type=int, default=None)
    p_cleanup.add_argument("--repo", default=None)

    p_serve = sub.add_parser("serve", help="start the local HTTP bridge for non-Python callers")
    p_serve.add_argument("--port", type=int, default=8787)

    args = parser.parse_args()

    if args.command == "check-env":
        return check_environment.main()

    if args.command == "scan":
        inventory = issueloop.scan_repo(args.repo_path)
        print(f"scanned {inventory['file_count']} files — {inventory['language_breakdown']}")
        return 0

    if args.command == "test":
        for r in issueloop.run_tests(args.repo_name):
            status = "OK" if r["exit_code"] == 0 else "FAIL"
            print(f"[{status}] {r['test_id']} (exit {r['exit_code']})")
        return 0

    if args.command == "tickets":
        created = issueloop.create_tickets(args.repo_name)
        print(f"created {len(created)} ticket(s)")
        for t in created:
            print(f"  [{t['priority']}] {t['error_summary']}")
        return 0

    if args.command == "next":
        ticket = issueloop.get_top_error(args.repo_name)
        if ticket is None:
            print("no pending tickets")
            return 0
        print(json.dumps(ticket, indent=2))
        return 0

    if args.command == "cleanup":
        removed = issueloop.cleanup(older_than_days=args.days, repo=args.repo)
        print(f"removed {removed} old ticket(s)")
        return 0

    if args.command == "serve":
        from . import server
        server.serve(port=args.port)
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
import json
import sys
from raiseticket.utils import llm
from raiseticket.logs import log_reader
from raiseticket.state.agent_state import TicketPriority
from . import ticket_store

SPLIT_PROMPT = """You are triaging a failed command's output. Decide if it \
represents ONE error or SEVERAL independent, unrelated errors bundled \
together. Respond ONLY with a JSON list, one object per independent \
error, each with a single field "summary" (one sentence, plain English, \
no stack trace dump, no markdown).

Command: {command}
Exit code: {exit_code}
Stderr (tail): {stderr_tail}
"""

def _split_errors(entry:dict):
    prommpt=SPLIT_PROMPT.format(
        command-entry["command"], exit_code=entry["exit_code"], stderr_tail=entry["stderr_tail"]
    )
    raw=llm.chat(prommpt)
    try: 
        parsed=json.loads(raw)
        summaries=[items["summary"] for item in parsed]
        if summaries:
            return summaries
    except(json.JSONDecodeError, KeyError, TypeError):
        pass
    return [raw.strip()[:500]]

def create_ticket_for_repo(repo_name: str):
    created=[]
    for entry in log_reader.read_erros(repo_name):
        summaries=_split_errors(entry)
        priority=TicketPriority.BLOCKING if entry["blocking"] else TicketPriority.NORMAL
        for summary in summaries:
            ticket=ticket_store.new_ticket(
                repo=repo_name,
                error_summary=summary,
                raw_log_ref=f"run_{repo_name}.jsonl:{entry['test_id']}:{entry['timestammp']}",
                priority=priority,
                command=entry["command"],
                test_id=entry["test_id"]
            )
            ticket_store.create_ticket(ticket)
            created.append(ticket)
    return created
        
if __name__=="__main__": 
    if len(sys.argv)!=2:
        print("RAISETICKET:: usage: python src/ticket_creator.py <repo_name>")
        sys.exit(1)
    tickets=create_ticket_for_repo(sys.argv[1])
    print(f"RAISETICKET:: Created {len(tickets)} ticket(s)")
    for t in tickets:
        print(f"RAISETICKET:: [{t.priority.value}] {t.error_summary}")
        
# issueloop

JS/TS client for [IssueLoop](https://github.com/onenot8/issueLoop)'s
local HTTP bridge. This package does not run IssueLoop — it talks to a
Python `issueloop serve` process already running, from Node.js,
TypeScript, React, Vue, or React Native.

## Install

    npm install issueloop

## Start the Python side first

    pip install issueloop
    issueloop serve --port 8787

## Use

    const { IssueLoop } = require("issueloop");
    // or: import { IssueLoop } from "issueloop";

    const client = new IssueLoop({ baseUrl: "http://127.0.0.1:8787" });

    const ticket = await client.getTopError("myrepo");
    if (ticket) {
      await client.resolve(ticket.id);
    }

## Full API

Five dedicated methods (`health`, `getTopError`, `getAllErrors`,
`resolve`, `fail`) plus 44 more reachable through the same client,
covering the full Python API — bug query, ticket lifecycle, fix-apply,
live monitoring, LLM/token tracking, and database maintenance:

    const bugs = await client.getAllBugs({ repo: "myrepo" });
    const stats = await client.getDatabaseStats({ repo: "myrepo" });
    await client.proposeFix(ticket.id, { patch_or_command: "sed -i '...' file.py" });
    const result = await client.applyFix({ ticket_id: ticket.id });

Parameter names match the Python API exactly (snake_case, passed as a
single object) — see the main
[README](https://github.com/onenot8/issueLoop#full-api) for the
complete function list.

## CORS

The bridge sends `Access-Control-Allow-Origin: *`, so this package
works directly from browser-based apps (React, Vue) as well as
Node.js and React Native — no proxy needed for local development.

## Requires

`issueloop serve` running on the Python side. Not a reimplementation —
every call is a real HTTP round-trip to that process.

## License

MIT
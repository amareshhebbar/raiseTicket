# issueloop-client

JS/TS client for IssueLoop's local HTTP bridge. This package does not
run IssueLoop — it talks to a Python `issueloop serve` process already
running.

## Install

    npm install issueloop-client

## Use

    const { IssueLoop } = require("issueloop-client");
    const client = new IssueLoop({ baseUrl: "http://127.0.0.1:8787" });
    const ticket = await client.getTopError("myrepo");
    if (ticket) {
      await client.resolve(ticket.id);
    }

## Requires

`issueloop serve` running on the Python side.
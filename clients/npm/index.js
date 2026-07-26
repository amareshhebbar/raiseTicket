class IssueLoop {
  constructor({ baseUrl = "http://127.0.0.1:8787" } = {}) {
    this.baseUrl = baseUrl.replace(/\/$/, "");
  }

  async _get(path) {
    const res = await fetch(`${this.baseUrl}${path}`);
    if (!res.ok) throw new Error(`issueloop server returned ${res.status}`);
    return res.json();
  }

  async _post(path, body) {
    const res = await fetch(`${this.baseUrl}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(`issueloop server returned ${res.status}`);
    return res.json();
  }

  async health() {
    return this._get("/health");
  }

  async getTopError(repo) {
    const result = await this._get(`/errors/top?repo=${encodeURIComponent(repo)}`);
    return Object.keys(result).length === 0 ? null : result;
  }

  async getAllErrors(repo) {
    const result = await this._get(`/errors/all?repo=${encodeURIComponent(repo)}`);
    return result.tickets;
  }

  async resolve(ticketId) {
    return this._post("/errors/resolve", { id: ticketId });
  }

  async fail(ticketId) {
    return this._post("/errors/fail", { id: ticketId });
  }
}

module.exports = { IssueLoop };
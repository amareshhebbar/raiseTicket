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
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new Error(`issueloop server returned ${res.status}${text ? `: ${text}` : ""}`);
    }
    return res.json();
  }

  async _rpc(functionName, params = {}) {
    const response = await this._post(`/rpc/${functionName}`, params);
    return response.result;
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

  async scanRepo(params = {}) {
    return this._rpc("scan_repo", params);
  }

  async getFileInventory(params = {}) {
    return this._rpc("get_file_inventory", params);
  }

  async runTests(params = {}) {
    return this._rpc("run_tests", params);
  }

  async runSingleTest(params = {}) {
    return this._rpc("run_single_test", params);
  }

  async createTickets(params = {}) {
    return this._rpc("create_tickets", params);
  }

  async getAllBugs(params = {}) {
    return this._rpc("get_all_bugs", params);
  }

  async getUnresolvedBugs(params = {}) {
    return this._rpc("get_unresolved_bugs", params);
  }

  async getResolvedBugs(params = {}) {
    return this._rpc("get_resolved_bugs", params);
  }

  async getFailedBugs(params = {}) {
    return this._rpc("get_failed_bugs", params);
  }

  async getBugsNeedingHuman(params = {}) {
    return this._rpc("get_bugs_needing_human", params);
  }

  async getBugsByStatus(params = {}) {
    return this._rpc("get_bugs_by_status", params);
  }

  async getBugsByPriority(params = {}) {
    return this._rpc("get_bugs_by_priority", params);
  }

  async getBug(params = {}) {
    return this._rpc("get_bug", params);
  }

  async getBugCount(params = {}) {
    return this._rpc("get_bug_count", params);
  }

  async getBugCountByStatus(params = {}) {
    return this._rpc("get_bug_count_by_status", params);
  }

  async searchBugs(params = {}) {
    return this._rpc("search_bugs", params);
  }

  async getOldestBug(params = {}) {
    return this._rpc("get_oldest_bug", params);
  }

  async getNewestBug(params = {}) {
    return this._rpc("get_newest_bug", params);
  }

  async escalate(params = {}) {
    return this._rpc("escalate", params);
  }

  async reassign(params = {}) {
    return this._rpc("reassign", params);
  }

  async retryBug(params = {}) {
    return this._rpc("retry_bug", params);
  }

  async getBugAttempts(params = {}) {
    return this._rpc("get_bug_attempts", params);
  }

  async bulkResolve(params = {}) {
    return this._rpc("bulk_resolve", params);
  }

  async proposeFix(params = {}) {
    return this._rpc("propose_fix", params);
  }

  async applyFix(params = {}) {
    return this._rpc("apply_fix", params);
  }

  async checkPermission(params = {}) {
    return this._rpc("check_permission", params);
  }

  async getPermissionAuditLog(params = {}) {
    return this._rpc("get_permission_audit_log", params);
  }

  async watchProcess(params = {}) {
    return this._rpc("watch_process", params);
  }

  async watchLogFile(params = {}) {
    return this._rpc("watch_log_file", params);
  }

  async stopWatch(params = {}) {
    return this._rpc("stop_watch", params);
  }

  async listActiveWatchers(params = {}) {
    return this._rpc("list_active_watchers", params);
  }

  async getTokenConsumption(params = {}) {
    return this._rpc("get_token_consumption", params);
  }

  async getTokenConsumptionByProvider(params = {}) {
    return this._rpc("get_token_consumption_by_provider", params);
  }

  async getLlmCallHistory(params = {}) {
    return this._rpc("get_llm_call_history", params);
  }

  async getLlmProviderStatus(params = {}) {
    return this._rpc("get_llm_provider_status", params);
  }

  async cleanup(params = {}) {
    return this._rpc("cleanup", params);
  }

  async purgeRepo(params = {}) {
    return this._rpc("purge_repo", params);
  }

  async getDatabaseStats(params = {}) {
    return this._rpc("get_database_stats", params);
  }

  async exportBugs(params = {}) {
    return this._rpc("export_bugs", params);
  }

  async reapStaleBugs(params = {}) {
    return this._rpc("reap_stale_bugs", params);
  }

  async rotateLogs(params = {}) {
    return this._rpc("rotate_logs", params);
  }

  async getCrashLog(params = {}) {
    return this._rpc("get_crash_log", params);
  }

  async getNotificationConfig(params = {}) {
    return this._rpc("get_notification_config", params);
  }

  async listRepos(params = {}) {
    return this._rpc("list_repos", params);
  }

  async healthCheck(params = {}) {
    return this._rpc("health_check", params);
  }
}

module.exports = { IssueLoop };
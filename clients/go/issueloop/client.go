package issueloop

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"strings"
	"time"
)

type Ticket struct {
	ID                string  `json:"id"`
	Repo              string  `json:"repo"`
	Priority          string  `json:"priority"`
	Status            string  `json:"status"`
	ErrorSummary      string  `json:"error_summary"`
	RawLogRef         string  `json:"raw_log_ref"`
	Command           *string `json:"command"`
	TestID            *string `json:"test_id"`
	Attempts          int     `json:"attempts"`
	EscalationSummary *string `json:"escalation_summary"`
	ProposedFix       *string `json:"proposed_fix"`
	CreatedAt         string  `json:"created_at"`
	ResolvedAt        *string `json:"resolved_at"`
	DispensedAt       *string `json:"dispensed_at"`
}

type Client struct {
	BaseURL string
	HTTP    *http.Client
}

func NewClient(baseURL string) *Client {
	if baseURL == "" {
		baseURL = "http://127.0.0.1:8787"
	}
	return &Client{
		BaseURL: strings.TrimRight(baseURL, "/"),
		HTTP:    &http.Client{Timeout: 30 * time.Second},
	}
}

type rpcEnvelope struct {
	Result    json.RawMessage `json:"result"`
	Error     string          `json:"error"`
	ErrorType string          `json:"error_type"`
}

func (c *Client) get(path string) ([]byte, int, error) {
	resp, err := c.HTTP.Get(c.BaseURL + path)
	if err != nil {
		return nil, 0, err
	}
	defer resp.Body.Close()
	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, resp.StatusCode, err
	}
	return body, resp.StatusCode, nil
}

func (c *Client) post(path string, payload interface{}) ([]byte, int, error) {
	buf, err := json.Marshal(payload)
	if err != nil {
		return nil, 0, err
	}
	resp, err := c.HTTP.Post(c.BaseURL+path, "application/json", bytes.NewReader(buf))
	if err != nil {
		return nil, 0, err
	}
	defer resp.Body.Close()
	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, resp.StatusCode, err
	}
	return body, resp.StatusCode, nil
}

// RPC calls any of the ~45 functions in IssueLoop's Python API by name and
// unmarshals the result into out. See the Python package's issueloop/__init__.py
// __all__ list for the full set of allowed function names and their kwargs.
func (c *Client) RPC(name string, params map[string]interface{}, out interface{}) error {
	if params == nil {
		params = map[string]interface{}{}
	}
	body, status, err := c.post("/rpc/"+name, params)
	if err != nil {
		return err
	}
	var env rpcEnvelope
	if err := json.Unmarshal(body, &env); err != nil {
		return fmt.Errorf("issueloop: could not parse response: %w", err)
	}
	if status >= 400 {
		return fmt.Errorf("issueloop: %s (%s)", env.Error, env.ErrorType)
	}
	if out == nil || len(env.Result) == 0 {
		return nil
	}
	return json.Unmarshal(env.Result, out)
}

func (c *Client) Health() (map[string]string, error) {
	body, status, err := c.get("/health")
	if err != nil {
		return nil, err
	}
	if status >= 400 {
		return nil, fmt.Errorf("issueloop: server returned %d", status)
	}
	var out map[string]string
	return out, json.Unmarshal(body, &out)
}

func (c *Client) GetTopError(repo string) (*Ticket, error) {
	body, status, err := c.get("/errors/top?repo=" + url.QueryEscape(repo))
	if err != nil {
		return nil, err
	}
	if status >= 400 {
		return nil, fmt.Errorf("issueloop: server returned %d", status)
	}
	if string(body) == "{}" {
		return nil, nil
	}
	var t Ticket
	if err := json.Unmarshal(body, &t); err != nil {
		return nil, err
	}
	return &t, nil
}

func (c *Client) GetAllErrors(repo string) ([]Ticket, error) {
	body, status, err := c.get("/errors/all?repo=" + url.QueryEscape(repo))
	if err != nil {
		return nil, err
	}
	if status >= 400 {
		return nil, fmt.Errorf("issueloop: server returned %d", status)
	}
	var wrapper struct {
		Tickets []Ticket `json:"tickets"`
	}
	if err := json.Unmarshal(body, &wrapper); err != nil {
		return nil, err
	}
	return wrapper.Tickets, nil
}

func (c *Client) Resolve(ticketID string) error {
	_, status, err := c.post("/errors/resolve", map[string]string{"id": ticketID})
	if err != nil {
		return err
	}
	if status >= 400 {
		return fmt.Errorf("issueloop: server returned %d", status)
	}
	return nil
}

func (c *Client) Fail(ticketID string) error {
	_, status, err := c.post("/errors/fail", map[string]string{"id": ticketID})
	if err != nil {
		return err
	}
	if status >= 400 {
		return fmt.Errorf("issueloop: server returned %d", status)
	}
	return nil
}

func (c *Client) ListRepos() ([]string, error) {
	var out []string
	return out, c.RPC("list_repos", nil, &out)
}

func (c *Client) HealthCheck() (map[string]interface{}, error) {
	var out map[string]interface{}
	return out, c.RPC("health_check", nil, &out)
}

func (c *Client) ScanRepo(repoPath string) (map[string]interface{}, error) {
	var out map[string]interface{}
	return out, c.RPC("scan_repo", map[string]interface{}{"repo_path": repoPath}, &out)
}

func (c *Client) RunTests(repoName string) ([]map[string]interface{}, error) {
	var out []map[string]interface{}
	return out, c.RPC("run_tests", map[string]interface{}{"repo_name": repoName}, &out)
}

func (c *Client) CreateTickets(repoName string) ([]Ticket, error) {
	var out []Ticket
	return out, c.RPC("create_tickets", map[string]interface{}{"repo_name": repoName}, &out)
}

func (c *Client) GetAllBugs(repo string) ([]Ticket, error) {
	var out []Ticket
	return out, c.RPC("get_all_bugs", map[string]interface{}{"repo": repo}, &out)
}

func (c *Client) GetUnresolvedBugs(repo string) ([]Ticket, error) {
	var out []Ticket
	return out, c.RPC("get_unresolved_bugs", map[string]interface{}{"repo": repo}, &out)
}

func (c *Client) GetBug(ticketID string) (*Ticket, error) {
	var out *Ticket
	return out, c.RPC("get_bug", map[string]interface{}{"ticket_id": ticketID}, &out)
}

func (c *Client) Escalate(ticketID string, reason string) (*Ticket, error) {
	var out *Ticket
	return out, c.RPC("escalate", map[string]interface{}{"ticket_id": ticketID, "reason": reason}, &out)
}

func (c *Client) ProposeFix(ticketID string, patchOrCommand string) (*Ticket, error) {
	var out *Ticket
	return out, c.RPC("propose_fix", map[string]interface{}{"ticket_id": ticketID, "patch_or_command": patchOrCommand}, &out)
}

func (c *Client) ApplyFix(ticketID string) (map[string]interface{}, error) {
	var out map[string]interface{}
	return out, c.RPC("apply_fix", map[string]interface{}{"ticket_id": ticketID}, &out)
}

func (c *Client) CheckPermission(cmd string, repo string) (bool, error) {
	var out bool
	return out, c.RPC("check_permission", map[string]interface{}{"cmd": cmd, "repo": repo}, &out)
}

func (c *Client) GetDatabaseStats(repo string) (map[string]interface{}, error) {
	var out map[string]interface{}
	return out, c.RPC("get_database_stats", map[string]interface{}{"repo": repo}, &out)
}

func (c *Client) Cleanup(olderThanDays *int, repo string) (int, error) {
	params := map[string]interface{}{"repo": repo}
	if olderThanDays != nil {
		params["older_than_days"] = *olderThanDays
	}
	var out int
	return out, c.RPC("cleanup", params, &out)
}
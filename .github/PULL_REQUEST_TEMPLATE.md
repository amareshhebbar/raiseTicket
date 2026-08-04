**What this changes and why**

**Checklist**
- [ ] `pytest tests/ -v` passes locally, zero external services running
- [ ] New behavior has a new test
- [ ] If `db/local_store.py` or `db/supabase_store.py` changed, both still pass the `db/base.py` interface tests
- [ ] Not adding fix-proposal / diff-apply / PR-creation (out of scope — see CONTRIBUTING.md)
- [ ] Linked issue: #
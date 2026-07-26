# PUBLISHING.md

## Python package (PyPI)

    pip install build twine
    python -m build

Expected: creates `dist/issueloop-0.1.0-py3-none-any.whl` and
`dist/issueloop-0.1.0.tar.gz`. If this fails, `pytest tests/ -v` first —
don't publish a build that doesn't pass its own tests.

    python -m twine upload --repository testpypi dist/*

Test on TestPyPI first. Expected: a URL to
`https://test.pypi.org/project/issueloop/`. Verify with a clean install:

    pip install --index-url https://test.pypi.org/simple/ issueloop
    issueloop --help

Expected: same `--help` output as local dev. Then the real upload:

    python -m twine upload dist/*

Needs a PyPI account + API token. Bump `version` in `pyproject.toml`
before every re-publish — PyPI rejects re-uploading the same number.

## npm package (issueloop-client)

    cd clients/npm
    npm login
    npm publish --access public

Expected: `+ issueloop-client@0.1.0` in the output, and a URL to
`https://www.npmjs.com/package/issueloop-client`. Verify:

    mkdir /tmp/npm-verify && cd /tmp/npm-verify
    npm init -y && npm install issueloop-client
    node -e "const {IssueLoop} = require('issueloop-client'); console.log(new IssueLoop())"

Expected: prints an `IssueLoop { baseUrl: 'http://127.0.0.1:8787' }`
object, no error. Bump `version` in `clients/npm/package.json` before
every re-publish.

## What "done" looks like for both

- CI green on `main` — don't publish off a red build
- A round-trip that actually works from the **published** package, not
  just the dev checkout — I ran this exact check locally already
  (Python server + real Node client, dispense-once, resolve, verified
  the second call correctly returned nothing) before handing you this
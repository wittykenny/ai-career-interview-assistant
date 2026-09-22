# Release Audit

## Scope

This independent release copy was prepared from the newer nested coursework
directory, `presantation/presantation`. Original files were preserved. No core
application algorithms were changed during packaging.

Included: Streamlit entry point, application modules, tests, dependency list,
interview knowledge text, and documentation. Excluded: credentials, personal
internship documents, generated databases, vector indexes, logs, caches, model
weights, and optional third-party skill directories. The latter require a
separate licensing review; their absence may change model prompt enrichment.

## Verification

- Python 3.10.11, existing local environment.
- `python -m pytest tests -q`: **50 passed in 206.04 seconds**.
- This result verifies the existing automated suite, not live provider quality,
  real-world hiring validity, or every browser interaction.
- `pypdf` was missing from the inspected environment. PDF parsing with real
  files remains unverified; install all requirements before use.
- A clean-environment installation and live cloud model availability were not
  verified. No performance benchmark or research metric is claimed.

## Data and Privacy

See `data/README.md` for provenance and limitations. Employment data is a
partial transcription attributed to official reports, not a complete dataset.
Salary figures are industry-reference mappings, not individual salary
predictions. Role records are illustrative. Original sources and redistribution
rights must be reviewed before making the repository public.

Only placeholder credentials belong in `.env.example`. Runtime databases and
uploaded resumes must remain untracked. Automated text-pattern screening is a
limited safeguard, not a guarantee that every sensitive value is detected.

## Publication

Intended repository: `ai-career-interview-assistant`, **private**.
The initial restricted-network authentication check failed. A subsequent
network-enabled check verified authentication successfully. For a new remote,
publish from this directory:

```powershell
gh auth login --hostname github.com --web
gh repo create ai-career-interview-assistant --private --source . --remote origin --push
```

The creation command assumes no repository with that name already exists.
Do not overwrite an existing remote or force-push. No LICENSE has been added;
the owner must choose one after reviewing third-party rights.

## Documentation Review

The README identifies the application problem, implemented methods, data
limitations, setup, tests, and authorship. It presents a course application
prototype, not a novel model, validated assessment instrument, or published
research result.

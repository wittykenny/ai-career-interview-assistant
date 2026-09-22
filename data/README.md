# Data and provenance

The application reconstructs its small SQLite database from constants in `career_assistant/database.py`. Generated databases and Chroma caches are excluded.

- Employment seeds: 15 college-level undergraduate rows transcribed from the ZUEL 2019 employment quality report, table 1.9. Source URL is stored as `OFFICIAL_EMPLOYMENT_SOURCE_URL` in the code. This release has not independently re-audited the transcription.
- Wage references: industry statistics attributed to the National Bureau of Statistics 2024 wage release, including 2023/2024 and private/non-private categories. Role mappings, monthly conversions and salary intervals are derived application values, not official role-level statistics.
- Jobs: 11 illustrative role profiles, not live job vacancies.
- Skill trends: five qualitative seed records referencing Job-SDF (arXiv:2406.11920). These are application summaries, not reproduced measurements or an imported Job-SDF dataset.
- `interview_bank.md`: adapted preparation material whose introductory section lists references. It is not an official employer question bank. Source attribution does not itself grant redistribution rights; review this content before public release.

No raw official PDFs, full third-party datasets, uploaded resumes, or model weights are distributed. No training/test split is used. Missing sample sizes in legacy seeds must not be treated as actual zero-person samples.

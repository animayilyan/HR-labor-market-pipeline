# Architecture

## Data flow
Arbeitnow API (paged, `links.next`) → `data/raw/jobs.ndjson` → Pydantic `Job` →
Polars (dedupe, derive, explode) → SQLite `data/processed/pipeline.db` + Parquet →
`reports/summary.md`

## API envelope (one page)
```
{ "data":  [ {job}, {job}, ... ],
  "links": { "first": url, "last": url, "prev": url|null, "next": url|null },
  "meta":  { "current_page": int, ... } }
```
Stop paging when `links.next` is null or MAX_PAGES is reached.
The feed is newest-first, so a job can appear on two pages if new jobs are posted
during the run → dedupe on `slug`.

## Tables and grain
| Table | One row per | Key | Columns |
|---|---|---|---|
| jobs | job posting | slug | slug, title, company_name, location, remote, url, posted_at, seniority, job_function, tag_count, job_type_count, description_chars |
| job_tags | job × tag | (slug, tag) | slug, tag |
| job_types | job × job type | (slug, job_type) | slug, job_type |

## Fan-out rules
- `jobs` → `job_tags` and `jobs` → `job_types` are 1:N.
- Joining BOTH child tables in one query multiplies rows (tags × types). Never do it.
- Aggregate a child table first (e.g. count per slug or per tag), then join to `jobs`.
- Counting jobs per tag: `job_tags` grouped by tag, `n_unique(slug)`.

## Derived columns (regex on lower-cased title; first match wins, in this order)
seniority:
| value | English | German |
|---|---|---|
| Intern | intern, internship, trainee | praktikum, praktikant, werkstudent, azubi, ausbildung |
| Junior | junior, entry level, graduate | einsteiger, berufseinstieg |
| Lead | lead, head of, principal, director, manager | leitung, leiter, teamleiter |
| Senior | senior, sr. | erfahren |
| Mid / unspecified | everything else | |

job_function:
| value | English | German |
|---|---|---|
| Data & Analytics | data, analyst, analytics, scientist, bi | daten |
| Engineering | engineer, developer, devops, software, frontend, backend, fullstack | entwickler, ingenieur, informatik |
| HR & Recruiting | hr, human resources, recruit, talent, people | personal, recruiter |
| Sales | sales, account executive, business development | vertrieb, verkauf, außendienst |
| Marketing | marketing, seo, content, social media | |
| Finance | finance, accountant, accounting, controller | buchhalt, finanz, steuer |
| Design | design, ux, ui | gestalt |
| Customer Support | support, customer service, customer success | kundenservice, kundenbetreuung |
| Other | everything else | |

Use word boundaries for short keywords (`\bhr\b`, `\bbi\b`, `\bux\b`, `\bui\b`) so "hr" doesn't match "three".

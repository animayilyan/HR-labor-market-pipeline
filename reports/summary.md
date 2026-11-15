# HR Job-Market Summary (Arbeitnow)

Snapshot: 2026-11-15 18:11 UTC · 10 API pages · job data courtesy of [Arbeitnow](https://www.arbeitnow.com/).
Seniority and job function are derived from title keywords (English + German).

## Headline findings
- **2,506 job postings** from **1,035 companies** (2026-11-08 → 2026-11-15).
- Top hiring company: **Doctolib** (56 postings); the top 15 employers post 15.1% of all jobs.
- Most demanded skill tags: **engineering, sales, remote**.
- **6.4% of jobs are remote**; the rest are on-site or hybrid.
- Biggest job hubs: **Paris, London, Berlin**.
- Seniority: Lead roles (749) are the largest named level; entry-level (Intern + Junior) is just 9.0%.
- Largest job function: **Engineering** (24.3% of jobs); 38.8% of titles could not be classified by keywords.
- Most remote-friendly function: **Marketing** (10.7% remote).
- 100.0% of postings were published in the last 7 days.

## 1. Dataset overview

| metric | value |
|---|---|
| Job postings (unique) | 2,506 |
| Hiring companies | 1,035 |
| Distinct skill tags | 686 |
| Distinct job types | 105 |
| Earliest posting | 2026-11-08 |
| Latest posting | 2026-11-15 |
| API pages fetched | 10 (max_pages = 10 reached) |
| Snapshot taken (UTC) | 2026-11-15 18:11 |

**Takeaway:** 2,506 unique postings from 1,035 companies, posted between 2026-11-08 and 2026-11-15.

## 2. Top hiring companies

| company_name | postings | share_of_all_jobs |
|---|---|---|
| Doctolib | 56 | 2.2% |
| MY Humancapital GmbH | 45 | 1.8% |
| Mistral.ai | 25 | 1.0% |
| Alan | 24 | 1.0% |
| Artefactlinkedin | 24 | 1.0% |
| celonis | 24 | 1.0% |
| wppmedia | 23 | 0.9% |
| Artefactjobs | 22 | 0.9% |
| Salonkee | 21 | 0.8% |
| The Trainee Company | 21 | 0.8% |
| Deliveroo | 20 | 0.8% |
| SwissPeak Partners GmbH | 19 | 0.8% |
| Teampicnic | 19 | 0.8% |
| Artefact | 18 | 0.7% |
| Excellent Go4 | 18 | 0.7% |

**Takeaway:** Doctolib leads with 56 postings; the top 15 companies account for 15.1% of all jobs.

## 3. Most demanded skills (tags)

| tag | jobs | share_of_jobs |
|---|---|---|
| engineering | 182 | 7.3% |
| sales | 156 | 6.2% |
| remote | 122 | 4.9% |
| product | 57 | 2.3% |
| operations | 46 | 1.8% |
| social media manager | 44 | 1.8% |
| finance | 41 | 1.6% |
| development | 40 | 1.6% |
| marketing | 37 | 1.5% |
| software development | 34 | 1.4% |
| project management | 33 | 1.3% |
| customer service | 32 | 1.3% |
| system and network administration | 30 | 1.2% |
| commercial | 27 | 1.1% |
| technology | 27 | 1.1% |
| consulting | 26 | 1.0% |
| online marketing | 26 | 1.0% |
| sap/erp consulting | 23 | 0.9% |
| it | 21 | 0.8% |
| tech | 20 | 0.8% |

**Takeaway:** The most frequent tags are engineering, sales, remote. Jobs carry only 1.1 tags on average and tags are broad categories rather than specific tools, so each tag covers a small share.

## 4. Remote vs on-site

| work_mode | jobs | share |
|---|---|---|
| On-site / hybrid | 2346 | 93.6% |
| Remote | 160 | 6.4% |

**Takeaway:** Only 6.4% of postings are flagged remote by the API; the rest are on-site or hybrid (the flag does not separate the two).

## 5. Job type mix

| job_type | jobs | share_of_jobs |
|---|---|---|
| full time | 872 | 34.8% |
| (none given) | 575 | 22.9% |
| unbefristeter arbeitsvertrag | 334 | 13.3% |
| berufserfahren | 229 | 9.1% |
| fulltime permanent | 168 | 6.7% |
| experienced | 129 | 5.1% |
| internship | 83 | 3.3% |
| mid | 75 | 3.0% |
| berufseinstieg | 72 | 2.9% |
| teamleitung | 67 | 2.7% |
| fulltime fixed term | 56 | 2.2% |
| hilfstätigkeit / student | 53 | 2.1% |
| intern | 52 | 2.1% |
| full-time | 49 | 2.0% |
| professional / experienced | 49 | 2.0% |
| student college | 46 | 1.8% |
| entry | 41 | 1.6% |
| contract | 38 | 1.5% |
| freelance | 35 | 1.4% |
| permanent employment (unbefristeter arbeitsvertrag) | 30 | 1.2% |

**Takeaway:** "full time" is the most common type (872 jobs). Labels mix English and German (e.g. contract type and experience level), and one job can carry several.

## 6. Where the jobs are (top 15 locations)

| city | jobs | share |
|---|---|---|
| Paris | 359 | 14.3% |
| London | 318 | 12.7% |
| Berlin | 271 | 10.8% |
| Munich | 185 | 7.4% |
| Remote / home office | 114 | 4.5% |
| Zürich | 102 | 4.1% |
| (not given) | 98 | 3.9% |
| Amsterdam | 83 | 3.3% |
| Hamburg | 38 | 1.5% |
| Cologne | 33 | 1.3% |
| Germany | 32 | 1.3% |
| Bern | 25 | 1.0% |
| United Kingdom | 22 | 0.9% |
| France | 19 | 0.8% |
| Düsseldorf | 18 | 0.7% |

**Takeaway:** Paris has the most postings (359, 14.3%); top 3 cities: Paris, London, Berlin. Locations are free text, so spellings were normalized (e.g. Zurich → Zürich).

## 7. Seniority distribution

| seniority | jobs | share |
|---|---|---|
| Intern | 161 | 6.4% |
| Junior | 65 | 2.6% |
| Mid / unspecified | 1096 | 43.7% |
| Senior | 435 | 17.4% |
| Lead | 749 | 29.9% |

**Takeaway:** The largest group (43.7%) names no level; among titles that do, Lead is most common (749) — note that "Lead" counts every "…Manager" title. Entry-level roles (Intern + Junior) are only 9.0%.

## 8. Job functions

| job_function | jobs | share |
|---|---|---|
| Other | 972 | 38.8% |
| Engineering | 608 | 24.3% |
| Sales | 280 | 11.2% |
| Data & Analytics | 202 | 8.1% |
| Marketing | 149 | 5.9% |
| HR & Recruiting | 88 | 3.5% |
| Finance | 84 | 3.4% |
| Customer Support | 65 | 2.6% |
| Design | 58 | 2.3% |

**Takeaway:** Engineering is the largest classified function (608, 24.3%); 972 jobs (38.8%) stayed "Other" (keyword rules only; LLM fallback was not run).

## 9. Remote share by job function (functions with ≥ 10 jobs)

| job_function | jobs | remote_jobs | remote_share |
|---|---|---|---|
| Marketing | 149 | 16 | 10.7% |
| Sales | 280 | 29 | 10.4% |
| Design | 58 | 6 | 10.3% |
| Finance | 84 | 7 | 8.3% |
| Other | 972 | 55 | 5.7% |
| Engineering | 608 | 32 | 5.3% |
| Customer Support | 65 | 3 | 4.6% |
| Data & Analytics | 202 | 9 | 4.5% |
| HR & Recruiting | 88 | 3 | 3.4% |

**Takeaway:** Marketing is the most remote-friendly function (10.7%); HR & Recruiting the least (3.4%).

## 10. Skills of remote vs on-site roles (top 10 tags each)

| rank | remote tag | % of remote jobs | on-site tag | % of on-site jobs |
|---|---|---|---|---|
| 1 | remote | 76.2% | engineering | 7.5% |
| 2 | sales | 8.1% | sales | 6.1% |
| 3 | customer service | 4.4% | product | 2.3% |
| 4 | engineering | 4.4% | operations | 2.0% |
| 5 | online marketing | 4.4% | finance | 1.7% |
| 6 | social media manager | 4.4% | marketing | 1.6% |
| 7 | global digital - emea | 3.8% | social media manager | 1.6% |
| 8 | project management | 3.8% | development | 1.5% |
| 9 | business development | 3.1% | software development | 1.3% |
| 10 | consulting | 2.5% | commercial | 1.2% |

**Takeaway:** Remote roles lean on remote, sales, customer service; on-site roles on engineering, sales, product.

## 11. Posting freshness (age at snapshot time)

| posted | jobs | share |
|---|---|---|
| ≤ 7 days | 2506 | 100.0% |
| 8–30 days | 0 | 0.0% |
| > 30 days | 0 | 0.0% |

**Takeaway:** 100.0% of postings are at most a week old. The feed is newest-first and the run stopped at MAX_PAGES, so older postings were not read and the sample skews fresh.

## 12. Data quality

| check | value |
|---|---|
| Raw records fetched | 2510 |
| Rejected by Pydantic | 0 |
| Duplicate slugs removed | 4 |
| Unique jobs kept | 2506 |
| Jobs with no tags | 80 (3.2%) |
| Jobs with no job type | 575 (22.9%) |
| Jobs with no location | 98 (3.9%) |

**Takeaway:** 0 records failed validation and 4 duplicates were removed; the biggest gap is a missing job type (22.9% of jobs).

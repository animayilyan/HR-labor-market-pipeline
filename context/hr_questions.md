# HR analytics questions for reports/summary.md

Answer each with Polars from the Parquet files. One section per question:
a small markdown table + a one-line takeaway in plain English.

1. **Dataset overview** – jobs, companies, distinct tags, date range of postings, pages fetched.
2. **Top hiring companies** – top 15 companies by number of postings.
3. **Most demanded skills** – top 20 tags by number of distinct jobs.
4. **Remote vs on-site** – count and share of remote jobs.
5. **Job type mix** – postings per job_type (full time, part time, internship, …).
6. **Where the jobs are** – top 15 locations.
7. **Seniority distribution** – jobs per seniority level, with share.
8. **Job functions** – jobs per job_function; how many stayed "Other".
9. **Remote share by job function** – % remote within each function (only functions with ≥ 10 jobs).
10. **Skills of remote roles** – top 10 tags among remote jobs vs on-site jobs.
11. **Posting freshness** – jobs posted in the last 7, 30, and more than 30 days before the run date.
12. **Data quality** – rejected records, duplicate slugs removed, jobs with no tags.

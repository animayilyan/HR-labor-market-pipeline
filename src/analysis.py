"""HR analytics over the Parquet tables → `reports/summary.md` (one section per question).

Answers every question in `context/hr_questions.md` with Polars. Fan-out rule: `job_tags`
and `job_types` are NEVER joined in the same query; each child table is aggregated on its own
(optionally joined to `jobs`, which is 1:N and therefore safe).
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import polars as pl

SENIORITY_ORDER: list[str] = ["Intern", "Junior", "Mid / unspecified", "Senior", "Lead"]


@dataclass(frozen=True)
class Section:
    """One report section: a heading, a small result table and a one-line takeaway."""

    title: str
    table: pl.DataFrame
    takeaway: str
    headline: str | None = None  # short bullet for README "Headline findings"


# ---------------------------------------------------------------- helpers
def load_tables(processed_dir: Path) -> dict[str, pl.DataFrame]:
    """Read `jobs`, `job_tags`, `job_types` from their Parquet files."""
    return {name: pl.read_parquet(processed_dir / f"{name}.parquet")
            for name in ("jobs", "job_tags", "job_types")}


def pct(expr: pl.Expr) -> pl.Expr:
    """Format a 0–1 share as a percentage string with one decimal, e.g. `12.3%`."""
    return pl.concat_str((expr * 100).round(1).cast(pl.String), pl.lit("%"))


def fmt_pct(share: float) -> str:
    """Format a 0–1 share as `12.3%` (for takeaway sentences)."""
    return f"{share * 100:.1f}%"


def to_markdown(df: pl.DataFrame) -> str:
    """Render a small DataFrame as a GitHub markdown table using native Polars string ops."""
    if df.is_empty():
        return "_(no rows)_"
    cells = df.select(
        pl.all().cast(pl.String).fill_null("—").str.replace_all("|", r"\|", literal=True)
    )
    lines = cells.select(
        pl.concat_str([pl.lit("| "), pl.concat_str(pl.all(), separator=" | "), pl.lit(" |")])
        .alias("line")
    ).get_column("line")
    header = "| " + " | ".join(df.columns) + " |"
    rule = "|" + "|".join("---" for _ in df.columns) + "|"
    return "\n".join([header, rule, *lines.to_list()])


def run_time(meta: dict[str, Any]) -> datetime:
    """Snapshot time of the data (when the API was read); falls back to now (UTC)."""
    raw = meta.get("ingested_at")
    return datetime.fromisoformat(raw) if raw else datetime.now(UTC)


# ---------------------------------------------------------------- questions
def q01_overview(t: dict[str, pl.DataFrame], meta: dict[str, Any]) -> Section:
    """Dataset overview: jobs, companies, distinct tags, date range, pages fetched."""
    jobs = t["jobs"]
    stats = jobs.select(
        n_jobs=pl.len(),
        n_companies=pl.col("company_name").n_unique(),
        first=pl.col("posted_at").min().dt.strftime("%Y-%m-%d"),
        last=pl.col("posted_at").max().dt.strftime("%Y-%m-%d"),
    ).row(0, named=True)
    n_tags = t["job_tags"].get_column("tag").n_unique()
    n_types = t["job_types"].get_column("job_type").n_unique()
    pages = meta.get("pages_fetched", "n/a")
    table = pl.DataFrame({
        "metric": ["Job postings (unique)", "Hiring companies", "Distinct skill tags",
                   "Distinct job types", "Earliest posting", "Latest posting",
                   "API pages fetched", "Snapshot taken (UTC)"],
        "value": [f"{stats['n_jobs']:,}", f"{stats['n_companies']:,}", f"{n_tags:,}", f"{n_types:,}",
                  stats["first"], stats["last"], f"{pages} ({meta.get('stop_reason', 'n/a')})",
                  run_time(meta).strftime("%Y-%m-%d %H:%M")],
    })
    return Section(
        "1. Dataset overview", table,
        f"{stats['n_jobs']:,} unique postings from {stats['n_companies']:,} companies, "
        f"posted between {stats['first']} and {stats['last']}.",
        f"**{stats['n_jobs']:,} job postings** from **{stats['n_companies']:,} companies** "
        f"({stats['first']} → {stats['last']}).",
    )


def q02_top_companies(t: dict[str, pl.DataFrame], meta: dict[str, Any]) -> Section:
    """Top 15 companies by number of postings."""
    jobs = t["jobs"]
    top = (jobs.group_by("company_name").agg(postings=pl.len())
           .sort(["postings", "company_name"], descending=[True, False]).head(15)
           .with_columns(share_of_all_jobs=pct(pl.col("postings") / jobs.height)))
    leader = top.row(0, named=True)
    top15_share = top.get_column("postings").sum() / jobs.height
    return Section(
        "2. Top hiring companies", top,
        f"{leader['company_name']} leads with {leader['postings']} postings; the top 15 companies "
        f"account for {fmt_pct(top15_share)} of all jobs.",
        f"Top hiring company: **{leader['company_name']}** ({leader['postings']} postings); "
        f"the top 15 employers post {fmt_pct(top15_share)} of all jobs.",
    )


def q03_top_skills(t: dict[str, pl.DataFrame], meta: dict[str, Any]) -> Section:
    """Top 20 tags by number of distinct jobs."""
    n_jobs = t["jobs"].height
    top = (t["job_tags"].group_by("tag").agg(jobs=pl.col("slug").n_unique())
           .sort(["jobs", "tag"], descending=[True, False]).head(20)
           .with_columns(share_of_jobs=pct(pl.col("jobs") / n_jobs)))
    names = ", ".join(top.get_column("tag").head(3).to_list())
    mean_tags = float(t["jobs"].get_column("tag_count").mean() or 0.0)
    return Section(
        "3. Most demanded skills (tags)", top,
        f"The most frequent tags are {names}. Jobs carry only {mean_tags:.1f} tags on average and "
        "tags are broad categories rather than specific tools, so each tag covers a small share.",
        f"Most demanded skill tags: **{names}**.",
    )


def q04_remote(t: dict[str, pl.DataFrame], meta: dict[str, Any]) -> Section:
    """Count and share of remote vs on-site jobs."""
    jobs = t["jobs"]
    table = (jobs.group_by("remote").agg(jobs=pl.len())
             .with_columns(work_mode=pl.when(pl.col("remote")).then(pl.lit("Remote"))
                           .otherwise(pl.lit("On-site / hybrid")),
                           share=pct(pl.col("jobs") / jobs.height))
             .sort("jobs", descending=True).select("work_mode", "jobs", "share"))
    remote_share = float(jobs.get_column("remote").mean() or 0.0)
    return Section(
        "4. Remote vs on-site", table,
        f"Only {fmt_pct(remote_share)} of postings are flagged remote by the API; the rest are "
        "on-site or hybrid (the flag does not separate the two).",
        f"**{fmt_pct(remote_share)} of jobs are remote**; the rest are on-site or hybrid.",
    )


def q05_job_types(t: dict[str, pl.DataFrame], meta: dict[str, Any]) -> Section:
    """Postings per job_type (a job can have several types, so shares do not sum to 100%)."""
    jobs = t["jobs"]
    counts = t["job_types"].group_by("job_type").agg(jobs=pl.col("slug").n_unique())
    none_given = pl.DataFrame({"job_type": ["(none given)"],
                               "jobs": [jobs.filter(pl.col("job_type_count") == 0).height]},
                              schema={"job_type": pl.String, "jobs": pl.UInt32})
    table = (pl.concat([counts, none_given]).sort(["jobs", "job_type"], descending=[True, False])
             .head(20).with_columns(share_of_jobs=pct(pl.col("jobs") / jobs.height)))
    top = table.row(0, named=True)
    return Section(
        "5. Job type mix", table,
        f"\"{top['job_type']}\" is the most common type ({top['jobs']} jobs). Labels mix English and "
        "German (e.g. contract type and experience level), and one job can carry several.",
    )


#: Spelling variants merged into the spelling used most often in the data (no transliteration).
CITY_ALIASES: dict[str, str] = {"Zurich": "Zürich", "München": "Munich", "Köln": "Cologne",
                                "Frankfurt am Main": "Frankfurt", "LONDON": "London"}


def normalize_city(location: pl.Expr) -> pl.Expr:
    """Reduce free-text `location` to a city label with native string expressions.

    Drops country prefixes ("Deutschland / Berlin"), Paris arrondissements, "(hybrid)" /
    "office" decorations and leading emoji; keeps the first of several cities; groups every
    remote / home-office label; merges spelling variants via `CITY_ALIASES`.
    """
    text = location.fill_null("").str.strip_chars()
    city = (
        text.str.replace(r"(?i)^(deutschland|germany|united kingdom|uk|gbr|gb)\s*[-/]\s*", "")
        .str.replace(r"(?i)^\d+(st|nd|rd|th|e|er)\s+arrondissement\s+(of|de)\s+", "")
        .str.replace(r"(?i)^hybrid\s*-\s*", "")
        .str.replace(r"^[^\p{L}]+", "")
        .str.extract(r"^([^,;/(]+)", 1)
        .str.replace(r"(?i)\s+office$", "")
        .str.strip_chars()
        .replace(CITY_ALIASES)
    )
    return (pl.when(text == "").then(pl.lit("(not given)"))
            .when(text.str.contains(r"(?i)remote|home ?office")).then(pl.lit("Remote / home office"))
            .when(city.is_null() | (city == "")).then(pl.lit("(not given)"))
            .otherwise(city))


def q06_locations(t: dict[str, pl.DataFrame], meta: dict[str, Any]) -> Section:
    """Top 15 locations (normalized city label, see `normalize_city`)."""
    jobs = t["jobs"]
    table = (jobs.with_columns(city=normalize_city(pl.col("location")))
             .group_by("city").agg(jobs=pl.len())
             .sort(["jobs", "city"], descending=[True, False]).head(15)
             .with_columns(share=pct(pl.col("jobs") / jobs.height)))
    cities = table.filter(~pl.col("city").is_in(["(not given)", "Remote / home office"]))
    top = cities.row(0, named=True)
    top3 = ", ".join(cities.get_column("city").head(3).to_list())
    return Section(
        "6. Where the jobs are (top 15 locations)", table,
        f"{top['city']} has the most postings ({top['jobs']}, {top['share']}); top 3 cities: {top3}. "
        "Locations are free text, so spellings were normalized (e.g. Zurich → Zürich).",
        f"Biggest job hubs: **{top3}**.",
    )


def q07_seniority(t: dict[str, pl.DataFrame], meta: dict[str, Any]) -> Section:
    """Jobs per seniority level (from title keywords), with share."""
    jobs = t["jobs"]
    order = pl.DataFrame({"seniority": SENIORITY_ORDER, "_o": list(range(len(SENIORITY_ORDER)))})
    table = (jobs.group_by("seniority").agg(jobs=pl.len())
             .join(order, on="seniority", how="left").sort("_o").drop("_o")
             .with_columns(share=pct(pl.col("jobs") / jobs.height)))
    named = table.filter(pl.col("seniority") != "Mid / unspecified").sort("jobs", descending=True).row(0, named=True)
    unspecified = table.filter(pl.col("seniority") == "Mid / unspecified").row(0, named=True)
    entry = table.filter(pl.col("seniority").is_in(["Intern", "Junior"])).get_column("jobs").sum()
    return Section(
        "7. Seniority distribution", table,
        f"The largest group ({unspecified['share']}) names no level; among titles that do, "
        f"{named['seniority']} is most common ({named['jobs']}) — note that \"Lead\" counts every "
        f"\"…Manager\" title. Entry-level roles (Intern + Junior) are only {fmt_pct(entry / jobs.height)}.",
        f"Seniority: {named['seniority']} roles ({named['jobs']}) are the largest named level; "
        f"entry-level (Intern + Junior) is just {fmt_pct(entry / jobs.height)}.",
    )


def q08_functions(t: dict[str, pl.DataFrame], meta: dict[str, Any]) -> Section:
    """Jobs per job_function; how many stayed "Other"."""
    jobs = t["jobs"]
    table = (jobs.group_by("job_function").agg(jobs=pl.len())
             .sort(["jobs", "job_function"], descending=[True, False])
             .with_columns(share=pct(pl.col("jobs") / jobs.height)))
    other = int(table.filter(pl.col("job_function") == "Other").get_column("jobs").sum())
    top = table.filter(pl.col("job_function") != "Other").row(0, named=True)
    return Section(
        "8. Job functions", table,
        f"{top['job_function']} is the largest classified function ({top['jobs']}, {top['share']}); "
        f"{other} jobs ({fmt_pct(other / jobs.height)}) stayed \"Other\" (keyword rules only; "
        "LLM fallback was not run).",
        f"Largest job function: **{top['job_function']}** ({top['share']} of jobs); "
        f"{fmt_pct(other / jobs.height)} of titles could not be classified by keywords.",
    )


def q09_remote_by_function(t: dict[str, pl.DataFrame], meta: dict[str, Any]) -> Section:
    """% remote within each job_function (only functions with ≥ 10 jobs)."""
    table = (t["jobs"].group_by("job_function")
             .agg(jobs=pl.len(), remote_jobs=pl.col("remote").sum(), _share=pl.col("remote").mean())
             .filter(pl.col("jobs") >= 10)
             .sort(["_share", "job_function"], descending=[True, False])
             .with_columns(remote_share=pct(pl.col("_share"))).drop("_share"))
    top, low = table.row(0, named=True), table.row(-1, named=True)
    return Section(
        "9. Remote share by job function (functions with ≥ 10 jobs)", table,
        f"{top['job_function']} is the most remote-friendly function ({top['remote_share']}); "
        f"{low['job_function']} the least ({low['remote_share']}).",
        f"Most remote-friendly function: **{top['job_function']}** ({top['remote_share']} remote).",
    )


def q10_remote_skills(t: dict[str, pl.DataFrame], meta: dict[str, Any]) -> Section:
    """Top 10 tags among remote jobs vs on-site jobs (job_tags ⋈ jobs only; 1:N, no fan-out)."""
    jobs = t["jobs"]
    n_by_mode = dict(jobs.group_by("remote").agg(n=pl.len()).iter_rows())
    tagged = t["job_tags"].join(jobs.select("slug", "remote"), on="slug", how="inner")

    def top10(is_remote: bool, label: str) -> pl.DataFrame:
        """Top 10 tags for one work mode, ranked, with share of that mode's jobs."""
        return (tagged.filter(pl.col("remote") == is_remote)
                .group_by("tag").agg(jobs=pl.col("slug").n_unique())
                .sort(["jobs", "tag"], descending=[True, False]).head(10)
                .with_row_index("rank", offset=1)
                .select("rank",
                        pl.col("tag").alias(f"{label} tag"),
                        pct(pl.col("jobs") / max(n_by_mode.get(is_remote, 0), 1)).alias(f"% of {label} jobs")))

    table = top10(True, "remote").join(top10(False, "on-site"), on="rank", how="full", coalesce=True).sort("rank")
    r1 = table.get_column("remote tag").drop_nulls().head(3).to_list()
    o1 = table.get_column("on-site tag").drop_nulls().head(3).to_list()
    return Section(
        "10. Skills of remote vs on-site roles (top 10 tags each)", table,
        f"Remote roles lean on {', '.join(r1)}; on-site roles on {', '.join(o1)}.",
    )


def q11_freshness(t: dict[str, pl.DataFrame], meta: dict[str, Any]) -> Section:
    """Jobs posted ≤ 7, 8–30 and > 30 days before the snapshot time."""
    jobs = t["jobs"]
    now = run_time(meta)
    bucket = (pl.when(pl.col("posted_at") >= now - timedelta(days=7)).then(pl.lit("≤ 7 days"))
              .when(pl.col("posted_at") >= now - timedelta(days=30)).then(pl.lit("8–30 days"))
              .otherwise(pl.lit("> 30 days")))
    order = pl.DataFrame({"posted": ["≤ 7 days", "8–30 days", "> 30 days"], "_o": [0, 1, 2]})
    table = (order.join(jobs.with_columns(posted=bucket).group_by("posted").agg(jobs=pl.len()),
                        on="posted", how="left")
             .with_columns(pl.col("jobs").fill_null(0)).sort("_o").drop("_o")
             .with_columns(share=pct(pl.col("jobs") / jobs.height)))
    fresh = table.row(0, named=True)
    capped = str(meta.get("stop_reason", "")).startswith("max_pages")
    why = (" The feed is newest-first and the run stopped at MAX_PAGES, so older postings were "
           "not read and the sample skews fresh." if capped else "")
    return Section(
        "11. Posting freshness (age at snapshot time)", table,
        f"{fresh['share']} of postings are at most a week old.{why}",
        f"{fresh['share']} of postings were published in the last 7 days.",
    )


def q12_data_quality(t: dict[str, pl.DataFrame], meta: dict[str, Any]) -> Section:
    """Rejected records, duplicate slugs removed, jobs with no tags / types / location."""
    jobs = t["jobs"]
    no_tags = jobs.filter(pl.col("tag_count") == 0).height
    no_types = jobs.filter(pl.col("job_type_count") == 0).height
    no_loc = jobs.filter(pl.col("location").fill_null("").str.strip_chars() == "").height
    rows = {
        "Raw records fetched": meta.get("raw_records", "n/a"),
        "Rejected by Pydantic": meta.get("rejected_records", "n/a"),
        "Duplicate slugs removed": meta.get("duplicates_removed", "n/a"),
        "Unique jobs kept": jobs.height,
        "Jobs with no tags": f"{no_tags} ({fmt_pct(no_tags / jobs.height)})",
        "Jobs with no job type": f"{no_types} ({fmt_pct(no_types / jobs.height)})",
        "Jobs with no location": f"{no_loc} ({fmt_pct(no_loc / jobs.height)})",
    }
    table = pl.DataFrame({"check": list(rows), "value": [str(v) for v in rows.values()]})
    gaps = {"job type": no_types, "tag": no_tags, "location": no_loc}
    worst = max(gaps, key=lambda k: gaps[k])
    return Section(
        "12. Data quality", table,
        f"{meta.get('rejected_records', 'n/a')} records failed validation and "
        f"{meta.get('duplicates_removed', 'n/a')} duplicates were removed; the biggest gap is a "
        f"missing {worst} ({fmt_pct(gaps[worst] / jobs.height)} of jobs).",
    )


QUESTIONS = [q01_overview, q02_top_companies, q03_top_skills, q04_remote, q05_job_types,
             q06_locations, q07_seniority, q08_functions, q09_remote_by_function,
             q10_remote_skills, q11_freshness, q12_data_quality]


# ---------------------------------------------------------------- report
def build_sections(tables: dict[str, pl.DataFrame], meta: dict[str, Any]) -> list[Section]:
    """Answer every HR question; returns one `Section` per question, in order."""
    return [question(tables, meta) for question in QUESTIONS]


def headline_findings(sections: list[Section]) -> list[str]:
    """Collect the short headline bullets (for README and the console)."""
    return [s.headline for s in sections if s.headline]


def render_summary(sections: list[Section], meta: dict[str, Any]) -> str:
    """Render the full markdown report."""
    parts = [
        "# HR Job-Market Summary (Arbeitnow)",
        "",
        f"Snapshot: {run_time(meta).strftime('%Y-%m-%d %H:%M')} UTC · "
        f"{meta.get('pages_fetched', 'n/a')} API pages · job data courtesy of "
        "[Arbeitnow](https://www.arbeitnow.com/).",
        "Seniority and job function are derived from title keywords (English + German).",
        "",
        "## Headline findings",
        *[f"- {line}" for line in headline_findings(sections)],
    ]
    for s in sections:
        parts += ["", f"## {s.title}", "", to_markdown(s.table), "", f"**Takeaway:** {s.takeaway}"]
    return "\n".join(parts) + "\n"


def write_summary(processed_dir: Path, report_path: Path, meta: dict[str, Any]) -> list[Section]:
    """Load Parquet, answer all questions, write `summary.md`; return the sections."""
    sections = build_sections(load_tables(processed_dir), meta)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_summary(sections, meta), encoding="utf-8")
    return sections

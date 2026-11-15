"""Pure Polars transformations: validated jobs → `jobs`, `job_tags`, `job_types` tables.

No file, network or database I/O in this module (that lives in ingestor.py, storage.py,
pipeline.py), so every function can be tested offline. Only native Polars expressions are
used: no `map_elements`, no `apply`, no Python loops over rows.
"""

from collections.abc import Sequence
from functools import reduce

import polars as pl

from src.models import Job

#: Schema of the validated input frame (one row per API record, duplicates still present).
RAW_SCHEMA: dict[str, pl.DataType] = {
    "slug": pl.String(),
    "company_name": pl.String(),
    "title": pl.String(),
    "description": pl.String(),
    "remote": pl.Boolean(),
    "url": pl.String(),
    "tags": pl.List(pl.String()),
    "job_types": pl.List(pl.String()),
    "location": pl.String(),
    "created_at": pl.Datetime("us", "UTC"),
}

#: Columns of the `jobs` table, in order (see context/architecture.md).
JOBS_COLUMNS: list[str] = [
    "slug", "title", "company_name", "location", "remote", "url", "posted_at",
    "seniority", "job_function", "tag_count", "job_type_count", "description_chars",
]

# Regex rules on the lower-cased title; first match wins, in this order.
# English + German keywords from architecture.md. Word boundaries (\b) guard short or
# ambiguous English words ("hr" ≠ "three", "intern" ≠ "international"). German keywords stay
# substrings because German builds compounds ("Werkstudentin", "Abteilungsleiter").
SENIORITY_RULES: list[tuple[str, str]] = [
    ("Intern", r"\bintern(ship)?s?\b|\btrainee|praktikum|praktikant|werkstudent|\bazubi|ausbildung"),
    ("Junior", r"\bjunior\b|\bjr\.?\b|entry[- ]level|\bgraduate|einsteiger|berufseinstieg"),
    ("Lead", r"\blead\b|\bteam ?lead|head of|\bprincipal\b|\bdirector\b|\bmanager\b"
             r"|(^|[^g])leit(ung|er)"),  # [^g]: "Begleiter/Begleitung" (companion) is not a lead
    ("Senior", r"\bsenior\b|\bsr\.?\b|erfahren"),
]
SENIORITY_DEFAULT: str = "Mid / unspecified"

JOB_FUNCTION_RULES: list[tuple[str, str]] = [
    ("Data & Analytics", r"\bdata\b|analyst|analytics|scientist|\bbi\b|daten"),
    ("Engineering", r"engineer|developer|devops|software|front[- ]?end|back[- ]?end|full[- ]?stack"
                    r"|entwickler|ingenieur|informatik"),
    ("HR & Recruiting", r"\bhr\b|human resources|recruit|talent|\bpeople\b|personal"),
    ("Sales", r"\bsales\b|account executive|account manager|business development"
              r"|vertrieb|verkauf|verkäuf"
              r"|außendienst|aussendienst"),
    ("Marketing", r"marketing|\bseo\b|\bcontent\b|social media"),
    ("Finance", r"financ|accountant|accounting|controller|controlling|buchhalt|finanz"
                r"|steuer([^u]|$)"),  # "Steuerberater" yes, "Steuerungstechnik" (controls) no
    ("Design", r"design|\bux\b|\bui\b|gestalt"),
    ("Customer Support", r"support|customer service|customer success|kundenservice"
                         r"|kundenbetreuung"),
]
JOB_FUNCTION_DEFAULT: str = "Other"


class GrainError(ValueError):
    """Raised when a table breaks its declared grain or the parent/child counts disagree."""


def jobs_to_lazyframe(jobs: Sequence[Job]) -> pl.LazyFrame:
    """Turn validated `Job` models into a typed LazyFrame (in-memory, no I/O)."""
    rows = [job.model_dump() for job in jobs]
    return pl.DataFrame(rows, schema=RAW_SCHEMA).lazy()


def classify_title(title: pl.Expr, rules: Sequence[tuple[str, str]], default: str) -> pl.Expr:
    """Build a `when/then` chain: the first regex in `rules` that matches the title wins."""
    lowered = title.str.to_lowercase()
    first_label, first_pattern = rules[0]
    chain = pl.when(lowered.str.contains(first_pattern)).then(pl.lit(first_label))
    chain = reduce(
        lambda acc, rule: acc.when(lowered.str.contains(rule[1])).then(pl.lit(rule[0])),
        rules[1:],
        chain,
    )
    return chain.otherwise(pl.lit(default))


def clean_list(column: str) -> pl.Expr:
    """Trim + lower-case every list item, drop empty/null items and per-row duplicates."""
    return (
        pl.col(column)
        .fill_null(pl.lit([], dtype=pl.List(pl.String())))
        .list.eval(pl.element().str.strip_chars().str.to_lowercase())
        .list.eval(pl.element().filter(pl.element().is_not_null() & (pl.element() != "")))
        .list.unique(maintain_order=True)
    )


def dedupe_slugs(lf: pl.LazyFrame) -> pl.LazyFrame:
    """Keep the first occurrence of each slug (the feed is newest-first and shifts while paging)."""
    return lf.unique(subset="slug", keep="first", maintain_order=True)


def build_jobs(lf: pl.LazyFrame) -> pl.DataFrame:
    """One row per slug with derived seniority, job_function, list lengths and description size."""
    return (
        dedupe_slugs(lf)
        .with_columns(
            posted_at=pl.col("created_at"),
            seniority=classify_title(pl.col("title"), SENIORITY_RULES, SENIORITY_DEFAULT),
            job_function=classify_title(pl.col("title"), JOB_FUNCTION_RULES, JOB_FUNCTION_DEFAULT),
            tag_count=clean_list("tags").list.len().cast(pl.Int64),
            job_type_count=clean_list("job_types").list.len().cast(pl.Int64),
            description_chars=pl.col("description").fill_null("").str.len_chars().cast(pl.Int64),
        )
        .select(JOBS_COLUMNS)
        .collect()
    )


def _explode_child(lf: pl.LazyFrame, source: str, target: str) -> pl.DataFrame:
    """Explode a cleaned list column into a (slug, target) bridge table, one row per pair."""
    return (
        dedupe_slugs(lf)
        .select("slug", clean_list(source).alias(target))
        .explode(target)
        .drop_nulls(target)  # rows whose list was empty explode to a single null
        .unique(maintain_order=True)
        .collect()
    )


def build_job_tags(lf: pl.LazyFrame) -> pl.DataFrame:
    """Bridge table job × tag: (slug, tag), tags lower-cased and trimmed, empties removed."""
    return _explode_child(lf, "tags", "tag")


def build_job_types(lf: pl.LazyFrame) -> pl.DataFrame:
    """Bridge table job × job type: (slug, job_type), cleaned the same way as tags."""
    return _explode_child(lf, "job_types", "job_type")


def check_grain(jobs: pl.DataFrame, job_tags: pl.DataFrame, job_types: pl.DataFrame) -> dict[str, int]:
    """Assert the table grain; raise `GrainError` on any violation, else return the counts.

    Checks: slug unique in `jobs`; `sum(tag_count)` = rows in `job_tags`;
    `sum(job_type_count)` = rows in `job_types`; (slug, child) unique; every child slug in `jobs`.
    """
    if jobs.get_column("slug").n_unique() != jobs.height:
        raise GrainError(f"jobs.slug is not unique ({jobs.height} rows, "
                         f"{jobs.get_column('slug').n_unique()} distinct slugs)")
    for child, count_col, name in ((job_tags, "tag_count", "job_tags"),
                                   (job_types, "job_type_count", "job_types")):
        expected = int(jobs.get_column(count_col).sum())
        if expected != child.height:
            raise GrainError(f"sum(jobs.{count_col}) = {expected} but {name} has {child.height} rows")
        if child.unique().height != child.height:
            raise GrainError(f"{name} has duplicate (slug, value) rows")
        orphans = child.join(jobs.select("slug"), on="slug", how="anti")
        if orphans.height:
            raise GrainError(f"{name} has {orphans.height} rows whose slug is missing in jobs")
    return {"jobs": jobs.height, "job_tags": job_tags.height, "job_types": job_types.height}

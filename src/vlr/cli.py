"""CLI entry point.

Bulk-scrape workflow:
    1. Discover events into files (filter by category):
       python -m vlr.cli discover-events --since 2024 --category international --output events_international.txt
       python -m vlr.cli discover-events --since 2024 --category regional --output events_regional.txt
       python -m vlr.cli discover-events --since 2024 --category challengers --output events_challengers.txt
    2. Review the file(s) in VSCode, delete any duds
    3. Bulk scrape (resumable):
       cat events_*.txt > events_all.txt
       python -m vlr.cli scrape-events-bulk events_all.txt --verbose
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.logging import RichHandler
from rich.table import Table
from sqlalchemy import desc, func, or_, select, text as sql_text

from .db.models import (
    Event,
    MapPlayed,
    Match,
    Player,
    PlayerMapStat,
    Team,
    VetoAction,
)
from .db.session import get_session, init_db as _init_db
from .scraping.pipeline import (
    bulk_scrape_events,
    discover_events,
    repair_event_names,
    scrape_event,
    scrape_match_ids,
    scrape_rankings,
    scrape_recent,
)

console = Console()
app = typer.Typer(add_completion=False, help="vlr.gg analytics CLI")


def _configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True, markup=False, show_path=False)],
    )


# --- Setup / scraping ----------------------------------------------------


@app.command("init-db")
def init_db_cmd() -> None:
    """Create or update the database schema. Safe to call repeatedly.

    Creates any missing tables AND applies any pending column migrations.
    Use this after upgrading the project to a new iteration.
    """
    _configure_logging(verbose=False)
    _init_db()


@app.command("import-vct-abilities")
def import_vct_abilities_cmd(
    tier: str = typer.Option(
        "vct-international",
        help="game-changers | vct-challengers | vct-international",
    ),
    year: int = typer.Option(2024, help="2022, 2023 or 2024"),
    limit: Optional[int] = typer.Option(None, help="max games to import (subset)"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Import Riot's VCT esports telemetry -> derived ability/ult usage (2022-24).

    Historical, one-time (idempotent) import — separate from the live scrape.
    Run `init-db` first so the vct_* tables exist. Example:
        python -m src.vlr.cli import-vct-abilities --tier vct-international --year 2024 --limit 150
    """
    _configure_logging(verbose)
    from .vct.loader import import_vct_games

    def _prog(i: int, total: int, gid: str, status: str) -> None:
        if status in ("ok", "error", "empty") or i % 25 == 0:
            console.print(f"[{i + 1}/{total}] {gid[:22]} -> {status}")

    result = import_vct_games(tier, year, limit=limit, on_progress=_prog)
    console.print(f"[bold green]VCT import done[/]: {result}")
    console.print("[green]Schema created and migrations applied.[/green]")

    # Check whether tier classifications are missing — common after a 7b upgrade
    session = get_session()
    try:
        n_total = session.scalar(select(func.count()).select_from(Event)) or 0
        n_unclassified = session.scalar(
            select(func.count()).select_from(Event).where(Event.tier.is_(None))
        ) or 0
        if n_total > 0 and n_unclassified == n_total:
            console.print(
                "[yellow]All events have no tier yet.[/yellow] "
                "Run `python -m vlr.cli backfill-tiers` to classify them — "
                "required before the AI Match Analysis page will work."
            )
    finally:
        session.close()


@app.command("scrape-recent")
def scrape_recent_cmd(
    pages: int = typer.Option(1, "--pages", "-p"),
    force: bool = typer.Option(False, "--force"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    _configure_logging(verbose)
    stats = scrape_recent(pages=pages, force=force)
    console.print(
        f"\n[bold]Done.[/bold] listed={stats['listed']} skipped={stats['skipped']} "
        f"ok={stats['ok']} failed={stats['failed']} player_rows={stats['player_rows']}"
    )


@app.command("scrape-event")
def scrape_event_cmd(
    event_id: int = typer.Argument(...),
    force: bool = typer.Option(False, "--force"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    _configure_logging(verbose)
    stats = scrape_event(event_id, force=force)
    console.print(
        f"\n[bold]Done.[/bold] listed={stats['listed']} skipped={stats['skipped']} "
        f"ok={stats['ok']} failed={stats['failed']} player_rows={stats['player_rows']}"
    )


@app.command("scrape-events-bulk")
def scrape_events_bulk_cmd(
    file: Path = typer.Argument(..., exists=True, readable=True),
    force: bool = typer.Option(False, "--force"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Read event IDs from a file and scrape each. Progress is saved so re-runs resume."""
    _configure_logging(verbose)
    summary = bulk_scrape_events(file, force=force, resume=True)
    console.print(
        f"\n[bold]Bulk scrape done.[/bold]\n"
        f"  events: total={summary['events_total']} ok={summary['events_ok']} "
        f"skipped_done={summary['events_skipped_done']} failed={summary['events_failed']}\n"
        f"  matches: ok={summary['matches_ok']} failed={summary['matches_failed']}\n"
        f"  player_rows: {summary['player_rows']}"
    )


@app.command("scrape-matches")
def scrape_matches_cmd(
    match_ids: list[int] = typer.Argument(...),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    _configure_logging(verbose)
    stats = scrape_match_ids(match_ids)
    console.print(
        f"\n[bold]Done.[/bold] ok={stats['ok']} failed={stats['failed']} "
        f"player_rows={stats['player_rows']}"
    )


# --- Discovery -----------------------------------------------------------


@app.command("scrape-rankings")
def scrape_rankings_cmd(
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Scrape vlr.gg official team rankings (rating / rank / record) into the
    teams table, across all franchise regions."""
    _configure_logging(verbose)
    stats = scrape_rankings()
    console.print(
        f"\n[bold]Rankings done.[/bold] regions={stats['regions']} "
        f"teams={stats['teams']} created={stats['created']} failed={stats['failed']}"
    )


@app.command("discover-events")
def discover_events_cmd(
    search: Optional[str] = typer.Option(None, "--search", "-s"),
    category: Optional[str] = typer.Option(
        None, "--category", "-c",
        help="international | regional | challengers | gc | all-vct",
    ),
    year: Optional[int] = typer.Option(None, "--year"),
    since_year: Optional[int] = typer.Option(None, "--since"),
    region: Optional[str] = typer.Option(
        None, "--region", help="americas | emea | pacific | cn",
    ),
    status: Optional[str] = typer.Option(
        None, "--status", help="completed | ongoing | upcoming",
    ),
    max_pages: int = typer.Option(20, "--max-pages"),
    limit: Optional[int] = typer.Option(None, "--limit", "-n"),
    output: Optional[Path] = typer.Option(None, "--output", "-o"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Browse vlr.gg's events page with rich filtering. Does NOT save to DB.

    Categories (name-based classification):
      international = Valorant Masters, Champions, Kickoff
      regional      = VCT YYYY: Region Stage N (the main regional leagues)
      challengers   = Challengers / VCL events
      gc            = Game Changers events
      all-vct       = anything under vlr.gg's "VCT" tier (international + regional)
    """
    _configure_logging(verbose)
    valid_categories = {"international", "regional", "challengers", "gc", "all-vct"}
    if category and category.lower() not in valid_categories:
        console.print(
            f"[red]Unknown category {category!r}. "
            f"Choose from: {', '.join(sorted(valid_categories))}[/red]"
        )
        raise typer.Exit(1)

    try:
        events = discover_events(
            search=search,
            category=category,
            year=year,
            since_year=since_year,
            region=region,
            status=status,
            max_pages=max_pages,
            limit=limit,
        )
    except Exception:
        console.print("[red]Failed to fetch events from vlr.gg.[/red]")
        raise

    if not events:
        console.print(
            f"[yellow]No events matched the filters.[/yellow] "
            f"Try widening with --max-pages, dropping --category, or running "
            f"without --since to see what's returned."
        )
        return

    t = Table(title=f"Events on vlr.gg ({len(events)} matched)")
    t.add_column("Event ID")
    t.add_column("Name")
    t.add_column("Category")
    t.add_column("Year", justify="right")
    t.add_column("Region")
    t.add_column("Status")
    t.add_column("Dates")
    for ev in events:
        t.add_row(
            str(ev.event_id),
            ev.name[:60],
            ev.category or "-",
            str(ev.year) if ev.year else "-",
            ev.region or "-",
            ev.status or "-",
            ev.date_range or "-",
        )
    console.print(t)

    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("w", encoding="utf-8") as f:
            f.write(
                f"# Event IDs from discover-events\n"
                f"#   category={category or 'any'}  year={year or 'any'}  "
                f"since={since_year or '-'}  region={region or 'any'}  "
                f"search={search!r}\n"
                f"# Total: {len(events)} events\n#\n"
            )
            for ev in events:
                f.write(
                    f"{ev.event_id}  # {ev.name} "
                    f"({ev.year or '?'}, {ev.region or '?'}, {ev.category or '?'})\n"
                )
        console.print(f"\n[green]Wrote {len(events)} event IDs to {output}[/green]")
        console.print(
            f"[dim]Review the file (delete duds), then run:[/dim]\n"
            f"  python -m vlr.cli scrape-events-bulk {output}"
        )


@app.command("list-events")
def list_events_cmd() -> None:
    _configure_logging(verbose=False)
    session = get_session()
    try:
        rows = (
            session.execute(
                select(
                    Event.id, Event.name,
                    func.count(Match.id).label("n_matches"),
                    func.min(Match.match_datetime).label("earliest"),
                    func.max(Match.match_datetime).label("latest"),
                )
                .join(Match, Match.event_id == Event.id)
                .group_by(Event.id, Event.name)
                .order_by(desc("latest"))
            ).all()
        )
        if not rows:
            console.print("[yellow]No events in the local DB yet.[/yellow]")
            return
        t = Table(title="Events in local DB")
        t.add_column("Event ID")
        t.add_column("Name")
        t.add_column("Matches", justify="right")
        t.add_column("Date range")
        for event_id, name, n_matches, earliest, latest in rows:
            date_range = "-"
            if earliest and latest:
                if earliest.date() == latest.date():
                    date_range = str(earliest.date())
                else:
                    date_range = f"{earliest.date()} → {latest.date()}"
            t.add_row(str(event_id), (name or "")[:60], str(n_matches), date_range)
        console.print(t)
    finally:
        session.close()


# --- Maintenance ---------------------------------------------------------


@app.command("repair-events")
def repair_events_cmd(verbose: bool = typer.Option(False, "--verbose", "-v")) -> None:
    _configure_logging(verbose)
    stats = repair_event_names()
    if stats["checked"] == 0:
        console.print("[green]No broken event names found.[/green]")
        return
    console.print(
        f"\n[bold]Done.[/bold] checked={stats['checked']} fixed={stats['fixed']} "
        f"no_match={stats['no_match']} failed={stats['failed']}"
    )


@app.command("audit")
def audit_cmd() -> None:
    _configure_logging(verbose=False)
    session = get_session()
    try:
        findings: list[tuple[str, int, str]] = []

        bad_events = session.execute(
            select(Event.id, Event.name).where(
                Event.name.in_(["upcoming", "completed", "live", "final", "tbd", "ongoing", ""])
            )
        ).all()
        if bad_events:
            sample = ", ".join(f"{r[0]}={r[1]!r}" for r in bad_events[:3])
            findings.append(("Events with status-word names — run `repair-events`",
                             len(bad_events), sample))

        n_no_maps = session.scalar(
            select(func.count(Match.id)).where(
                ~Match.id.in_(select(MapPlayed.match_id).distinct())
            )
        ) or 0
        if n_no_maps:
            findings.append(("Matches with no maps", n_no_maps, ""))

        n_no_score = session.scalar(
            select(func.count(Match.id)).where(
                or_(Match.score_a.is_(None), Match.score_b.is_(None))
            )
        ) or 0
        if n_no_score:
            findings.append(("Matches with null score", n_no_score, ""))

        n_null_rating = session.scalar(
            select(func.count(PlayerMapStat.id)).where(PlayerMapStat.rating.is_(None))
        ) or 0
        if n_null_rating:
            findings.append(("Player-map rows with null rating", n_null_rating, ""))

        wrong_count_maps = session.execute(sql_text("""
            SELECT mp.match_id, mp.map_name, COUNT(pms.id) AS n_players
            FROM maps_played mp
            LEFT JOIN player_map_stats pms ON pms.map_id = mp.id
            GROUP BY mp.id, mp.match_id, mp.map_name
            HAVING COUNT(pms.id) NOT IN (0, 10)
            ORDER BY n_players
            LIMIT 5
        """)).all()
        if wrong_count_maps:
            sample = "; ".join(f"match {r[0]} {r[1]}: {r[2]} rows" for r in wrong_count_maps[:3])
            findings.append(("Maps with player count != 10", len(wrong_count_maps), sample))

        n_empty_maps = session.scalar(sql_text("""
            SELECT COUNT(*) FROM maps_played mp
            WHERE NOT EXISTS (SELECT 1 FROM player_map_stats pms WHERE pms.map_id = mp.id)
        """)) or 0
        if n_empty_maps:
            findings.append(("Maps with NO player stats", n_empty_maps, ""))

        if not findings:
            console.print("[green]No data-quality issues detected.[/green]")
            return
        t = Table(title="Data-quality audit")
        t.add_column("Issue", style="bold")
        t.add_column("Count", justify="right")
        t.add_column("Examples")
        for label, count, sample in findings:
            t.add_row(label, str(count), sample)
        console.print(t)
    finally:
        session.close()


@app.command("stats")
def stats_cmd() -> None:
    _configure_logging(verbose=False)
    session = get_session()
    try:
        counts = [
            ("Matches",         session.scalar(select(func.count()).select_from(Match)) or 0),
            ("Teams",           session.scalar(select(func.count()).select_from(Team)) or 0),
            ("Events",          session.scalar(select(func.count()).select_from(Event)) or 0),
            ("Players",         session.scalar(select(func.count()).select_from(Player)) or 0),
            ("Maps played",     session.scalar(select(func.count()).select_from(MapPlayed)) or 0),
            ("Player-map rows", session.scalar(select(func.count()).select_from(PlayerMapStat)) or 0),
            ("Veto actions",    session.scalar(select(func.count()).select_from(VetoAction)) or 0),
        ]
        table = Table(title="Database contents", show_header=False)
        table.add_column("Entity", style="bold")
        table.add_column("Rows", justify="right")
        for label, n in counts:
            table.add_row(label, str(n))
        console.print(table)
    finally:
        session.close()


@app.command("show-event")
def show_event_cmd(
    event_id: int = typer.Argument(...),
    min_maps: int = typer.Option(3, "--min-maps"),
    top: int = typer.Option(10, "--top"),
) -> None:
    _configure_logging(verbose=False)
    session = get_session()
    try:
        event = session.get(Event, event_id)
        if event is None:
            console.print(f"[red]Event {event_id} not found.[/red]")
            return
        console.print(f"\n[bold]{event.name}[/bold]   [dim]event_id={event_id}[/dim]")
        matches = session.execute(
            select(Match).where(Match.event_id == event_id)
            .order_by(desc(Match.match_datetime))
        ).scalars().all()
        if not matches:
            console.print("[yellow]No matches in DB for this event.[/yellow]")
            return
        t = Table(title=f"Matches ({len(matches)})")
        t.add_column("Match ID")
        t.add_column("Date")
        t.add_column("Stage")
        t.add_column("Match")
        t.add_column("Score")
        for m in matches:
            t.add_row(
                str(m.id),
                str(m.match_datetime.date()) if m.match_datetime else "-",
                (m.stage or "-")[:25],
                f"{m.team_a_name} vs {m.team_b_name}",
                f"{m.score_a}-{m.score_b}",
            )
        console.print(t)
    finally:
        session.close()


@app.command("show-match")
def show_match_cmd(match_id: int) -> None:
    _configure_logging(verbose=False)
    session = get_session()
    try:
        m = session.get(Match, match_id)
        if m is None:
            console.print(f"[red]Match {match_id} not found.[/red]")
            return
        score_str = f"{m.score_a if m.score_a is not None else '?'} : {m.score_b if m.score_b is not None else '?'}"
        console.print(f"\n[bold]{m.team_a_name}  {score_str}  {m.team_b_name}[/bold]   "
                      f"Bo{m.best_of or '?'}   {m.stage or ''}")
        if m.event:
            console.print(f"[dim]{m.event.name}[/dim]")
        maps = session.execute(
            select(MapPlayed).where(MapPlayed.match_id == match_id).order_by(MapPlayed.map_index)
        ).scalars().all()
        for map_row in maps:
            console.print(
                f"\n[bold cyan]Map {map_row.map_index}: {map_row.map_name}[/bold cyan]   "
                f"{map_row.score_a}-{map_row.score_b}   picked by {map_row.picked_by or '?'}"
            )
            stats = session.execute(
                select(PlayerMapStat).where(PlayerMapStat.map_id == map_row.id)
            ).scalars().all()
            by_team: dict[str, list[PlayerMapStat]] = {}
            for s in stats:
                by_team.setdefault(s.team_name or "?", []).append(s)
            for team_name, team_stats in by_team.items():
                t = Table(title=team_name, title_justify="left")
                t.add_column("Player")
                t.add_column("Agent")
                t.add_column("R", justify="right")
                t.add_column("ACS", justify="right")
                t.add_column("K", justify="right")
                t.add_column("D", justify="right")
                t.add_column("A", justify="right")
                team_stats.sort(key=lambda s: s.rating or 0, reverse=True)
                for s in team_stats:
                    player = session.get(Player, s.player_id)
                    t.add_row(
                        player.name if player else f"id={s.player_id}",
                        s.agent or "-",
                        f"{s.rating:.2f}" if s.rating is not None else "-",
                        str(s.acs) if s.acs is not None else "-",
                        str(s.kills) if s.kills is not None else "-",
                        str(s.deaths) if s.deaths is not None else "-",
                        str(s.assists) if s.assists is not None else "-",
                    )
                console.print(t)
    finally:
        session.close()


_METRIC_COLUMNS = {
    "rating": PlayerMapStat.rating, "acs": PlayerMapStat.acs,
    "adr": PlayerMapStat.adr, "kast": PlayerMapStat.kast,
    "hs_pct": PlayerMapStat.hs_pct, "kills": PlayerMapStat.kills,
}


@app.command("top-players")
def top_players_cmd(
    metric: str = typer.Option("rating"),
    min_maps: int = typer.Option(5, "--min-maps"),
    limit: int = typer.Option(10),
    event: Optional[int] = typer.Option(None, "--event", "-e"),
) -> None:
    _configure_logging(verbose=False)
    if metric not in _METRIC_COLUMNS:
        console.print(f"[red]Unknown metric: {metric}[/red]")
        raise typer.Exit(1)
    col = _METRIC_COLUMNS[metric]
    session = get_session()
    try:
        if event is None:
            query = (
                select(
                    PlayerMapStat.player_id,
                    func.count(PlayerMapStat.id).label("n_maps"),
                    func.avg(col).label("avg_metric"),
                )
                .where(col.is_not(None))
                .group_by(PlayerMapStat.player_id)
                .having(func.count(PlayerMapStat.id) >= min_maps)
                .order_by(desc("avg_metric"))
                .limit(limit)
            )
            title = f"Top {limit} by avg {metric} (min {min_maps} maps)"
        else:
            query = (
                select(
                    PlayerMapStat.player_id,
                    func.count(PlayerMapStat.id).label("n_maps"),
                    func.avg(col).label("avg_metric"),
                )
                .join(Match, Match.id == PlayerMapStat.match_id)
                .where(col.is_not(None), Match.event_id == event)
                .group_by(PlayerMapStat.player_id)
                .having(func.count(PlayerMapStat.id) >= min_maps)
                .order_by(desc("avg_metric"))
                .limit(limit)
            )
            event_obj = session.get(Event, event)
            title = f"{event_obj.name if event_obj else f'event {event}'} — top {limit}"

        rows = session.execute(query).all()
        t = Table(title=title)
        t.add_column("Player")
        t.add_column("Maps", justify="right")
        t.add_column(f"Avg {metric}", justify="right")
        for player_id, n_maps, avg in rows:
            player = session.get(Player, player_id)
            pname = player.name if player else f"id={player_id}"
            t.add_row(pname, str(n_maps), f"{float(avg):.2f}" if avg else "-")
        console.print(t)
    finally:
        session.close()


# --- ML commands ----------------------------------------------------------


@app.command("backfill-tiers")
def backfill_tiers_cmd(verbose: bool = typer.Option(False, "--verbose", "-v")) -> None:
    """Classify every event by tier and populate Event.tier.

    Run this once after upgrading to 7b. Then re-run compute-features --force
    and train-model to rebuild the model with tier-aware features.
    """
    _configure_logging(verbose)
    from .ml.tiers import classify_event_tier

    session = get_session()
    try:
        # Add the tier column if it's missing (for users upgrading mid-project)
        session.execute(sql_text("""
            ALTER TABLE events ADD COLUMN IF NOT EXISTS tier VARCHAR(32)
        """))
        session.commit()

        events = session.execute(select(Event)).scalars().all()
        counts = {"international": 0, "tier1": 0, "tier2": 0, "unclassified": 0}

        for event in events:
            classified = classify_event_tier(event.name)
            if classified:
                event.tier = classified
                counts[classified] += 1
            else:
                event.tier = None
                counts["unclassified"] += 1

        session.commit()

        t = Table(title="Tier classification results")
        t.add_column("Tier", style="bold")
        t.add_column("Events", justify="right")
        for k, v in counts.items():
            t.add_row(k, str(v))
        console.print(t)
        console.print(
            "\n[dim]Next:[/dim] run `compute-features --force` to rebuild "
            "feature snapshots with tier-aware fields, then `train-model`."
        )
    finally:
        session.close()


@app.command("backfill-regions")
def backfill_regions_cmd(verbose: bool = typer.Option(False, "--verbose", "-v")) -> None:
    """Classify every team by region using their match history.

    For each team: looks at the regional events they've appeared in
    (excluding international events like Masters/Champions/Kickoff)
    and picks the region they appear in most often.

    Run this once after upgrading. Re-run any time after big scrapes
    to keep regions current.
    """
    _configure_logging(verbose)
    from .ml.tiers import classify_event_region
    from collections import Counter

    session = get_session()
    try:
        # Ensure the column exists (idempotent)
        session.execute(sql_text(
            "ALTER TABLE teams ADD COLUMN IF NOT EXISTS region VARCHAR(64)"
        ))
        session.commit()

        # For each team, count how many matches they played in each region
        rows = session.execute(sql_text("""
            SELECT m.team_a_id AS team_id, e.name AS event_name
            FROM matches m
            JOIN events e ON e.id = m.event_id
            WHERE m.team_a_id IS NOT NULL

            UNION ALL

            SELECT m.team_b_id AS team_id, e.name AS event_name
            FROM matches m
            JOIN events e ON e.id = m.event_id
            WHERE m.team_b_id IS NOT NULL
        """)).all()

        per_team: dict[int, Counter] = {}
        for team_id, event_name in rows:
            region = classify_event_region(event_name)
            if region is None:
                continue
            per_team.setdefault(team_id, Counter())[region] += 1

        # Pick the most common region per team
        counts = {"americas": 0, "emea": 0, "pacific": 0, "china": 0, "unclassified": 0}
        for team_id, region_counts in per_team.items():
            top_region, _ = region_counts.most_common(1)[0]
            session.execute(sql_text(
                "UPDATE teams SET region = :r WHERE id = :tid"
            ), {"r": top_region, "tid": team_id})
            counts[top_region] += 1

        # Count teams with no regional events
        total_teams = session.scalar(select(func.count()).select_from(Team)) or 0
        counts["unclassified"] = total_teams - sum(
            v for k, v in counts.items() if k != "unclassified"
        )

        session.commit()

        t = Table(title="Team region classification results")
        t.add_column("Region", style="bold")
        t.add_column("Teams", justify="right")
        for k, v in counts.items():
            t.add_row(k, str(v))
        console.print(t)
    finally:
        session.close()


@app.command("scrape-recent-results")
def scrape_recent_results_cmd(
    pages: int = typer.Option(1, "--pages", "-p"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Scrape vlr.gg /matches/results for the most recent completed matches.

    Wraps the same logic the live results scheduler uses. Run it manually
    once to verify it works before letting the API auto-scrape.
    """
    _configure_logging(verbose)
    from .scraping.pipeline import scrape_recent_results
    n_new = scrape_recent_results(pages=pages)
    console.print(f"[green]Done.[/green] {n_new} new matches added to the database.")


@app.command("backfill-player-profiles")
def backfill_player_profiles_cmd(
    limit: Optional[int] = typer.Option(None, "--limit", "-n",
        help="Only scrape this many players (for testing). Omit to scrape all."),
    force: bool = typer.Option(False, "--force",
        help="Re-scrape players that already have an image_url"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Scrape vlr.gg for every player's photo, country flag, and real name.

    Resumable: by default skips players who already have an image_url, so
    if this crashes halfway you can just re-run and it picks up where it left off.

    With 7,000+ players and a 2-second delay per request, expect this to take
    around 4 hours end to end. Run it in a screen/tmux session or overnight.
    Use --limit 20 first to verify the scraper actually works on real pages.
    """
    _configure_logging(verbose)
    from .scraping.pipeline import backfill_player_profiles
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, \
        TimeRemainingColumn, MofNCompleteColumn

    counts_seen = {"ok": 0, "no_data": 0, "failed": 0}

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]Scraping players"),
        BarColumn(),
        MofNCompleteColumn(),
        TimeRemainingColumn(),
        TextColumn("· last: pid={task.fields[last_pid]} [{task.fields[last_status]}]"),
        console=console,
    ) as progress:
        task = progress.add_task("scrape", total=None, last_pid="-", last_status="-")

        def cb(i, total, pid, status):
            if progress.tasks[task].total is None:
                progress.update(task, total=total)
            counts_seen[status] = counts_seen.get(status, 0) + 1
            progress.update(task, advance=1, last_pid=str(pid), last_status=status)

        stats = backfill_player_profiles(limit=limit, force=force, on_progress=cb)

    t = Table(title="Player profile backfill")
    t.add_column("Metric", style="bold")
    t.add_column("Count", justify="right")
    for k, v in stats.items():
        t.add_row(k, str(v))
    console.print(t)


@app.command("backfill-team-logos")
def backfill_team_logos_cmd(
    limit: Optional[int] = typer.Option(None, "--limit", "-n"),
    force: bool = typer.Option(False, "--force"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Scrape vlr.gg for every team's logo URL and country.

    1,500-ish teams at 2-second delay ~= 50 minutes. Faster than player profiles.
    """
    _configure_logging(verbose)
    from .scraping.pipeline import backfill_team_logos
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, \
        TimeRemainingColumn, MofNCompleteColumn

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]Scraping teams"),
        BarColumn(),
        MofNCompleteColumn(),
        TimeRemainingColumn(),
        TextColumn("· last: tid={task.fields[last_tid]} [{task.fields[last_status]}]"),
        console=console,
    ) as progress:
        task = progress.add_task("scrape", total=None, last_tid="-", last_status="-")

        def cb(i, total, tid, status):
            if progress.tasks[task].total is None:
                progress.update(task, total=total)
            progress.update(task, advance=1, last_tid=str(tid), last_status=status)

        stats = backfill_team_logos(limit=limit, force=force, on_progress=cb)

    t = Table(title="Team logo backfill")
    t.add_column("Metric", style="bold")
    t.add_column("Count", justify="right")
    for k, v in stats.items():
        t.add_row(k, str(v))
    console.print(t)


# --- compute-features stays below ---------------------------------------


@app.command("compute-features")
def compute_features_cmd(
    force: bool = typer.Option(False, "--force", help="Recompute features that already exist"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Compute and cache feature vectors for every completed match.

    Idempotent — skips matches already cached unless --force. After scraping
    new matches, re-run this to backfill features for the new ones.
    """
    _configure_logging(verbose)
    from .ml.features import backfill_features
    stats = backfill_features(force=force)
    console.print(
        f"\n[bold]Done.[/bold] total={stats['total']} computed={stats['computed']} "
        f"skipped={stats['skipped']} failed={stats['failed']}"
    )


@app.command("train-model")
def train_model_cmd(
    test_fraction: float = typer.Option(0.2, "--test-fraction"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Train the XGBoost model on all cached features.

    Uses a temporal split (latest test_fraction of matches as hold-out).
    Saves the model to data/models/xgboost_v1.pkl.
    """
    _configure_logging(verbose)
    from .ml.model import train_model
    try:
        result = train_model(test_fraction=test_fraction)
    except RuntimeError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1)

    t = Table(title="Training results", show_header=False)
    t.add_column("Metric", style="bold")
    t.add_column("Value")
    t.add_row("Model version", result.model_version)
    t.add_row("Training rows", f"{result.n_train:,}")
    t.add_row("Test rows", f"{result.n_test:,}")
    t.add_row("Train accuracy", f"{result.train_accuracy:.3f}")
    t.add_row("Test accuracy", f"{result.test_accuracy:.3f}")
    t.add_row("Test log-loss", f"{result.test_log_loss:.3f}")
    t.add_row("Test Brier score", f"{result.test_brier:.3f}")
    console.print(t)

    fi = Table(title="Top 15 feature importances")
    fi.add_column("Feature")
    fi.add_column("Importance", justify="right")
    for k, v in list(result.feature_importances.items())[:15]:
        fi.add_row(k, f"{v:.4f}")
    console.print(fi)


@app.command("evaluate-model")
def evaluate_model_cmd() -> None:
    """Print the saved evaluation metrics from the last training run."""
    _configure_logging(verbose=False)
    from .ml.model import evaluate_model
    result = evaluate_model()
    if result is None:
        console.print(
            "[yellow]No trained model found. "
            "Run `train-model` first.[/yellow]"
        )
        return

    t = Table(title="Saved model metrics", show_header=False)
    t.add_column("Metric", style="bold")
    t.add_column("Value")
    t.add_row("Model version", str(result.get("model_version", "?")))
    t.add_row("Trained at", str(result.get("trained_at", "?")))
    t.add_row("Train rows", f"{result.get('n_train', 0):,}")
    t.add_row("Test rows", f"{result.get('n_test', 0):,}")
    t.add_row("Train accuracy", f"{result.get('train_accuracy', 0):.3f}")
    t.add_row("Test accuracy", f"{result.get('test_accuracy', 0):.3f}")
    t.add_row("Test log-loss", f"{result.get('test_log_loss', 0):.3f}")
    t.add_row("Test Brier", f"{result.get('test_brier', 0):.3f}")
    console.print(t)


@app.command("explain-match")
def explain_match_cmd(
    match_id: int = typer.Argument(...),
    regenerate: bool = typer.Option(False, "--regenerate", "-r",
                                    help="Force a fresh OpenAI call (ignores cache)"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Generate AI analysis for a match. Tests the OpenAI pipeline from the CLI.

    Requires OPENAI_API_KEY to be set in .env or the environment.
    """
    _configure_logging(verbose)
    from .ml.explain import explain_match
    from .config import settings

    if not settings.openai_api_key:
        console.print(
            "[red]OPENAI_API_KEY is not set.[/red] "
            "Add it to your .env file: OPENAI_API_KEY=sk-..."
        )
        raise typer.Exit(1)

    console.print(f"Generating analysis for match {match_id} "
                  f"using {settings.openai_model}...")
    result = explain_match(match_id, force_regenerate=regenerate)
    if result is None:
        console.print("[red]Analysis failed. Check logs above.[/red]")
        raise typer.Exit(1)

    console.print(f"\n[bold]Summary[/bold]")
    console.print(result.summary)

    console.print(f"\n[bold]Key factors[/bold]")
    for f in result.key_factors:
        console.print(f"  · {f}")

    console.print(f"\n[bold]Standout players[/bold]")
    for p in result.standout_players:
        console.print(f"  ▲ {p}")

    console.print(f"\n[bold]Underperformers[/bold]")
    for p in result.underperformers:
        console.print(f"  ▼ {p}")


if __name__ == "__main__":
    app()

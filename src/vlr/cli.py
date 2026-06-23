"""CLI entry point.

Usage examples:
    python -m vlr.cli init-db
    python -m vlr.cli scrape-recent --pages 1
    python -m vlr.cli scrape-event 2765                     # incremental by default
    python -m vlr.cli scrape-event 2765 --force             # re-fetch everything
    python -m vlr.cli scrape-matches 670471 670470
    python -m vlr.cli discover-events --search masters
    python -m vlr.cli list-events
    python -m vlr.cli show-event 2765
    python -m vlr.cli show-match 670471
    python -m vlr.cli stats
    python -m vlr.cli top-players --metric rating --min-maps 5
    python -m vlr.cli top-players --event 2765 --metric rating
    python -m vlr.cli audit                                 # data-quality report
    python -m vlr.cli repair-events                         # fix bad event names
"""
from __future__ import annotations

import logging
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
    discover_events,
    repair_event_names,
    scrape_event,
    scrape_match_ids,
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
    """Create all tables. Safe to run multiple times."""
    _configure_logging(verbose=False)
    _init_db()
    console.print("[green]Schema created (or already present).[/green]")


@app.command("scrape-recent")
def scrape_recent_cmd(
    pages: int = typer.Option(1, "--pages", "-p"),
    force: bool = typer.Option(False, "--force", help="Re-scrape matches already in DB"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Scrape recent completed matches. Incremental by default."""
    _configure_logging(verbose)
    stats = scrape_recent(pages=pages, force=force)
    console.print(
        f"\n[bold]Done.[/bold] listed={stats['listed']} skipped={stats['skipped']} "
        f"ok={stats['ok']} failed={stats['failed']} player_rows={stats['player_rows']}"
    )


@app.command("scrape-event")
def scrape_event_cmd(
    event_id: int = typer.Argument(...),
    force: bool = typer.Option(False, "--force", help="Re-scrape matches already in DB"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Scrape every match from one event. Incremental by default (skips matches
    already in DB). Pass --force to re-fetch everything (useful after parser fixes)."""
    _configure_logging(verbose)
    stats = scrape_event(event_id, force=force)
    console.print(
        f"\n[bold]Done.[/bold] listed={stats['listed']} skipped={stats['skipped']} "
        f"ok={stats['ok']} failed={stats['failed']} player_rows={stats['player_rows']}"
    )


@app.command("scrape-matches")
def scrape_matches_cmd(
    match_ids: list[int] = typer.Argument(...),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Scrape specific match IDs (always re-fetches — you named them explicitly)."""
    _configure_logging(verbose)
    stats = scrape_match_ids(match_ids)
    console.print(
        f"\n[bold]Done.[/bold] ok={stats['ok']} failed={stats['failed']} "
        f"player_rows={stats['player_rows']}"
    )


# --- Discovery / browsing ------------------------------------------------


@app.command("discover-events")
def discover_events_cmd(
    search: Optional[str] = typer.Option(None, "--search", "-s"),
    limit: int = typer.Option(25, "--limit", "-n"),
) -> None:
    """Browse vlr.gg's events page to find event IDs."""
    _configure_logging(verbose=False)
    try:
        pairs = discover_events(search=search, limit=limit)
    except Exception:
        console.print("[red]Failed to fetch events from vlr.gg.[/red]")
        raise

    if not pairs:
        console.print(
            f"[yellow]No events found{f' for {search!r}' if search else ''}.[/yellow] "
            f"Try a different search or browse https://www.vlr.gg/events manually."
        )
        return

    t = Table(title=f"Events on vlr.gg{f' (matching {search!r})' if search else ''}")
    t.add_column("Event ID")
    t.add_column("Name")
    for eid, name in pairs:
        t.add_row(str(eid), name[:80])
    console.print(t)


@app.command("list-events")
def list_events_cmd() -> None:
    """List events that already have matches in the local DB."""
    _configure_logging(verbose=False)
    session = get_session()
    try:
        rows = (
            session.execute(
                select(
                    Event.id,
                    Event.name,
                    func.count(Match.id).label("n_matches"),
                    func.min(Match.match_datetime).label("earliest"),
                    func.max(Match.match_datetime).label("latest"),
                )
                .join(Match, Match.event_id == Event.id)
                .group_by(Event.id, Event.name)
                .order_by(desc("latest"))
            )
            .all()
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
def repair_events_cmd(
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Fix events whose name is a status word ('upcoming', 'completed', etc.)
    by re-parsing one match per event. Cheap — about 1 HTTP request per event."""
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
    """Run data-quality checks and print a report.

    This is the kind of check your dissertation methodology chapter will need
    to demonstrate — evidence that you understand your data before modelling it.
    """
    _configure_logging(verbose=False)
    session = get_session()
    try:
        findings: list[tuple[str, int, str]] = []

        # 1. Events with status-word names (parser artifacts)
        bad_events = (
            session.execute(
                select(Event.id, Event.name).where(
                    Event.name.in_(["upcoming", "completed", "live", "final", "tbd", ""])
                )
            )
            .all()
        )
        if bad_events:
            sample = ", ".join(f"{r[0]}={r[1]!r}" for r in bad_events[:3])
            findings.append(
                ("Events with status-word names — run `repair-events`",
                 len(bad_events), sample)
            )

        # 2. Matches with no maps (forfeits or scraping failures)
        n_no_maps = session.scalar(
            select(func.count(Match.id)).where(
                ~Match.id.in_(select(MapPlayed.match_id).distinct())
            )
        ) or 0
        if n_no_maps:
            findings.append(
                ("Matches with no maps (forfeit / walkover / parse failure)",
                 n_no_maps, "")
            )

        # 3. Matches missing scores
        n_no_score = session.scalar(
            select(func.count(Match.id)).where(
                or_(Match.score_a.is_(None), Match.score_b.is_(None))
            )
        ) or 0
        if n_no_score:
            findings.append(("Matches with null score", n_no_score, ""))

        # 4. Player-map rows with null rating
        n_null_rating = session.scalar(
            select(func.count(PlayerMapStat.id)).where(PlayerMapStat.rating.is_(None))
        ) or 0
        if n_null_rating:
            findings.append(("Player-map rows with null rating", n_null_rating, ""))

        # 5. Maps with player count != 10
        wrong_count_maps = session.execute(
            sql_text(
                """
                SELECT mp.match_id, mp.map_name, COUNT(pms.id) AS n_players
                FROM maps_played mp
                LEFT JOIN player_map_stats pms ON pms.map_id = mp.id
                GROUP BY mp.id, mp.match_id, mp.map_name
                HAVING COUNT(pms.id) NOT IN (0, 10)
                ORDER BY n_players
                LIMIT 5
                """
            )
        ).all()
        if wrong_count_maps:
            sample = "; ".join(
                f"match {r[0]} {r[1]}: {r[2]} rows"
                for r in wrong_count_maps[:3]
            )
            findings.append(
                ("Maps with player count != 10 (should be 5+5)",
                 len(wrong_count_maps), sample)
            )

        # 6. Maps with no player stats at all (parser failure)
        n_empty_maps = session.scalar(
            sql_text(
                """
                SELECT COUNT(*) FROM maps_played mp
                WHERE NOT EXISTS (
                    SELECT 1 FROM player_map_stats pms WHERE pms.map_id = mp.id
                )
                """
            )
        ) or 0
        if n_empty_maps:
            findings.append(("Maps with NO player stats (parser failed)", n_empty_maps, ""))

        # 7. Matches with no event
        n_no_event = session.scalar(
            select(func.count(Match.id)).where(Match.event_id.is_(None))
        ) or 0
        if n_no_event:
            findings.append(("Matches with no event_id", n_no_event, ""))

        # 8. Matches with no team_a_id or team_b_id
        n_no_team = session.scalar(
            select(func.count(Match.id)).where(
                or_(Match.team_a_id.is_(None), Match.team_b_id.is_(None))
            )
        ) or 0
        if n_no_team:
            findings.append(("Matches missing a team_id", n_no_team, ""))

        # 9. Forfeit detection (one team has 0 maps wins, other has the BO count)
        # Light-touch check: any match where score_a + score_b == 0
        n_zero = session.scalar(
            select(func.count(Match.id)).where(
                Match.score_a == 0, Match.score_b == 0
            )
        ) or 0
        if n_zero:
            findings.append(("Matches with score 0-0 (likely walkover / TBD)", n_zero, ""))

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


# --- Inspection / analytics ----------------------------------------------


@app.command("stats")
def stats_cmd() -> None:
    """Print a summary of what's in the database."""
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

        recent = (
            session.execute(select(Match).order_by(desc(Match.scraped_at)).limit(5))
            .scalars()
            .all()
        )
        if recent:
            t = Table(title="Recent matches (latest 5 by scraped_at)")
            t.add_column("ID")
            t.add_column("Match")
            t.add_column("Score")
            t.add_column("Bo")
            t.add_column("Stage")
            t.add_column("Event")
            for m in recent:
                t.add_row(
                    str(m.id),
                    f"{m.team_a_name} vs {m.team_b_name}",
                    f"{m.score_a}-{m.score_b}",
                    str(m.best_of) if m.best_of else "?",
                    (m.stage or "-")[:30],
                    (m.event.name if m.event else "-")[:40],
                )
            console.print(t)
    finally:
        session.close()


@app.command("show-event")
def show_event_cmd(
    event_id: int = typer.Argument(...),
    min_maps: int = typer.Option(3, "--min-maps"),
    top: int = typer.Option(10, "--top"),
) -> None:
    """Show all matches and a leaderboard for one event."""
    _configure_logging(verbose=False)
    session = get_session()
    try:
        event = session.get(Event, event_id)
        if event is None:
            console.print(f"[red]Event {event_id} not found in DB.[/red]")
            return

        console.print(f"\n[bold]{event.name}[/bold]   [dim]event_id={event_id}[/dim]")

        matches = (
            session.execute(
                select(Match)
                .where(Match.event_id == event_id)
                .order_by(desc(Match.match_datetime))
            )
            .scalars()
            .all()
        )
        if not matches:
            console.print("[yellow]No matches in DB for this event.[/yellow]")
            return

        t = Table(title=f"Matches ({len(matches)})")
        t.add_column("Match ID")
        t.add_column("Date")
        t.add_column("Stage")
        t.add_column("Match")
        t.add_column("Score")
        t.add_column("Bo")
        for m in matches:
            t.add_row(
                str(m.id),
                str(m.match_datetime.date()) if m.match_datetime else "-",
                (m.stage or "-")[:25],
                f"{m.team_a_name} vs {m.team_b_name}",
                f"{m.score_a}-{m.score_b}",
                str(m.best_of) if m.best_of else "?",
            )
        console.print(t)

        top_rows = (
            session.execute(
                select(
                    PlayerMapStat.player_id,
                    func.count(PlayerMapStat.id).label("n_maps"),
                    func.avg(PlayerMapStat.rating).label("avg_rating"),
                    func.avg(PlayerMapStat.acs).label("avg_acs"),
                    func.avg(PlayerMapStat.adr).label("avg_adr"),
                )
                .join(Match, Match.id == PlayerMapStat.match_id)
                .where(Match.event_id == event_id, PlayerMapStat.rating.is_not(None))
                .group_by(PlayerMapStat.player_id)
                .having(func.count(PlayerMapStat.id) >= min_maps)
                .order_by(desc("avg_rating"))
                .limit(top)
            )
            .all()
        )
        if top_rows:
            t = Table(title=f"Top {top} players by avg rating (min {min_maps} maps)")
            t.add_column("Player")
            t.add_column("Maps", justify="right")
            t.add_column("Avg Rating", justify="right")
            t.add_column("Avg ACS", justify="right")
            t.add_column("Avg ADR", justify="right")
            for player_id, n_maps, avg_rating, avg_acs, avg_adr in top_rows:
                player = session.get(Player, player_id)
                pname = player.name if player else f"id={player_id}"
                t.add_row(
                    pname,
                    str(n_maps),
                    f"{float(avg_rating):.2f}" if avg_rating is not None else "-",
                    f"{float(avg_acs):.0f}" if avg_acs is not None else "-",
                    f"{float(avg_adr):.1f}" if avg_adr is not None else "-",
                )
            console.print(t)
    finally:
        session.close()


@app.command("show-match")
def show_match_cmd(match_id: int) -> None:
    """Display a single match in detail with per-map player stats."""
    _configure_logging(verbose=False)
    session = get_session()
    try:
        m = session.get(Match, match_id)
        if m is None:
            console.print(f"[red]Match {match_id} not found in DB.[/red]")
            return

        score_str = (
            f"{m.score_a if m.score_a is not None else '?'} : "
            f"{m.score_b if m.score_b is not None else '?'}"
        )
        console.print()
        console.print(
            f"[bold]{m.team_a_name}  {score_str}  {m.team_b_name}[/bold]   "
            f"Bo{m.best_of or '?'}   {m.stage or ''}"
        )
        if m.event:
            console.print(f"[dim]{m.event.name}[/dim]")
        if m.patch:
            console.print(f"[dim]Patch {m.patch}[/dim]")

        maps = (
            session.execute(
                select(MapPlayed)
                .where(MapPlayed.match_id == match_id)
                .order_by(MapPlayed.map_index)
            )
            .scalars()
            .all()
        )

        for map_row in maps:
            console.print()
            console.print(
                f"[bold cyan]Map {map_row.map_index}: {map_row.map_name}[/bold cyan]   "
                f"{map_row.score_a}-{map_row.score_b}   "
                f"picked by {map_row.picked_by or '?'}"
            )

            stats = (
                session.execute(
                    select(PlayerMapStat).where(PlayerMapStat.map_id == map_row.id)
                )
                .scalars()
                .all()
            )
            if not stats:
                console.print("  [yellow](no player stats parsed for this map)[/yellow]")
                continue

            by_team: dict[str, list[PlayerMapStat]] = {}
            for s in stats:
                key = s.team_name or "?"
                by_team.setdefault(key, []).append(s)

            for team_name, team_stats in by_team.items():
                t = Table(title=team_name, show_lines=False, title_justify="left")
                t.add_column("Player")
                t.add_column("Agent")
                t.add_column("Rating", justify="right")
                t.add_column("ACS", justify="right")
                t.add_column("K", justify="right")
                t.add_column("D", justify="right")
                t.add_column("A", justify="right")
                t.add_column("+/-", justify="right")
                t.add_column("KAST", justify="right")
                t.add_column("ADR", justify="right")
                t.add_column("HS%", justify="right")
                team_stats.sort(key=lambda s: (s.rating or 0.0), reverse=True)
                for s in team_stats:
                    player = session.get(Player, s.player_id)
                    pname = player.name if player else f"id={s.player_id}"
                    t.add_row(
                        pname,
                        s.agent or "-",
                        f"{s.rating:.2f}" if s.rating is not None else "-",
                        str(s.acs) if s.acs is not None else "-",
                        str(s.kills) if s.kills is not None else "-",
                        str(s.deaths) if s.deaths is not None else "-",
                        str(s.assists) if s.assists is not None else "-",
                        f"{s.plus_minus:+d}" if s.plus_minus is not None else "-",
                        f"{s.kast}%" if s.kast is not None else "-",
                        f"{s.adr:.1f}" if s.adr is not None else "-",
                        f"{s.hs_pct}%" if s.hs_pct is not None else "-",
                    )
                console.print(t)

        veto = (
            session.execute(
                select(VetoAction)
                .where(VetoAction.match_id == match_id)
                .order_by(VetoAction.order_index)
            )
            .scalars()
            .all()
        )
        if veto:
            console.print()
            console.print("[bold]Veto sequence:[/bold]")
            for v in veto:
                team = v.team_name or "(decider)"
                console.print(f"  {v.order_index + 1}. {team}  {v.action}  {v.map_name}")
    finally:
        session.close()


_METRIC_COLUMNS = {
    "rating": PlayerMapStat.rating,
    "acs": PlayerMapStat.acs,
    "adr": PlayerMapStat.adr,
    "kast": PlayerMapStat.kast,
    "hs_pct": PlayerMapStat.hs_pct,
    "kills": PlayerMapStat.kills,
}


@app.command("top-players")
def top_players_cmd(
    metric: str = typer.Option("rating", help=f"One of: {', '.join(_METRIC_COLUMNS)}"),
    min_maps: int = typer.Option(5, "--min-maps"),
    limit: int = typer.Option(10),
    event: Optional[int] = typer.Option(None, "--event", "-e"),
) -> None:
    """Top players by average metric. Optionally restrict to a single event."""
    _configure_logging(verbose=False)
    if metric not in _METRIC_COLUMNS:
        console.print(f"[red]Unknown metric: {metric}. Choose from {list(_METRIC_COLUMNS)}[/red]")
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
            title = f"Top {limit} players by avg {metric} (min {min_maps} maps)"
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
            title = (
                f"{event_obj.name if event_obj else f'event {event}'} — "
                f"top {limit} by avg {metric} (min {min_maps} maps)"
            )

        rows = session.execute(query).all()
        if not rows:
            console.print("[yellow]No results. Try lowering --min-maps.[/yellow]")
            return

        t = Table(title=title)
        t.add_column("Player")
        t.add_column("Maps", justify="right")
        t.add_column(f"Avg {metric}", justify="right")
        for player_id, n_maps, avg in rows:
            player = session.get(Player, player_id)
            pname = player.name if player else f"id={player_id}"
            avg_fmt = f"{float(avg):.2f}" if avg is not None else "-"
            t.add_row(pname, str(n_maps), avg_fmt)
        console.print(t)
    finally:
        session.close()


if __name__ == "__main__":
    app()

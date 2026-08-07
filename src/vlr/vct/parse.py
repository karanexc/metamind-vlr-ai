"""Parse one VCT game (an event stream) into per-player + per-round ability data.

The game files are a time-ordered list of events; each has `platformGameId`,
`metadata`, and one type body (`configuration`, `snapshot`, `playerDied`,
`roundStarted`, `roundDecided`, `spikeStatus`, ...).

Ability usage is DERIVED from state snapshots: every snapshot carries each
player's current charges per slot (GRENADE / ABILITY_1 / ABILITY_2 / ULTIMATE).
A cast = a charge drop within a round; an ult = a ready ult being spent (clean).
We attribute each cast to the active round + team and log a compact per-round
timeline (casts, ults, kills, spike) so the UI can show *which* utility shaped a
round. It's a state-diff / timing proxy, not a discrete cast log — see the UI
methodology note.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

_ABILITY_SLOTS = ("ABILITY_1", "ABILITY_2", "GRENADE")
_ULT_SLOT = "ULTIMATE"


@dataclass
class PlayerAbilities:
    player_id: int
    handle: str = ""
    agent: Optional[str] = None
    role: Optional[str] = None
    team_id: Optional[int] = None
    team_name: str = ""
    ability1_casts: int = 0
    ability2_casts: int = 0
    grenade_casts: int = 0
    ult_casts: int = 0
    kills: int = 0
    deaths: int = 0
    won: bool = False


@dataclass
class GameResult:
    game_id: str
    map_name: Optional[str]
    date: Optional[str]
    total_rounds: int
    winner_team_id: Optional[int]
    round_wins: dict
    team_names: dict          # team_id -> name (insertion order = A, B)
    players: list             # list[PlayerAbilities]
    rounds: list = field(default_factory=list)   # list[dict] per-round records


def _cur(ability: dict) -> int:
    return (ability.get("baseCharges", 0) or 0) + (ability.get("temporaryCharges", 0) or 0)


def _slot(ability: dict) -> Optional[str]:
    fb = (ability.get("ability", {}) or {}).get("fallback", {}) or {}
    return (fb.get("inventorySlot", {}) or {}).get("slot")


def _secs(e: dict) -> Optional[float]:
    m = (e.get("metadata", {}) or {}).get("eventTime", {}) or {}
    v = m.get("omittingPauses") or m.get("includedPauses") or ""
    try:
        return float(str(v).rstrip("s"))
    except Exception:
        return None


def parse_game(events: list, agent_map: Optional[dict] = None,
               map_map: Optional[dict] = None) -> Optional[GameResult]:
    agent_map = agent_map or {}
    map_map = map_map or {}

    game_id: Optional[str] = None
    map_name: Optional[str] = None
    date: Optional[str] = None
    team_names: dict = {}
    player_team: dict = {}
    team_index: dict = {}          # team_id -> 0/1 (for compact timeline)
    players: dict[int, PlayerAbilities] = {}

    last_charge: dict = {}
    ult_cost: dict = {}
    round_active = False
    total_rounds = 0
    round_wins: dict = {}
    rounds: list = []
    player_agent: dict = {}         # player_id -> agent name (FK / ult attribution)
    cur: Optional[dict] = None      # in-progress round record

    def _tidx(tid):
        return team_index.get(tid)

    def _new_round(rnum, attacker, start_t):
        tids = list(team_names.keys())
        return {
            "round_number": rnum, "attacker_team_id": attacker, "start_time": start_t,
            "util": {t: 0 for t in tids}, "ults": {t: 0 for t in tids},
            "alive": {t: 5 for t in tids}, "reached_1v2": {t: False for t in tids},
            "opening_kill_team_id": None, "opening_kill_time": None,
            "opening_kill_agent": None, "ult_agents": [],
            "spike_planted": False, "spike_defused": False, "timeline": [],
        }

    def _log(t, kind, team_id, slot=None):
        if cur is None:
            return
        rel = round(t - cur["start_time"], 1) if (t is not None and cur["start_time"] is not None) else None
        ev = {"t": rel, "k": kind, "team": _tidx(team_id)}
        if slot:
            ev["slot"] = slot
        cur["timeline"].append(ev)

    for e in events:
        if game_id is None and e.get("platformGameId"):
            game_id = e["platformGameId"]
        md = e.get("metadata")
        if md and date is None and md.get("wallTime"):
            date = md["wallTime"]

        if "configuration" in e:
            c = e["configuration"]
            sm = (c.get("selectedMap", {}) or {}).get("fallback", {}) or {}
            map_name = map_map.get(sm.get("guid") or "") or sm.get("displayName") or map_name
            for t in c.get("teams", []):
                tid = (t.get("teamId", {}) or {}).get("value")
                if tid is not None:
                    if tid not in team_index:
                        team_index[tid] = len(team_index)
                    team_names[tid] = t.get("name", team_names.get(tid, ""))
                    for pv in t.get("playersInTeam", []):
                        player_team[pv.get("value")] = tid
            for p in c.get("players", []):
                pid = (p.get("playerId", {}) or {}).get("value")
                if pid is None:
                    continue
                pa = players.setdefault(pid, PlayerAbilities(player_id=pid))
                pa.handle = p.get("displayName") or pa.handle
                resolved = agent_map.get(
                    ((p.get("selectedAgent", {}) or {}).get("fallback", {}) or {}).get("guid", "").upper()
                )
                if resolved:
                    pa.agent, pa.role = resolved
                    player_agent[pid] = resolved[0]
            continue

        if "roundStarted" in e:
            round_active = True
            rs = e["roundStarted"]
            rnum = rs.get("roundNumber", total_rounds + 1)
            total_rounds = max(total_rounds, rnum)
            attacker = (rs.get("spikeMode", {}) or {}).get("attackingTeam", {}).get("value")
            cur = _new_round(rnum, attacker, _secs(e))
            for key in list(last_charge):
                if key[1] in _ABILITY_SLOTS:
                    last_charge[key] = None
            continue

        if "roundDecided" in e:
            round_active = False
            res = (e["roundDecided"].get("result", {}) or {})
            smr = res.get("spikeModeResult", {}) or {}
            wt = (res.get("winningTeam", {}) or {}).get("value")
            if wt is not None:
                round_wins[wt] = round_wins.get(wt, 0) + 1
            if cur is not None:
                cur["winner_team_id"] = wt
                cur["win_condition"] = smr.get("cause")
                rounds.append(cur)
                cur = None
            continue

        if "spikeStatus" in e:
            st = e["spikeStatus"].get("status")
            if cur is not None and st in ("PLANTED", "DEFUSED"):
                if st == "PLANTED":
                    cur["spike_planted"] = True
                    _log(_secs(e), "plant", cur.get("attacker_team_id"))
                else:
                    cur["spike_defused"] = True
                    _log(_secs(e), "defuse", None)
            continue

        if "playerDied" in e:
            pd = e["playerDied"]
            dec = (pd.get("deceasedId", {}) or {}).get("value")
            kil = (pd.get("killerId", {}) or {}).get("value")
            if dec in players:
                players[dec].deaths += 1
            if kil is not None and kil in players and kil != dec:
                players[kil].kills += 1
            if cur is not None:
                kteam = player_team.get(kil)
                _log(_secs(e), "kill", kteam)
                if cur["opening_kill_team_id"] is None and kteam is not None:
                    cur["opening_kill_team_id"] = kteam
                    cur["opening_kill_agent"] = player_agent.get(kil)
                    cur["opening_kill_time"] = round(_secs(e) - cur["start_time"], 1) \
                        if _secs(e) is not None and cur["start_time"] is not None else None
                vteam = player_team.get(dec)
                if vteam in cur["alive"]:
                    cur["alive"][vteam] -= 1
                    for t in cur["alive"]:
                        opp = [x for x in cur["alive"] if x != t]
                        if opp and cur["alive"][t] == 1 and cur["alive"][opp[0]] >= 2:
                            cur["reached_1v2"][t] = True
            continue

        if "snapshot" in e:
            t_ev = _secs(e)
            for p in e["snapshot"].get("players", []):
                pid = (p.get("playerId", {}) or {}).get("value")
                if pid is None:
                    continue
                pa = players.setdefault(pid, PlayerAbilities(player_id=pid))
                team = player_team.get(pid)
                for ab in p.get("abilities", []):
                    slot = _slot(ab)
                    if slot not in _ABILITY_SLOTS and slot != _ULT_SLOT:
                        continue
                    c = _cur(ab)
                    key = (pid, slot)
                    prev = last_charge.get(key)
                    if slot == _ULT_SLOT:
                        mx = ab.get("maxCharges", 0) or 0
                        if mx:
                            ult_cost[pid] = mx
                        if prev is not None and c < prev and ult_cost.get(pid, 0) and prev >= ult_cost[pid]:
                            pa.ult_casts += 1
                            if cur is not None and team in cur["ults"]:
                                cur["ults"][team] += 1
                                cur["ult_agents"].append({"agent": player_agent.get(pid), "team_id": team})
                                _log(t_ev, "ult", team)
                        last_charge[key] = c
                    else:
                        if prev is not None and round_active and c < prev:
                            amt = prev - c
                            if slot == "ABILITY_1":
                                pa.ability1_casts += amt
                            elif slot == "ABILITY_2":
                                pa.ability2_casts += amt
                            else:
                                pa.grenade_casts += amt
                            if cur is not None and team in cur["util"]:
                                cur["util"][team] += amt
                                _log(t_ev, "ability", team, slot)
                        last_charge[key] = c
            continue

    if not players:
        return None

    winner = max(round_wins, key=round_wins.get) if round_wins else None
    for pa in players.values():
        pa.team_id = player_team.get(pa.player_id)
        pa.team_name = team_names.get(pa.team_id, "")
        pa.won = winner is not None and pa.team_id == winner

    return GameResult(
        game_id=game_id or "", map_name=map_name, date=date,
        total_rounds=total_rounds, winner_team_id=winner, round_wins=round_wins,
        team_names=team_names, players=list(players.values()), rounds=rounds,
    )

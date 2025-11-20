from __future__ import annotations
from typing import Any, Dict, List
from datetime import date, timedelta


def today0() -> date:
    return date.today()


def add_days(d: date, n: int) -> date:
    return d + timedelta(days=n)


# --------- Projection des événements et courbe journalière --------- #


def generate_events(entries: List[Dict[str, Any]], horizon_days: int, start: date) -> List[Dict[str, Any]]:
    evts: List[Dict[str, Any]] = []
    end = add_days(start, horizon_days)

    for e in entries:
        try:
            amt = float(e.get("amount") or 0.0)
        except (TypeError, ValueError):
            amt = 0.0
        if amt == 0:
            continue

        typ = e.get("type") or "expense"
        sign = 1.0 if typ == "income" else -1.0
        rec = e.get("rec") or "monthly"

        start_str = e.get("start")
        if start_str:
            try:
                y, m, d = map(int, start_str.split("-"))
                d0 = date(y, m, d)
            except Exception:
                d0 = start
        else:
            d0 = start

        if d0 < start:
            d0 = start

        def push(dt: date) -> None:
            if dt <= end:
                evts.append({"date": dt, "delta": sign * amt})

        if rec == "oneoff":
            push(d0)
        else:
            cur = d0
            while cur <= end:
                push(cur)
                if rec == "weekly":
                    cur = cur + timedelta(days=7)
                elif rec == "monthly":
                    # approximatif mais suffisant pour la projection
                    month = cur.month + 1
                    year = cur.year + (month - 1) // 12
                    month = ((month - 1) % 12) + 1
                    cur = date(year, month, cur.day if cur.day <= 28 else 28)
                elif rec == "quarterly":
                    month = cur.month + 3
                    year = cur.year + (month - 1) // 12
                    month = ((month - 1) % 12) + 1
                    cur = date(year, month, cur.day if cur.day <= 28 else 28)
                elif rec == "yearly":
                    cur = date(cur.year + 1, cur.month, cur.day if cur.day <= 28 else 28)
                else:
                    # fallback -> monthly
                    month = cur.month + 1
                    year = cur.year + (month - 1) // 12
                    month = ((month - 1) % 12) + 1
                    cur = date(year, month, cur.day if cur.day <= 28 else 28)

    evts.sort(key=lambda x: x["date"])
    return evts


def project_daily(base: float, entries: List[Dict[str, Any]], horizon_days: int) -> List[Dict[str, Any]]:
    start = today0()
    evts = generate_events(entries, horizon_days, start)
    out: List[Dict[str, Any]] = []
    bal = float(base)
    i = 0
    for d in range(horizon_days + 1):
        cur = add_days(start, d)
        while i < len(evts) and evts[i]["date"] == cur:
            bal += evts[i]["delta"]
            i += 1
        out.append({"date": cur.isoformat(), "balance": round(bal, 2)})
    return out


# --------- KPI mensuels + scénarios --------- #


def apply_scenario(entries: List[Dict[str, Any]], scenario: Dict[str, Any]) -> List[Dict[str, Any]]:
    var_mul = float(scenario.get("var_mul", 1.0) or 1.0)
    extra_income = float(scenario.get("extra_income", 0.0) or 0.0)
    extra_credit = float(scenario.get("extra_credit", 0.0) or 0.0)

    out = [dict(e) for e in entries]

    # -10% variables
    if var_mul != 1.0:
        for e in out:
            if e.get("type") == "expense" and e.get("cat") == "variable":
                try:
                    amt = float(e.get("amount") or 0.0)
                except (TypeError, ValueError):
                    amt = 0.0
                if amt != 0.0:
                    e["amount"] = round(amt * var_mul, 2)

    # + X revenu mensuel
    if extra_income > 0:
        out.append(
            {
                "type": "income",
                "amount": extra_income,
                "rec": "monthly",
                "cat": "fixed",
                "start": today0().isoformat(),
            }
        )

    # + X crédit mensuel
    if extra_credit > 0:
        out.append(
            {
                "type": "expense",
                "amount": extra_credit,
                "rec": "monthly",
                "cat": "credit",
                "start": today0().isoformat(),
            }
        )

    return out


def monthly_kpis(entries: List[Dict[str, Any]]) -> Dict[str, float]:
    inc = fix = vari = cred = 0.0
    for e in entries:
        try:
            amt = float(e.get("amount") or 0.0)
        except (TypeError, ValueError):
            amt = 0.0
        if amt == 0:
            continue

        rec = e.get("rec") or "monthly"
        factor: float
        if rec == "weekly":
            factor = 4.333
        elif rec == "monthly":
            factor = 1.0
        elif rec == "quarterly":
            factor = 1.0 / 3.0
        elif rec == "yearly":
            factor = 1.0 / 12.0
        else:
            factor = 0.0  # oneoff -> ignoré pour KPI mensuels

        m_amt = amt * factor
        if e.get("type") == "income":
            inc += m_amt
        else:
            cat = e.get("cat") or "variable"
            if cat == "fixed":
                fix += m_amt
            elif cat == "credit":
                cred += m_amt
            else:
                vari += m_amt

    total_exp = fix + vari + cred
    debt_ratio = (cred / inc) if inc > 0 else 0.0  # crédit/revenus
    reste_a_vivre = inc - total_exp
    save_rate = (max(inc - total_exp, 0.0) / inc) if inc > 0 else 0.0

    return {
        "debt_pct": max(0.0, debt_ratio * 100.0),
        "reste": reste_a_vivre,
        "save_pct": max(0.0, save_rate * 100.0),
        "inc": inc,
        "fix": fix,
        "vari": vari,
        "cred": cred,
        "total_exp": total_exp,
    }


# --------- Score & breakdown (mêmes règles que le front) --------- #


def compute_score_from_kpis(k: Dict[str, float]) -> Dict[str, Any]:
    revenus = k.get("inc", 0.0) or 0.0
    total_exp = k.get("total_exp", 0.0) or 0.0
    fix = k.get("fix", 0.0) or 0.0
    cred = k.get("cred", 0.0) or 0.0

    taux_epargne = (max(revenus - total_exp, 0.0) / revenus) if revenus > 0 else 0.0
    taux_charges = (fix / revenus) if revenus > 0 else 0.0
    taux_dette = (cred / revenus) if revenus > 0 else 0.0

    comp_epargne = min(taux_epargne / 0.20, 1.0)
    comp_charges = 1.0 - min(taux_charges / 0.50, 1.0)
    comp_dette = 1.0 - min(taux_dette / 0.20, 1.0)

    score = round(100.0 * (0.4 * comp_epargne + 0.3 * comp_charges + 0.3 * comp_dette))
    score = max(0, min(100, score))

    level = "rouge"
    if score >= 85:
        level = "vert"
    elif score >= 70:
        level = "jaune"
    elif score >= 40:
        level = "orange"

    if level == "vert":
        message = "Budget serein — ton argent travaille pour toi."
    elif level == "jaune":
        message = "Base saine — renforce ton épargne pour passer au vert."
    elif level == "orange":
        message = "Budget sous tension — des ajustements simples peuvent aider."
    else:
        message = "Situation fragile — il faut reprendre le contrôle."

    return {
        "score": score,
        "level": level,
        "message": message,
        "ratios": {
            "taux_epargne": taux_epargne,
            "taux_charges": taux_charges,
            "taux_dette": taux_dette,
        },
    }


def breakdown_by_category_from_kpis(k: Dict[str, float]) -> List[Dict[str, Any]]:
    return [
        {"label": "Fixe", "amount": round(k.get("fix", 0.0) or 0.0, 2)},
        {"label": "Variable", "amount": round(k.get("vari", 0.0) or 0.0, 2)},
        {"label": "Crédit", "amount": round(k.get("cred", 0.0) or 0.0, 2)},
    ]


def breakdown_by_recurring(entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    sums = {"Mensuel": 0.0, "Hebdo": 0.0, "Ponctuel": 0.0, "Trimestriel": 0.0, "Annuel": 0.0}
    for e in entries:
        try:
            amt = float(e.get("amount") or 0.0)
        except (TypeError, ValueError):
            amt = 0.0
        if amt == 0.0:
            continue

        rec = e.get("rec") or "monthly"
        if rec == "weekly":
            m_amt = amt * 4.333
            sums["Hebdo"] += m_amt
        elif rec == "monthly":
            m_amt = amt
            sums["Mensuel"] += m_amt
        elif rec == "quarterly":
            m_amt = amt / 3.0
            sums["Trimestriel"] += m_amt
        elif rec == "yearly":
            m_amt = amt / 12.0
            sums["Annuel"] += m_amt
        elif rec == "oneoff":
            m_amt = amt
            sums["Ponctuel"] += m_amt

    return [
        {"label": "Mensuel", "amount": round(sums["Mensuel"], 2)},
        {"label": "Hebdo", "amount": round(sums["Hebdo"], 2)},
        {"label": "Ponctuel", "amount": round(sums["Ponctuel"], 2)},
        {"label": "Trimestriel", "amount": round(sums["Trimestriel"], 2)},
        {"label": "Annuel", "amount": round(sums["Annuel"], 2)},
    ]


def build_tips(score_pack: Dict[str, Any], k: Dict[str, float], cur: str) -> List[str]:
    tips: List[str] = []
    revenus = k.get("inc", 0.0) or 0.0
    total_exp = k.get("total_exp", 0.0) or 0.0
    fix = k.get("fix", 0.0) or 0.0
    cred = k.get("cred", 0.0) or 0.0

    actuelle_epargne = max(revenus - total_exp, 0.0)
    need20 = max(0.0, 0.20 * revenus - actuelle_epargne)
    if need20 > 0:
        tips.append(f"Augmente l’épargne mensuelle de {cur}{need20:.2f} pour viser 20 %.")

    over_fix = fix - 0.50 * revenus
    if over_fix > 0:
        tips.append(f"Réduis les charges fixes d’environ {cur}{over_fix:.2f} pour repasser sous 50 %.")

    over_debt = cred - 0.20 * revenus
    if over_debt > 0:
        tips.append(f"Négocie/solde {cur}{over_debt:.2f} de mensualités pour revenir sous 20 %.")

    if not tips:
        tips.append("Continue : maintiens ton cap et renforce progressivement l’épargne.")

    return tips


# --------- Fonction principale : moteur /calc --------- #


def compute_projection(
    base: float,
    currency: str,
    horizon_days: int,
    entries: List[Dict[str, Any]],
    scenario: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    if scenario is None:
        scenario = {}

    horizon_days = max(30, min(int(horizon_days or 90), 365))

    # Applique scénario
    entries_scn = apply_scenario(entries, scenario)

    # Courbe journalière
    curve = project_daily(base, entries_scn, horizon_days)

    # KPI mensuels
    kpi = monthly_kpis(entries_scn)

    # Score
    score_pack = compute_score_from_kpis(kpi)

    # Milestones
    def idx(d: int) -> int:
        return min(d, len(curve) - 1)

    milestones = {
        "m1": round(curve[idx(30)]["balance"], 2),
        "m6": round(curve[idx(180)]["balance"], 2),
        "m12": round(curve[idx(365)]["balance"], 2),
    }

    # Breakdown
    by_cat = breakdown_by_category_from_kpis(kpi)
    by_rec = breakdown_by_recurring(entries_scn)

    tips = build_tips(score_pack, kpi, currency)

    return {
        "meta": {
            "currency": currency,
            "horizon_days": horizon_days,
        },
        "inputs": {
            "base": base,
            "scenario": scenario,
        },
        "kpi": {
            **kpi,
            "debt_pct": kpi["debt_pct"],
            "reste_a_vivre": kpi["reste"],
            "save_pct": kpi["save_pct"],
        },
        "score": score_pack,
        "milestones": milestones,
        "curve": curve,
        "breakdown": {
            "by_category": by_cat,
            "by_recurring": by_rec,
        },
        "tips": tips,
    }

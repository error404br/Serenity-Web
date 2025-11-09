# PSEUDOCODE PYTHON (FastAPI-style)

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, validator

router = APIRouter()

# ---------- Schemas ----------
class CalcIn(BaseModel):
    revenus: float = Field(ge=0)
    charges_fixes: float = Field(ge=0)
    charges_variables: float = Field(ge=0)
    dettes_mensuelles: float = Field(ge=0)
    epargne_mensuelle: float = Field(ge=0)

    @validator("revenus")
    def revenus_not_zero_if_inputs(cls, v, values):
        # autorise 0 uniquement si tout est 0
        if v == 0 and any(values.get(k, 0) > 0 for k in
                          ["charges_fixes","charges_variables","dettes_mensuelles","epargne_mensuelle"]):
            raise ValueError("revenus doit être > 0 si des dépenses/épargne existent")
        return v

class CalcOut(BaseModel):
    score: int
    niveau: str              # "rouge"|"orange"|"jaune"|"vert"
    message: str
    solde: float
    ratios: dict             # { "taux_epargne":float, "taux_charges":float, "taux_dette":float, "taux_libre":float }
    recap: dict              # montants intermédiaires
    tips: list[str]          # suggestions d’actions

# ---------- Helpers ----------
def clamp(x, lo, hi): return max(lo, min(hi, x))

def round_money(x): return round(float(x), 2)

def format_level(score:int) -> tuple[str,str]:
    if score < 40:   return ("rouge",  "Situation fragile — il faut reprendre le contrôle.")
    if score < 70:   return ("orange", "Budget sous tension — des ajustements simples peuvent aider.")
    if score < 85:   return ("jaune",  "Base saine — renforce ton épargne pour passer au vert.")
    return ("vert",   "Budget serein — ton argent travaille pour toi.")

def build_tips(revenus, charges_fixes, dettes_mensuelles, epargne_mensuelle):
    tips = []
    # heuristiques simples, non bloquantes
    if epargne_mensuelle < 0.2 * revenus:
        gap = round_money(0.2 * revenus - epargne_mensuelle)
        tips.append(f"Augmente l’épargne mensuelle de {gap}$ pour atteindre 20 %.")
    if charges_fixes > 0.5 * revenus:
        target = round_money(charges_fixes - 0.5 * revenus)
        tips.append(f"Réduis les charges fixes d’environ {target}$ pour repasser sous 50 % des revenus.")
    if dettes_mensuelles > 0.2 * revenus:
        target = round_money(dettes_mensuelles - 0.2 * revenus)
        tips.append(f"Négocie/solde {target}$ de mensualités pour revenir sous 20 % d’endettement.")
    if not tips:
        tips.append("Continue: maintiens ton cap et renforce progressivement l’épargne.")
    return tips

# ---------- Core formula ----------
# score = 100 * ( 0.4*min(taux_epargne/0.2,1) + 0.3*(1-min(taux_charges/0.5,1)) + 0.3*(1-min(taux_dette/0.2,1)) )

@router.post("/calc", response_model=CalcOut)
def calc(payload: CalcIn):
    r  = float(payload.revenus)
    cf = float(payload.charges_fixes)
    cv = float(payload.charges_variables)
    dm = float(payload.dettes_mensuelles)
    ep = float(payload.epargne_mensuelle)

    # Cas trivial : tout à zéro
    if r == 0 and cf == 0 and cv == 0 and dm == 0 and ep == 0:
        return CalcOut(
            score=0, niveau="rouge", message="Commence par entrer tes revenus et dépenses.",
            solde=0.0,
            ratios={"taux_epargne":0,"taux_charges":0,"taux_dette":0,"taux_libre":0},
            recap={"revenus":0,"depenses_totales":0,"charges_fixes":0,"charges_variables":0,"dettes_mensuelles":0,"epargne_mensuelle":0},
            tips=["Renseigne ton budget pour obtenir un score."]
        )

    dep_tot = cf + cv + dm
    solde   = r - dep_tot

    # Eviter divisions par zéro
    if r <= 0:
        raise HTTPException(400, detail="revenus doit être > 0 pour calculer les ratios")

    taux_epargne = clamp(ep / r, 0, 5)          # borné large, puis normalisé
    taux_charges = clamp(cf / r, 0, 5)
    taux_dette   = clamp(dm / r, 0, 5)
    taux_libre   = clamp(solde / r, -5, 5)

    # Normalisation par zones cibles
    comp_epargne = min(taux_epargne / 0.20, 1.0)      # idéal ≥ 20%
    comp_charges = 1 - min(taux_charges / 0.50, 1.0)  # idéal ≤ 50%
    comp_dette   = 1 - min(taux_dette   / 0.20, 1.0)  # idéal ≤ 20%

    score = int(round(100 * (0.4*comp_epargne + 0.3*comp_charges + 0.3*comp_dette)))
    score = int(clamp(score, 0, 100))

    niveau, message = format_level(score)
    tips = build_tips(r, cf, dm, ep)

    return CalcOut(
        score=score,
        niveau=niveau,
        message=message,
        solde=round_money(solde),
        ratios={
            "taux_epargne": round(taux_epargne, 4),
            "taux_charges": round(taux_charges, 4),
            "taux_dette":   round(taux_dette,   4),
            "taux_libre":   round(taux_libre,   4),
        },
        recap={
            "revenus": r,
            "depenses_totales": round_money(dep_tot),
            "charges_fixes": cf,
            "charges_variables": cv,
            "dettes_mensuelles": dm,
            "epargne_mensuelle": ep,
        },
        tips=tips
    )

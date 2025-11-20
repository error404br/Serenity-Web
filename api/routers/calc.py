from typing import Any, Dict, List, Optional
from fastapi import APIRouter
from pydantic import BaseModel, Field
from services.calc import compute_projection

router = APIRouter()


class Entry(BaseModel):
    type: str = Field(..., description="income ou expense")
    amount: float = Field(..., description="Montant brut de la ligne")
    rec: str = Field("monthly", description="oneoff | weekly | monthly | quarterly | yearly")
    cat: str = Field("fixed", description="fixed | variable | credit")
    start: Optional[str] = Field(None, description="Date de début au format YYYY-MM-DD")


class Scenario(BaseModel):
    var_mul: float = Field(1.0, description="Multiplicateur sur les dépenses variables (ex: 0.9 = -10%)")
    extra_income: float = Field(0.0, description="Revenu mensualisé supplémentaire")
    extra_credit: float = Field(0.0, description="Crédit mensualisé supplémentaire")


class CalcRequest(BaseModel):
    base: float = 0.0
    currency: str = "$"
    horizon_days: int = 90
    entries: List[Entry] = []
    scenario: Scenario = Scenario()


@router.post("/calc")
def calc_projection(payload: CalcRequest) -> Dict[str, Any]:
    """
    Moteur de calcul Serenity Web.

    Reçoit:
    - base: solde initial
    - currency: devise (ex: "$", "€", "C$")
    - horizon_days: 30–365
    - entries: lignes revenu/dépense (type, amount, rec, cat, start)
    - scenario: options (-10% variables, +revenus, +crédit)

    Retourne:
    - meta, kpi, score, milestones, curve, breakdown, tips
    """
    data = compute_projection(
        base=payload.base,
        currency=payload.currency,
        horizon_days=payload.horizon_days,
        entries=[e.model_dump() for e in payload.entries],
        scenario=payload.scenario.model_dump(),
    )
    return data

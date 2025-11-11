from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional
from services.pdf import render_pdf

router = APIRouter()

# Modèle minimal (on reste permissif pour avancer vite)
class ExportPayload(BaseModel):
    meta: Dict[str, Any]
    summary: Dict[str, Any]
    milestones: Optional[Dict[str, float]] = None
    curve: Optional[List[Dict[str, Any]]] = None
    breakdown: Optional[Dict[str, Any]] = None
    tips: Optional[List[str]] = None
    disclaimer: Optional[str] = None

@router.post("/export-pdf", response_class=Response)
def export_pdf(payload: ExportPayload):
    try:
        # (Beta) Pas d’auth complexe ici. Plus tard: vérifier licence/clé.
        pdf_bytes = render_pdf(payload.model_dump())
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": 'attachment; filename="serenity-web-projection.pdf"'
            },
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Echec génération PDF: {e}")

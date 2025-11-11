from typing import Dict, Any, List
from jinja2 import Environment, FileSystemLoader, select_autoescape
from weasyprint import HTML, CSS
from pathlib import Path
import datetime as dt

TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "templates" / "pdf"

_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
)

def _fmt_money(v: float, cur: str) -> str:
    try:
        sign = "-" if v < 0 else ""
        return f"{sign}{cur}{abs(float(v)):.2f}"
    except Exception:
        return f"{cur}0.00"

def _sparkline_svg(points: List[Dict[str, Any]], width=520, height=80, pad=6) -> str:
    if not points:
        return f'<svg width="{width}" height="{height}"></svg>'
    xs = list(range(len(points)))
    ys = [float(p.get("balance", 0.0)) for p in points]
    y_min, y_max = min(ys), max(ys)
    span = (y_max - y_min) or 1.0

    def sx(i): return pad + (i / max(len(xs)-1, 1)) * (width - 2*pad)
    def sy(v): return height - pad - ((v - y_min) / span) * (height - 2*pad)

    points_attr = " ".join(f"{sx(i):.1f},{sy(ys[i]):.1f}" for i in range(len(xs)))
    zero_y = sy(0) if (y_min <= 0 <= y_max) else None
    axis = f'<line x1="0" y1="{zero_y:.1f}" x2="{width}" y2="{zero_y:.1f}" stroke="#e5e7eb"/>' if zero_y is not None else ""
    return f'''
<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  {axis}
  <polyline fill="none" stroke="#0b2545" stroke-width="2" points="{points_attr}" />
</svg>'''.strip()

def _merge_defaults(data: Dict[str, Any]) -> Dict[str, Any]:
    d = dict(data or {})
    d.setdefault("meta", {})
    d["meta"].setdefault("currency", "$")
    d["meta"].setdefault("generated_at", dt.datetime.utcnow().isoformat(timespec="seconds") + "Z")
    d["meta"].setdefault("horizon_days", 90)

    d.setdefault("summary", {})
    d["summary"].setdefault("score", 0)
    d["summary"].setdefault("level", "rouge")
    d["summary"].setdefault("message", "")
    d["summary"].setdefault("kpi", {})
    d["summary"]["kpi"].setdefault("inc", 0.0)
    d["summary"]["kpi"].setdefault("total_exp", 0.0)
    d["summary"]["kpi"].setdefault("fix", 0.0)
    d["summary"]["kpi"].setdefault("vari", 0.0)
    d["summary"]["kpi"].setdefault("cred", 0.0)
    d["summary"]["kpi"].setdefault("debt_pct", 0.0)
    d["summary"]["kpi"].setdefault("reste_a_vivre", 0.0)
    d["summary"]["kpi"].setdefault("save_pct", 0.0)

    d.setdefault("milestones", {"m1": 0.0, "m6": 0.0, "m12": 0.0})
    d.setdefault("curve", [])
    d.setdefault("breakdown", {"by_category": [], "by_recurring": []})
    d.setdefault("tips", [])
    d.setdefault("disclaimer", "Ce document est fourni à titre indicatif.")
    return d

def render_pdf(data: Dict[str, Any]) -> bytes:
    """Rend le PDF 2 pages à partir du payload JSON."""
    ctx = _merge_defaults(data)
    # Helpers calculés
    cur = ctx["meta"]["currency"]
    ctx["fmt"] = lambda v: _fmt_money(v, cur)
    ctx["sparkline_svg"] = _sparkline_svg(ctx.get("curve", []))

    # Charge templates
    page1 = _env.get_template("page1.html").render(**ctx)
    page2 = _env.get_template("page2.html").render(**ctx)

    # Styles globaux
    css = CSS(filename=str(TEMPLATES_DIR / "base.css"))

    # Génération PDF
    html = HTML(string=page1 + '<p style="page-break-before: always"></p>' + page2, base_url=str(TEMPLATES_DIR))
    pdf_bytes = html.write_pdf(stylesheets=[css])
    return pdf_bytes

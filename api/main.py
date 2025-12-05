from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# IMPORT DES ROUTERS
from routers import pdf_export, calc, ping

# -----------------------------------------------------
# CRÉATION DE L'APPLICATION FASTAPI
# -----------------------------------------------------
app = FastAPI(
    title="Serenity Web API",
    version="1.0.0"
)

# -----------------------------------------------------
# CORS
# -----------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # On ouvre pour le MVP
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------------------------------
# INCLUSION DES ROUTERS — UNIQUEMENT APRÈS CRÉATION DE app
# -----------------------------------------------------
app.include_router(pdf_export.router, prefix="/api", tags=["export"])
app.include_router(calc.router, prefix="/api", tags=["calc"])
app.include_router(ping.router, prefix="/api", tags=["monitoring"])

# -----------------------------------------------------
# ENDPOINT DE TEST / RACINE
# -----------------------------------------------------
@app.get("/")
def home():
    return {"message": "Bienvenue sur l'API Serenity Web 🚀"}

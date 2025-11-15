from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import pdf_export

# === Créer l'app AVANT d'utiliser app ===
app = FastAPI(title="Serenity Web API", version="1.0.0")

# === CORS (simple pour l'instant) ===
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # à restreindre plus tard à ton domaine static Serenity Web
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === Routes ===
app.include_router(pdf_export.router, prefix="/api", tags=["export"])


@app.get("/")
def home():
    return {"message": "Bienvenue sur l'API Serenity Web"}

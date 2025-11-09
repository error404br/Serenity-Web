# api/main.py

from fastapi import FastAPI
from routers import calc  # importe ton module /calc

app = FastAPI(
    title="Serenity Web API",
    description="API de calcul du Score de Sérénité financière",
    version="1.0.0"
)

# inclure les routes
app.include_router(calc.router, prefix="/api", tags=["calcul"])

@app.get("/")
def home():
    return {"message": "Bienvenue sur l'API Serenity Web"}

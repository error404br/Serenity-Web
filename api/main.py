from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import pdf_export, calc

app = FastAPI(title="Serenity Web API", version="1.0.0")

# CORS large pour le moment 
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(pdf_export.router, prefix="/api", tags=["export"])
app.include_router(calc.router, prefix="/api", tags=["calc"])


@app.get("/")
def home():
    return {"message": "Bienvenue sur l'API Serenity Web"}

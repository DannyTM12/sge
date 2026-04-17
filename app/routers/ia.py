"""
Router de IA.
Expone los endpoints bajo /ia/*: predicciones de riesgo y alertas generadas por el AI Worker.
"""
from fastapi import APIRouter

router = APIRouter(prefix="/ia", tags=["ia"])

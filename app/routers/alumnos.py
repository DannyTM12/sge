"""
Router de alumnos.
Expone los endpoints bajo /alumnos/*: consultas de información propia (solo lectura).
"""
from fastapi import APIRouter

router = APIRouter(prefix="/alumnos", tags=["alumnos"])

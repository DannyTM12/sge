"""
Base declarativa de SQLAlchemy 2.0.
Todos los modelos heredan de `Base`. Este módulo también importa cada modelo
para que Alembic los detecte automáticamente al correr autogenerate.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base declarativa común para todos los modelos del proyecto."""
    pass


# Los modelos se importan en app/models/__init__.py y desde ahí
# alembic/env.py importa `from app.models import *` para detectarlos.
# No importar aquí para evitar importaciones circulares.

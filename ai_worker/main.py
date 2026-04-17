"""
Entry point del AI Worker.
Inicializa el scheduler APScheduler y registra los jobs de predicción periódica.
Lee datos de alumnos desde PostgreSQL y escribe predicciones de vuelta a la BD.
No corre en cada request HTTP — es un proceso independiente.
"""

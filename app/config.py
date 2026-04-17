"""
Configuración centralizada de la aplicación.
Lee todas las variables de entorno desde .env via pydantic-settings.
Nunca hardcodear secrets — usar siempre esta clase.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Base de datos
    database_url: str

    # Redis
    redis_url: str

    # JWT
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # Entorno
    environment: str = "development"

    # Superadmin inicial
    superadmin_email: str
    superadmin_password: str

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def cors_origins(self) -> list[str]:
        if self.is_production:
            return []  # Configurar dominios reales en producción
        return ["http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:5173"]


settings = Settings()

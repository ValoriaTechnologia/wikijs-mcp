"""Configuration centralisée pour l'application utilisant Pydantic Settings."""

from typing import Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

MCP_TRANSPORT_VALUES: tuple[str, ...] = ("stdio", "http", "sse", "streamable-http")


class Config(BaseSettings):
    """Configuration centralisée de l'application.
    
    Toutes les variables d'environnement sont chargées automatiquement depuis le fichier .env
    ou depuis les variables d'environnement système.
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


    # ========== Configuration Debug ==========

    debug: bool = False
    """Mode debug.
    Défaut: False
    """
    # ========== Configuration Keycloak ==========
    
    keycloak_url: Optional[str] = None
    """URL de base de Keycloak utilisée pour PUBLIC et INTERNAL (mode rétrocompatible).
    Exemple: https://keycloak.example.com
    """
    
    keycloak_public_url: Optional[str] = None
    """URL publique de Keycloak pour les redirections navigateur.
    Exemple: https://keycloak.example.com
    """
    
    keycloak_internal_url: Optional[str] = None
    """URL interne de Keycloak pour les appels API.
    Exemple: http://keycloak:8080
    """
    
    keycloak_realm: Optional[str] = None
    """Nom du realm Keycloak.
    Exemple: oversecur-mcp
    """
    
    keycloak_client_id: Optional[str] = None
    """ID du client OAuth dans Keycloak."""
    
    keycloak_client_secret: Optional[str] = None
    """Secret du client OAuth (requis pour client confidentiel)."""
    
    mcp_base_url: str = "http://localhost:8000"
    """URL publique du serveur MCP.
    Exemple: http://localhost:8000
    """
    
    keycloak_scopes: str = "openid profile email"
    """Scopes OAuth requis, séparés par des espaces.
    Défaut: openid profile email
    """
    
    # ========== Configuration WikiJS ==========
    
    wikijs_url: str = "https://wiki.example.com"
    """URL de base de WikiJS.
    Exemple: https://wiki.example.com
    """
    
    wikijs_graphql_endpoint: Optional[str] = None
    """URL de l'endpoint GraphQL de WikiJS.
    Si non défini, sera construit automatiquement: {WIKIJS_URL}/graphql
    """
    
    wikijs_api_key: Optional[str] = None
    """Clé API WikiJS pour authentifier les requêtes GraphQL.
    Générée dans WikiJS avec les droits de lecture.
    """
    
    # ========== Configuration MCP Server ==========
    
    mcp_transport: str = "http"
    """Transport MCP : stdio, http, sse, streamable-http.
    Variable d'environnement : MCP_TRANSPORT.
    Défaut: http
    """
    
    mcp_host: str = "0.0.0.0"
    """Adresse d'écoute pour le mode réseau.
    Défaut: 0.0.0.0
    """
    
    mcp_port: int = 8000
    """Port pour le mode réseau.
    Défaut: 8000
    """
    
    @field_validator("mcp_transport", mode="after")
    @classmethod
    def validate_mcp_transport(cls, v: str) -> str:
        if v not in MCP_TRANSPORT_VALUES:
            raise ValueError(
                f"MCP_TRANSPORT doit être l'un de {MCP_TRANSPORT_VALUES}, reçu: {v!r}"
            )
        return v
    
    def get_keycloak_public_url(self) -> str:
        """Récupère l'URL publique Keycloak avec détection automatique.
        
        Priorité:
        1. KEYCLOAK_PUBLIC_URL si défini
        2. KEYCLOAK_URL si défini (rétrocompatibilité)
        3. Lève ValueError si aucune n'est définie
        """
        if self.keycloak_public_url:
            return self.keycloak_public_url
        elif self.keycloak_url:
            return self.keycloak_url
        else:
            raise ValueError(
                "KEYCLOAK_URL ou KEYCLOAK_PUBLIC_URL doit être défini "
                "dans les variables d'environnement."
            )
    
    def get_keycloak_internal_url(self) -> str:
        """Récupère l'URL interne Keycloak avec détection automatique.
        
        Priorité:
        1. KEYCLOAK_INTERNAL_URL si défini
        2. KEYCLOAK_URL si défini (rétrocompatibilité)
        3. Lève ValueError si aucune n'est définie
        """
        if self.keycloak_internal_url:
            return self.keycloak_internal_url
        elif self.keycloak_url:
            return self.keycloak_url
        else:
            raise ValueError(
                "KEYCLOAK_URL ou KEYCLOAK_INTERNAL_URL doit être défini "
                "dans les variables d'environnement."
            )


# Instance globale de configuration (chargée au premier import)
_config: Optional[Config] = None


def get_config() -> Config:
    """Récupère l'instance globale de configuration.
    
    Returns:
        Instance de Config chargée depuis les variables d'environnement
    """
    global _config
    if _config is None:
        _config = Config()
        # Construire l'endpoint GraphQL si non défini
        if _config.wikijs_graphql_endpoint is None:
            base_url = _config.wikijs_url.rstrip('/')
            _config.wikijs_graphql_endpoint = f"{base_url}/graphql"
    return _config

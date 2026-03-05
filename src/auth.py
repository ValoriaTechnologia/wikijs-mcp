"""Module d'authentification pour FastMCP avec support OAuth Keycloak."""

from typing import Optional

from fastmcp.server.auth import OAuthProxy
from fastmcp.server.auth.providers.jwt import JWTVerifier
from fastmcp.server.auth import AccessToken

from fastmcp.utilities.logging import get_logger
from src.config import get_config

logger = get_logger(__name__)

class MyJWTVerifier(JWTVerifier):
    async def verify_token(self, token: str) -> AccessToken:
        config = get_config()
        if config.debug:
            logger.info(f"Verifying token: {token}")
        return await super().verify_token(token)


def get_auth_provider() -> Optional[OAuthProxy]:
    """Crée et retourne un provider OAuth Keycloak si configuré.
    
    Configure OAuthProxy avec JWTVerifier pour authentifier les clients MCP
    via Keycloak. Le provider gère automatiquement:
    - Les endpoints OAuth discovery (/.well-known)
    - Le flux OAuth complet avec Dynamic Client Registration (DCR)
    - La vérification des tokens JWT via JWKS
    - Le cache des clés publiques JWKS
    
    Configuration requise via variables d'environnement:
    
    Mode simple (rétrocompatible):
    - KEYCLOAK_URL: URL de base de Keycloak utilisée pour PUBLIC et INTERNAL (ex: https://keycloak.example.com)
    
    Mode avancé (URLs séparées):
    - KEYCLOAK_PUBLIC_URL: URL publique de Keycloak pour les redirections navigateur (ex: https://keycloak.example.com)
    - KEYCLOAK_INTERNAL_URL: URL interne de Keycloak pour les appels API (ex: http://keycloak:8080)
    
    Variables communes:
    - KEYCLOAK_REALM: Nom du realm Keycloak (ex: oversecur-mcp)
    - KEYCLOAK_CLIENT_ID: ID du client OAuth dans Keycloak
    - KEYCLOAK_CLIENT_SECRET: Secret du client (requis pour client confidentiel)
    - MCP_BASE_URL: URL publique du serveur MCP (ex: http://localhost:8000)
    - KEYCLOAK_SCOPES: Scopes OAuth requis (défaut: openid profile email)
    
    Note: Si KEYCLOAK_URL est défini, il sera utilisé pour PUBLIC et INTERNAL (rétrocompatibilité).
    Sinon, KEYCLOAK_PUBLIC_URL et KEYCLOAK_INTERNAL_URL doivent être définis.
    
    Returns:
        OAuthProxy si Keycloak est configuré, None sinon (mode développement sans auth)
    
    Raises:
        ImportError: Si fastmcp.server.auth n'est pas disponible
        ValueError: Si la configuration Keycloak est incomplète
    """
    # Récupérer la configuration depuis la classe Config
    config = get_config()
    
    # Récupérer les URLs Keycloak avec détection automatique
    try:
        keycloak_public_url = config.get_keycloak_public_url()
        keycloak_internal_url = config.get_keycloak_internal_url()
    except ValueError as e:
        raise ValueError(
            "KEYCLOAK_URL ou (KEYCLOAK_PUBLIC_URL et KEYCLOAK_INTERNAL_URL) doivent être définis "
            "dans les variables d'environnement. Configurez Keycloak dans votre fichier .env."
        ) from e
    
    # Si le realm n'est pas configuré, retourner None (mode développement sans auth)
    if not config.keycloak_realm:
        raise ValueError(
            "KEYCLOAK_REALM doit être défini dans les variables d'environnement. "
            "Configurez Keycloak dans votre fichier .env."
        )
    
    # Récupérer les autres paramètres
    client_id = config.keycloak_client_id
    client_secret = config.keycloak_client_secret
    base_url = config.mcp_base_url
    scopes_str = config.keycloak_scopes
    required_scopes = [s.strip() for s in scopes_str.split() if s.strip()]
    
    # Vérifier que le client_id est défini
    if not client_id:
        raise ValueError(
            "KEYCLOAK_CLIENT_ID doit être défini dans les variables d'environnement. "
            "Créez un client dans Keycloak et configurez son ID."
        )
    
    # Construire les URLs Keycloak (séparées pour PUBLIC et INTERNAL)
    keycloak_public_url = keycloak_public_url.rstrip('/')
    keycloak_internal_url = keycloak_internal_url.rstrip('/')
    realm_public = f"{keycloak_public_url}/realms/{config.keycloak_realm}"
    realm_internal = f"{keycloak_internal_url}/realms/{config.keycloak_realm}"
    
    # Authorization endpoint utilise l'URL PUBLIQUE (redirection navigateur)
    authorization_endpoint = f"{realm_public}/protocol/openid-connect/auth"
    
    # Token endpoint et JWKS utilisent l'URL INTERNE (appels API backend)
    token_endpoint = f"{realm_internal}/protocol/openid-connect/token"
    jwks_uri = f"{realm_internal}/protocol/openid-connect/certs"
    
    # Créer le JWT verifier pour Keycloak
    # Le verifier récupère automatiquement les clés publiques JWKS depuis Keycloak
    # et vérifie la signature, l'expiration, l'issuer, l'audience et les scopes
    # L'issuer utilise l'URL INTERNE pour la vérification JWT
    logger.info(f"JWKS URI: {jwks_uri}")
    logger.info(f"Issuer: {realm_public}")
    logger.info(f"Required scopes: {required_scopes}")
    token_verifier = MyJWTVerifier(
        jwks_uri=jwks_uri,
        issuer=realm_public,
        required_scopes=required_scopes if required_scopes else None
    )
    
    # Créer l'OAuth proxy
    # Le proxy gère automatiquement:
    # - Les endpoints OAuth discovery (/.well-known/oauth-authorization-server, etc.)
    # - Le flux OAuth complet avec DCR
    # - La gestion des tokens avec chiffrement
    # - Le support PKCE
    # - La protection contre les attaques "confused deputy" via consent screen
    auth_provider = OAuthProxy(
        upstream_authorization_endpoint=authorization_endpoint,
        upstream_token_endpoint=token_endpoint,
        upstream_client_id=client_id,
        upstream_client_secret=client_secret,  # None pour client public
        token_verifier=token_verifier,
        base_url=base_url
    )
    
    return auth_provider

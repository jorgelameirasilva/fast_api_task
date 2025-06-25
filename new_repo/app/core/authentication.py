import json
import logging
import os
import time
import datetime
from tempfile import TemporaryDirectory
from typing import Any, Optional

import aiohttp
from functools import wraps

from msal import ConfidentialClientApplication
from msal_extensions import (
    FilePersistence,
    PersistedTokenCache,
    build_encrypted_persistence,
)

import jwt
from jwt import PyJWTError, PyJWKClient
from fastapi import Request, HTTPException
from .config import settings


class AuthError(Exception):
    def __init__(self, error: str, status_code: int = 401):
        self.error = error
        self.status_code = status_code


def token_required(f):
    """Decorator for token validation"""

    @wraps(f)
    async def decorated_function(*args, **kwargs):
        # Extract request from args (FastAPI passes request as first argument)
        request = None
        for arg in args:
            if isinstance(arg, Request):
                request = arg
                break

        if not request:
            raise HTTPException(status_code=500, detail="Request object not found")

        if settings.AZURE_USE_AUTHENTICATION:
            AUDIENCE = settings.AZURE_CLIENT_APP_ID
            ISSUER = "https://login.microsoftonline.com/53b7cac7-14be-46d4-be43-f2ad9244d901/v2.0"
            JWKS_URL = f"https://login.microsoftonline.com/53b7cac7-14be-46d4-be43-f2ad9244d901/discovery/v2.0/keys"

            now = datetime.datetime.now()
            current_timestamp = int(now.timestamp())

            auth = request.headers.get("Authorization", None)
            if not auth:
                raise AuthError(
                    error={
                        "code": "authorization_header_missing",
                        "description": "Authorization header is expected",
                    },
                    status_code=401,
                )

            parts = auth.split()
            if parts[0].lower() != "bearer":
                raise AuthError(
                    error={
                        "code": "invalid_header",
                        "description": "Authorization header must start with Bearer",
                    },
                    status_code=401,
                )
            elif len(parts) == 1:
                raise AuthError(
                    error={"code": "invalid_header", "description": "Token not found"},
                    status_code=401,
                )
            elif len(parts) > 2:
                raise AuthError(
                    error={
                        "code": "invalid_header",
                        "description": "Authorization header must be a bearer token",
                    },
                    status_code=401,
                )

            token = auth.split()[-1].strip()
            jwk_client = PyJWKClient(JWKS_URL)
            signing_key = jwk_client.get_signing_key_from_jwt(token)
            decoded_token = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience=AUDIENCE,
                issuer=ISSUER,
            )

            if decoded_token["iss"] != ISSUER:
                raise AuthError(
                    error={
                        "code": "invalid_issuer",
                        "description": "Token contains Invalid Issuer",
                    },
                    status_code=401,
                )

            if decoded_token["aud"] != AUDIENCE:
                raise AuthError(
                    error={
                        "code": "invalid_audience",
                        "description": "Token contains Invalid Audience",
                    },
                    status_code=401,
                )

            if decoded_token["exp"] < current_timestamp:
                return AuthError(error="Token has expired")

        return await f(*args, **kwargs)

    return decorated_function


class AuthenticationHelper:
    scope: str = "https://graph.microsoft.com/.default"

    def __init__(
        self,
        *,
        use_authentication: bool,
        server_app_id: Optional[str],
        server_app_secret: Optional[str],
        client_app_id: Optional[str],
        tenant_id: Optional[str],
        token_cache_path: Optional[str] = None,
    ):
        self.use_authentication = use_authentication
        self.server_app_id = server_app_id
        self.server_app_secret = server_app_secret
        self.client_app_id = client_app_id
        self.tenant_id = tenant_id
        self.authority = f"https://login.microsoftonline.com/{tenant_id}"

        if self.use_authentication:
            self.token_cache_path = token_cache_path
            if not self.token_cache_path:
                self.temporary_directory = TemporaryDirectory()
                self.token_cache_path = os.path.join(
                    self.temporary_directory.name, "token_cache.bin"
                )
            try:
                persistence = build_encrypted_persistence(
                    location=self.token_cache_path
                )
            except Exception:
                logging.exception("Encryption unavailable. Opting in to plain text.")
                persistence = FilePersistence(location=self.token_cache_path)
            self.confidential_client = ConfidentialClientApplication(
                server_app_id,
                authority=self.authority,
                client_credential=server_app_secret,
                token_cache=PersistedTokenCache(persistence),
            )

    def get_auth_setup_for_client(self) -> dict[str, Any]:
        return {
            "useLogin": self.use_authentication,
            "msalConfig": {
                "auth": {
                    "clientId": self.client_app_id,
                    "authority": self.authority,
                    "redirectUri": "/redirect",
                    "postLogoutRedirectUri": "/",
                    "navigateToLoginRequestUrl": "/",
                },
                "cache": {
                    "cacheLocation": "sessionStorage",
                    "storeAuthStateInCookie": False,
                },
            },
            "loginRequest": {
                "scopes": [".default"],
                # Uncomment the following line to cause a consent dialog to appear
                # For more information, please visit https://learn.microsoft.com
                # "prompt": "consent"
            },
            "tokenRequest": {
                "scopes": [f"api://{self.server_app_id}/access_as_user"],
            },
        }

    @staticmethod
    def get_token_auth_header(headers: dict) -> str:
        """Obtains the Access Token from the Authorization Header"""
        auth = headers.get("Authorization", None)
        if not auth:
            raise AuthError(
                {
                    "code": "authorization_header_missing",
                    "description": "Authorization header is expected",
                },
                status_code=401,
            )

        parts = auth.split()

        if parts[0].lower() != "bearer":
            raise AuthError(
                {
                    "code": "invalid_header",
                    "description": "Authorization header must start with Bearer",
                },
                status_code=401,
            )

        elif len(parts) == 1:
            raise AuthError(
                {"code": "invalid_header", "description": "Token not found"},
                status_code=401,
            )

        elif len(parts) > 2:
            raise AuthError(
                {
                    "code": "invalid_header",
                    "description": "Authorization header must be a bearer token",
                },
                status_code=401,
            )

        token = parts[1]
        return token

    @staticmethod
    def build_security_filters(
        overrides: dict[str, Any], auth_claims: dict[str, Any]
    ) -> Optional[str]:
        """
        Build security filters for search queries based on auth claims.
        """
        if not auth_claims:
            return None

        groups = auth_claims.get("groups", [])
        if not groups:
            return None

        if overrides.get("use_oid_security_filter"):
            return f"oid eq '{auth_claims.get('oid')}'"

        if overrides.get("use_groups_security_filter"):
            groups_filter_list = [
                f"groups/any(g:search.in(g, '{group}'))" for group in groups
            ]
            return f"({' or '.join(groups_filter_list)})"

        return None

    @staticmethod
    async def list_groups(graph_resource_access_token: dict) -> list[str]:
        """
        Get list of groups from Microsoft Graph API.
        """
        groups = []
        graph_url = "https://graph.microsoft.com/v1.0/me/transitiveMemberOf/microsoft.graph.group?$select=id"

        async with aiohttp.ClientSession() as session:
            headers = {
                "Authorization": f"Bearer {graph_resource_access_token['access_token']}",
                "ConsistencyLevel": "eventual",
            }
            async with session.get(graph_url, headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    for group in data.get("value", []):
                        groups.append(group["id"])

                    # Handle pagination
                    while "@odata.nextLink" in data:
                        async with session.get(
                            data["@odata.nextLink"], headers=headers
                        ) as next_resp:
                            if next_resp.status == 200:
                                data = await next_resp.json()
                                for group in data.get("value", []):
                                    groups.append(group["id"])
                            else:
                                break
                else:
                    logging.warning(
                        f"Failed to get groups from Graph API: {resp.status}"
                    )

        return groups

    async def get_auth_claims_if_enabled(self, headers: dict) -> dict[str, Any]:
        """
        Get authentication claims if authentication is enabled.
        """
        if not self.use_authentication:
            return {}

        try:
            access_token = self.get_token_auth_header(headers)
            graph_resource_access_token = (
                self.confidential_client.acquire_token_on_behalf_of(
                    user_assertion=access_token, scopes=[self.scope]
                )
            )

            if "error" in graph_resource_access_token:
                logging.error(
                    f"Error acquiring token: {graph_resource_access_token['error']}"
                )
                return {}

            # Get user groups
            groups = await self.list_groups(graph_resource_access_token)

            # Decode the access token to get user claims
            decoded_token = jwt.decode(
                access_token, options={"verify_signature": False}
            )

            return {
                "oid": decoded_token.get("oid"),
                "groups": groups,
                "name": decoded_token.get("name"),
                # Add other claims as needed
            }

        except Exception as e:
            logging.exception(f"Error getting auth claims: {e}")
            return {}

import json
import logging
import os
import time
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
from jwt import PyJWTError
from fastapi import Request, HTTPException


class AuthError(Exception):
    def __init__(self, error: str, status_code: int = 401):
        self.error = error
        self.status_code = status_code


class AuthenticationHelper:
    scope: str = "https://graph.microsoft.com/.default"
    _instance: Optional["AuthenticationHelper"] = None

    # JWT validation constants
    JWKS_URL = "https://login.microsoftonline.com/common/discovery/keys"
    ISSUER = "https://sts.windows.net/"
    AUDIENCE = None  # Will be set based on server_app_id

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

        # Set the audience for JWT validation
        if server_app_id:
            self.AUDIENCE = f"api://{server_app_id}"

        # Set the issuer based on tenant
        if tenant_id:
            self.ISSUER = f"https://sts.windows.net/{tenant_id}/"

        # Store instance for decorator access
        AuthenticationHelper._instance = self

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

    @classmethod
    def get_instance(cls) -> Optional["AuthenticationHelper"]:
        """Get the current authentication helper instance"""
        return cls._instance

    async def validate_token_from_request(self, request: Request) -> dict[str, Any]:
        """Validate JWT token from FastAPI request headers"""
        headers = dict(request.headers)
        token = self.get_token_auth_header(headers)
        return await self.validate_jwt_token(token)

    async def validate_jwt_token(self, token: str) -> dict[str, Any]:
        """
        Validate JWT token with comprehensive checks
        Returns decoded token claims if valid, raises AuthError if invalid
        """
        try:
            # Get signing key from Azure AD
            jwk_client = jwt.PyJWKClient(self.JWKS_URL)
            signing_key = jwk_client.get_signing_key_from_jwt(token)

            # Decode and validate token
            decoded_token = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience=self.AUDIENCE,
                issuer=self.ISSUER,
            )

            # Additional validation checks
            current_timestamp = time.time()

            # Check token expiration
            if decoded_token.get("exp", 0) < current_timestamp:
                raise AuthError(error="Token has expired", status_code=401)

            # Check issuer
            if decoded_token.get("iss") != self.ISSUER:
                raise AuthError(
                    error={
                        "code": "invalid_issuer",
                        "description": "Token contains Invalid Issuer",
                    },
                    status_code=401,
                )

            # Check audience
            if decoded_token.get("aud") != self.AUDIENCE:
                raise AuthError(
                    error={
                        "code": "invalid_audience",
                        "description": "Tokens contain Invalid Audience",
                    },
                    status_code=401,
                )

            return decoded_token

        except jwt.ExpiredSignatureError:
            raise AuthError(error="Token has expired", status_code=401)
        except jwt.InvalidTokenError as e:
            raise AuthError(error=f"Invalid token: {str(e)}", status_code=401)
        except Exception as e:
            logging.exception("Token validation failed")
            raise AuthError(error=f"Token validation failed: {str(e)}", status_code=401)

    def get_auth_setup_for_client(self) -> dict[str, Any]:
        """Returns JSON list settings used by the client app"""
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
                "scopes": ["openid", "profile", "email"],
                "prompt": "consent",
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
                401,
            )

        parts = auth.split()

        if parts[0].lower() != "bearer":
            raise AuthError(
                {
                    "code": "invalid_header",
                    "description": "Authorization header must start with Bearer",
                },
                401,
            )

        elif len(parts) == 1:
            raise AuthError(
                {"code": "invalid_header", "description": "Token not found"}, 401
            )

        elif len(parts) > 2:
            raise AuthError(
                {
                    "code": "invalid_header",
                    "description": "Authorization header must be a bearer token",
                },
                401,
            )

        token = parts[1]
        return token

    @staticmethod
    def build_security_filters(
        overrides: dict[str, Any], auth_claims: dict[str, Any]
    ) -> Optional[str]:
        """
        Builds a security filter to restrict search results based on user's access claims filters
        https://learn.microsoft.com/en-us/azure/search/search-security-trimming-for-azure-search
        https://learn.microsoft.com/en-us/azure/search/search-security-trimming-for-azure-search-with-aad
        """
        use_oid_security_filter = overrides.get("use_oid_security_filter")
        use_groups_security_filter = overrides.get("use_groups_security_filter")

        oid_security_filter = (
            "oid eq '{}'".format(auth_claims.get("oid") or "")
            if use_oid_security_filter
            else None
        )

        groups_security_filter = None
        if use_groups_security_filter:
            groups = auth_claims.get("groups") or []
            if groups:
                groups_filter_parts = [f'search.ismatch("{group}")' for group in groups]
                groups_security_filter = " or ".join(groups_filter_parts)

        # If only one security filter is specified, return that filter
        # If both security filters are specified, combine them with "or" as only 1 security filter needs to pass
        # If no security filters are specified, don't return any filter
        if oid_security_filter and not groups_security_filter:
            return oid_security_filter
        elif not oid_security_filter and groups_security_filter:
            return groups_security_filter
        elif oid_security_filter and groups_security_filter:
            return f"({oid_security_filter}) or ({groups_security_filter})"
        else:
            return None

    @staticmethod
    async def list_groups(graph_resource_access_token: dict) -> list[str]:
        headers = {
            "Authorization": "Bearer " + graph_resource_access_token["access_token"]
        }
        groups = []
        async with aiohttp.ClientSession(headers=headers) as session:
            resp_json = None
            resp_status = None
            async with session.get(
                url="https://graph.microsoft.com/v1.0/me/transitiveMemberOf?$select=id"
            ) as resp:
                resp_json = await resp.json()
                resp_status = resp.status
                if resp_status != 200:
                    raise AuthError(
                        error=json.dumps(resp_json), status_code=resp_status
                    )

            while resp_status == 200:
                value = resp_json["value"]
                for group in value:
                    groups.append(group["id"])
                next_link = resp_json.get("@odata.nextLink")
                if next_link:
                    async with session.get(url=next_link) as resp:
                        resp_json = await resp.json()
                        resp_status = resp.status
                else:
                    break
            if resp_status != 200:
                raise AuthError(error=json.dumps(resp_json), status_code=resp_status)

        return groups

    async def get_auth_claims_if_enabled(self, headers: dict) -> dict[str, Any]:
        if not self.use_authentication:
            return {}

        try:
            # First try JWT validation for direct token validation
            try:
                token = self.get_token_auth_header(headers)
                decoded_token = await self.validate_jwt_token(token)

                # Extract claims from JWT token
                auth_claims = {
                    "oid": decoded_token.get("oid"),
                    "groups": decoded_token.get("groups", []),
                    "sub": decoded_token.get("sub"),
                    "name": decoded_token.get("name"),
                    "email": decoded_token.get("email") or decoded_token.get("upn"),
                }
                return auth_claims

            except AuthError:
                # Fall back to On Behalf Of Flow if JWT validation fails
                pass

            # Read the token from the Authorization header and exchange it using the On Behalf Of Flow
            auth_token = AuthenticationHelper.get_token_auth_header(headers)
            graph_resource_access_token = (
                self.confidential_client.acquire_token_on_behalf_of(
                    user_assertion=auth_token,
                    scopes=["https://graph.microsoft.com/.default"],
                )
            )

            if "error" in graph_resource_access_token:
                raise AuthError(error=str(graph_resource_access_token), status_code=401)

            # Read the claims from the response
            id_token_claims = graph_resource_access_token.get("id_token_claims", {})
            auth_claims = {
                "oid": id_token_claims.get("oid"),
                "groups": id_token_claims.get("groups") or [],
            }

            # Handle groups overage claim
            missing_groups_claim = "groups" not in id_token_claims
            has_group_overage_claim = any(
                ("groups" in key) and (value is not None)
                for key, value in id_token_claims.items()
            )
            if missing_groups_claim or has_group_overage_claim:
                auth_claims["groups"] = await AuthenticationHelper.list_groups(
                    graph_resource_access_token
                )

            return auth_claims
        except AuthError as e:
            print(e.error)
            logging.exception("Exception getting authorization information")
            return {}
        except Exception:
            logging.exception("Exception getting authorization information")
            return {}

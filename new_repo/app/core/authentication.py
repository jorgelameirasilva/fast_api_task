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

        REQUIRE_AUTHENTICATION = int(os.environ.get("REQUIRE_AUTHENTICATION", 1))

        if REQUIRE_AUTHENTICATION:
            AUDIENCE = os.environ.get("APP_AUTHENTICATION_CLIENT_ID", None)
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
        Build different permutations of the oid or groups security filter
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
            # Read the authentication token from the authorization header and
            # The scope is set to the Microsoft Graph API, which may need to be
            # https://learn.microsoft.com/en-us/azure/active-directory/develop/
            auth_token = AuthenticationHelper.get_token_auth_header(headers)
            graph_resource_access_token = (
                self.confidential_client.acquire_token_on_behalf_of(
                    user_assertion=auth_token,
                    scopes=["https://graph.microsoft.com/.default"],
                )
            )

            if "error" in graph_resource_access_token:
                raise AuthError(error=str(graph_resource_access_token), status_code=401)

            # Read the claims from the response. The oid and groups claims are
            # https://learn.microsoft.com/en-us/azure/active-directory/develop/id-token-claims
            id_token_claims = graph_resource_access_token.get("id_token_claims", {})
            auth_claims = {
                "oid": id_token_claims.get("oid"),
                "groups": id_token_claims.get("groups") or [],
            }

            # A groups claim may have been omitted either because it was not
            # or a groups overage claim may have been emitted.
            # https://learn.microsoft.com/en-us/azure/active-directory/develop/id-token-claims
            missing_groups_claim = "groups" not in id_token_claims
            has_group_overage_claim = any(
                ("groups" in key) and (value is not None)
                for key, value in id_token_claims.items()
            )
            if missing_groups_claim or has_group_overage_claim:
                # Read the user's groups from Microsoft Graph
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

from abc import ABC
from typing import Any, AsyncGenerator, Optional, Union

from app.core.authentication import AuthenticationHelper


class Approach(ABC):
    def build_filter(
        self, overrides: dict[str, Any], auth_claims: dict[str, Any]
    ) -> Optional[str]:
        selected_category = overrides.get("selected_category") or None
        security_filter = AuthenticationHelper.build_security_filters(
            overrides, auth_claims
        )
        filters = []
        if selected_category:
            filters.append(
                "category eq '{}'".format(selected_category.replace("'", "''"))
            )
        if security_filter:
            filters.append(security_filter)
        return None if len(filters) == 0 else " and ".join(filters)

    async def run(
        self,
        messages: list[dict],
        stream: bool = False,
        session_state: Any = None,
        context: dict[str, Any] = None,
    ) -> Union[dict[str, Any], AsyncGenerator[dict[str, Any], None]]:
        raise NotImplementedError

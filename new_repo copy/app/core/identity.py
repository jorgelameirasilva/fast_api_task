import requests
import jwt

from azure.core.credentials import AccessToken


class OneAccount:

    def __init__(
        self, client_id: str, client_secret: str, apim_key: str, apim_login_url: str
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.apim_key = apim_key
        self.apim_login_url = apim_login_url

    def get_token(self) -> AccessToken:
        header = {
            "Client_Id": self.client_id,
            "Client_Secret": self.client_secret,
            "Scope": "urn:grp:chatgpt",
            "Cache-Control": "no-cache",
            "Ocp-Apim-Subscription-Key": self.apim_key,
        }

        token = requests.post(self.apim_login_url, headers=header).json()[
            "access_token"
        ]
        expires_on = jwt.decode(token, options={"verify_signature": False})["exp"]
        access_token = AccessToken(token, expires_on)
        return access_token

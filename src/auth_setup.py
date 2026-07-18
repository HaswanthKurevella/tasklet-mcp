from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
import os

SCOPES = ["https://www.googleapis.com/auth/tasks"]
CLIENT_SECRET_FILE = "credentials/client_secret.json"
TOKEN_FILE = "credentials/token.json"

flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
creds = flow.run_local_server(port=0)
with open(TOKEN_FILE, "w") as f:
    f.write(creds.to_json())

print("Success — token.json written.")

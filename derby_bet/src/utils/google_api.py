# Imports
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from pathlib import Path
import pickle
from derby_bet.src.utils.io_tools import find_project_root

SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
SPREADSHEET_ID = '1EKopkgD6Qqehk-WRzoMCKpT-3e7bErJShr0nZwYEw38'
TRANSACTION_RANGE_NAME = 'TransactionResponses!A:C'
WAGER_RANGE_NAME = 'WagerResponses!A:I'

_BASE_DIR = find_project_root()


def get_sheet_service():
    creds = None

    token_fp = Path(_BASE_DIR, '.auth', 'tokens.pkl')
    cred_fp = Path(_BASE_DIR, '.auth', 'credentials.json')

    if token_fp.exists():
        with open(str(token_fp), 'rb') as token:
            creds = pickle.load(token)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(cred_fp), SCOPES)
            creds = flow.run_local_server(port=0)

        with open(str(token_fp), 'wb') as token:
            pickle.dump(creds, token)
        
    service = build('sheets', 'v4', credentials=creds)
    return service


def get_form_responses(form_range):
    services = get_sheet_service()

    result = services.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID,
        range=form_range
    ).execute()

    values = result.get('values', [])

    if not values:
        return []

    headers = values[0]
    rows = values[1:]

    responses = []
    for row in rows:
        row_dict = {}
        for i, header in enumerate(headers):
            row_dict[header] = row[i] if i < len(row) else ''
        responses.append(row_dict)
    
    return responses


if __name__ == '__main__':
    responses = get_form_responses(WAGER_RANGE_NAME)
    print(f'Found {len(responses)} responses')
    for response in responses[:3]:
        print(response)

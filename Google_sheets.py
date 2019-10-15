'''
For instructions on how to run: https://developers.google.com/sheets/quickstart/python

pip install --upgrade google-api-python-client
'''

from __future__ import print_function
import httplib2
import os
import pickle

from apiclient import discovery,errors

from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# If modifying these scopes, delete your previously saved credentials
# at ~/.credentials/sheets.googleapis.com-python-quickstart.json
SCOPES = 'https://www.googleapis.com/auth/spreadsheets'
CLIENT_SECRET_FILE = 'client_secret.json'
APPLICATION_NAME = 'EU4 MP Stats Updater'


def get_credentials(credentials_dir):
    """Gets valid user credentials from storage.

    If nothing has been stored, or if the stored credentials are invalid,
    the OAuth2 flow is completed to obtain the new credentials.

    Returns:
        Credentials, the obtained credential.
    """
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    token_file_path=os.path.join(credentials_dir, 'token.pickle')
    if os.path.exists(token_file_path):
        with open(token_file_path, 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                os.path.join(credentials_dir, CLIENT_SECRET_FILE), # clientsecret file
                SCOPES
            )
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open(token_file_path, 'wb') as token:
            pickle.dump(creds, token)
    return creds

def get_cellrange(name, rowlength, rowstart=1, columnlength=1, columnstart=1):
    '''Currently does not support rowlength>25'''
    cellrange = name+'!A{}:'.format(rowstart)
    cellrange += chr(65+rowlength) + str(rowstart+columnlength-1)
    return cellrange

class Sheet:
    def __init__(self, SheetProperties):
        self.json = SheetProperties
        self.Id = SheetProperties['properties']['sheetId']
        self.title = SheetProperties['properties']['title']
        self.index = SheetProperties['properties']['index']
        self.Type = SheetProperties['properties']['sheetType']
        self.gridProperties = SheetProperties['properties']['gridProperties']

class Spreadsheet:
    def __init__(self, spreadsheetId, credentials_dir='./', retry_initialisation=False):
        self.ssId=spreadsheetId

        credentials = get_credentials(credentials_dir)
        discoveryUrl = ('https://sheets.googleapis.com/$discovery/rest?'
                    'version=v4')
        self.service = discovery.build('sheets', 'v4',credentials=credentials,
                              discoveryServiceUrl=discoveryUrl)

        self.sheets = {sheet['properties']['title']:Sheet(sheet) for sheet in self.service.spreadsheets().get(
                        spreadsheetId=self.ssId, includeGridData=True).execute()['sheets']}
        self.batch = {"valueInputOption": "USER_ENTERED", "data": []}

    def batchUpdate(self, values, cellrange, majorDimension='ROWS'):
        self.batch['data'].append({'range':cellrange, 'majorDimension':majorDimension, 'values':values})

    def batchExecute(self):
         resp = self.service.spreadsheets().values().batchUpdate(spreadsheetId=self.ssId,
                                                                    body=self.batch).execute()
         self.batch = {"valueInputOption": "USER_ENTERED","data": []}
         return resp

    def get_sheet(self, title):
        return self.sheets.get(title)

    def get_sheet_values(self, cellrange):
        response=self.service.spreadsheets().values().get(
                           spreadsheetId=self.ssId, range=cellrange).execute()
        return response.get('values', [])

    def add_sheet(self, title, num_rows=4515, num_columns=26, rgb=(0,0,0)):
        r,g,b = rgb
        request_body = {'requests':[{'addSheet':{'properties':{
            'title':title, 'gridProperties':{
                'rowCount':num_rows, 'columnCount':num_columns},
            'tabColor':{
                'red':r, 'green':g, 'blue':b}}}}]}
        try:
            response = self.service.spreadsheets().batchUpdate(spreadsheetId=self.ssId,
                                                             body=request_body).execute()
            sheet = Sheet(response['replies'][0]['addSheet'])
            self.sheets[sheet.title]=sheet
            return sheet
        except errors.HttpError as err:
            print(err)

    def clear_values(self, title):
        '''Preserves formatting'''
        request_body = {'requests': [{'updateCells': {
            'range': {'sheetId': self.get_sheet(title).Id},
            'fields': 'userEnteredValue'}}]}
        self.service.spreadsheets().batchUpdate(spreadsheetId=self.ssId,
                                                body=request_body).execute()

    def append_values(self, values, cellrange, inptOption='USER_ENTERED'):
        '''cellrange specifies sheet and range'''
        request_body = {'range':cellrange, 'majorDimension':'ROWS', 'values':values}
        self.service.spreadsheets().values().append(spreadsheetId=self.ssId,
                                                    range=cellrange,
                                                    body=request_body,
                                                    valueInputOption=inptOption).execute()

    def copy_sheet_to(self, sheet, target_ssId):
        request_body={"destinationSpreadsheetId": target_ssId}
        self.service.spreadsheets().sheets().copyTo(spreadsheetId=self.ssId,
                                                    sheetId=sheet.Id,
                                                    body=request_body).execute()

    def delete_sheet(self, sheet):
        request_body = {"requests": [{
            "deleteSheet": {
                "sheetId": sheet.Id}}]}
        self.service.spreadsheets().batchUpdate(spreadsheetId=self.ssId,
                                                body=request_body).execute()

def main():
    '''Clears all non-protected sheets (graphs and formatting is preserved).'''
    from settings import SPREADSHEET_ID, variables

    ss=Spreadsheet(SPREADSHEET_ID,os.getcwd())
    for var in variables:
        if var not in ss.sheets:
            ss.add_sheet(var)
    if input("Clear all values of spreadsheet '%s'? (y/n) " % ss.ssId).lower() == 'y':
        for title in ss.sheets.keys():
            try:
                ss.clear_values(title)
            except errors.HttpError as err:
                print("Did not clear protected sheet '%s'." % title)

if __name__ == '__main__':
    main()

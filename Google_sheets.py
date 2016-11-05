'''
For instructions on how to run: https://developers.google.com/sheets/quickstart/python

pip install --upgrade google-api-python-client
'''

from __future__ import print_function
import httplib2
import os

from apiclient import discovery,errors
import oauth2client
from oauth2client import client
from oauth2client import tools

try:
    import argparse
    flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
except ImportError:
    flags = None

# If modifying these scopes, delete your previously saved credentials
# at ~/.credentials/sheets.googleapis.com-python-quickstart.json
SCOPES = 'https://www.googleapis.com/auth/spreadsheets'
CLIENT_SECRET_FILE = 'client_secret.json'
APPLICATION_NAME = 'EU4 MP Stats Updater'


def get_credentials():
    """Gets valid user credentials from storage.

    If nothing has been stored, or if the stored credentials are invalid,
    the OAuth2 flow is completed to obtain the new credentials.

    Returns:
        Credentials, the obtained credential.
    """
    home_dir = os.path.expanduser('~')
    credential_dir = os.path.join(home_dir, '.credentials')
    if not os.path.exists(credential_dir):
        os.makedirs(credential_dir)
    credential_path = os.path.join(credential_dir,
                                   'sheets.googleapis.com-python-quickstart.json')

    store = oauth2client.file.Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME
        if flags:
            credentials = tools.run_flow(flow, store, flags)
        else: # Needed only for compatibility with Python 2.6
            credentials = tools.run(flow, store)
        print('Storing credentials to ' + credential_path)
    return credentials

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
    def __init__(self, spreadsheetId):
        self.ssId=spreadsheetId
        
        credentials = get_credentials()
        http = credentials.authorize(httplib2.Http())
        discoveryUrl = ('https://sheets.googleapis.com/$discovery/rest?'
                    'version=v4')
        self.service = discovery.build('sheets', 'v4', http=http,
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
    
    ss=Spreadsheet(SPREADSHEET_ID)
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
    
    
    
    
    
    
    
    
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

class Sheet:
    def __init__(self,SheetProperties):
        self.json=SheetProperties
        self.Id=SheetProperties['properties']['sheetId']
        self.title=SheetProperties['properties']['title']
        self.index=SheetProperties['properties']['index']
        # The above are used more frequently.
        
        self.Type=SheetProperties['properties']['sheetType']
        self.gridProperties=SheetProperties['properties']['gridProperties']
        self.hidden=SheetProperties['properties']['hidden']
        self.tabColor=SheetProperties['properties']['tabColor']
        self.rightToLeft=SheetProperties['properties']['rightToLeft']
        
class Spreadsheet:
    def __init__(self,spreadsheetId): #may want to change accessing sheets by title to accessing by sheetobject.
        self.ssId=spreadsheetId
        
        credentials = get_credentials()
        http = credentials.authorize(httplib2.Http())
        discoveryUrl = ('https://sheets.googleapis.com/$discovery/rest?'
                    'version=v4')
        self.service = discovery.build('sheets', 'v4', http=http,
                              discoveryServiceUrl=discoveryUrl)
        
        self.sheets=self.service.spreadsheets().get(spreadsheetId=self.ssId).execute()['sheets']
    
    def get_sheet(self, title):
        for sheet in self.sheets:
            if sheet.title == title:
                return sheet
        else:
            raise NameError("No sheet with title '%s' was found."%title)
        
    def add_sheet(self,title,num_rows=500, num_columns=200,rgb=(0,0,0)):
        r,g,b = rgb
        request_body = {'requests':[{'addSheet':{'properties':{
            'title':title,'gridProperties':{
                'rowCount':num_rows,'columnCount':num_columns},
            'tabColor':{
                'red':r,'green':g,'blue':b}}}}]}
        try:
            response=self.service.spreadsheets().batchUpdate(spreadsheetId=self.ssId,
                                                             body=request_body).execute()
            self.sheets.append(Sheet(response['replies'][0]['addSheet']))
            print(response)
        except errors.HttpError:
            print("NOTE: spreadsheet with name '%s' already exists." % title) 
    
    def clear_values(self,title):
        '''Preserves formatting'''
        request_body = {'requests': [{'updateCells': {
            'range': {'sheetId': self.get_sheetId(title)},
            'fields': 'userEnteredValue'}}]}
        self.service.spreadsheets().batchUpdate(spreadsheetId=self.ssId,
                                                body=request_body).execute()
    
    def append_values(self,values,cellrange,inptOption='USER_ENTERED'):
        '''cellrange specifies sheet and range'''
        request_body = {'range':cellrange,'majorDimension':'ROWS','values':values}
        self.service.spreadsheets().values().append(spreadsheetId=self.ssId,
                                                    range=cellrange,
                                                    body=request_body,
                                                    valueInputOption=inptOption).execute()
    
    def copy_sheet_to(self,sheet, target_ssId):
        request_body={"destinationSpreadsheetId": target_ssid}
        self.service.spreadsheets().sheets().copyTo(spreadsheetId=self.ssId,
                                                    sheetId=sheet.Id,
                                                    body=request_body).execute()

    def delete_sheet(self,sheet):
        request_body = {"requests": [{
            "deleteSheet": {
                "sheetId": sheet.Id}}]}
        self.service.spreadsheets().batchUpdate(spreadsheetId=self.ssId, 
                                                body=request_body).execute()
        
def main():
    SS=Spreadsheet('12YdppOoZUNZxhXvcY_cRgfXEfRnR_izlBsF8Sin3rw4')
    SS.add_sheet('testing')
    values=[["Door", "$15", "2", "3/15/2016"],["Engine", "$100", "1", "3/20/2016"]]
    SS.append_values(values,'testing!A1:E1')
    SS.copy_sheet_to('testing','1unIM0L_Jpgy7hIDOY2srYHFndWRFLCDEdhP_G55cNCc')
    SS2=Spreadsheet('1unIM0L_Jpgy7hIDOY2srYHFndWRFLCDEdhP_G55cNCc')
    SS2.delete_sheet('Kopia av testing')
    
if __name__ == '__main__':
    main()
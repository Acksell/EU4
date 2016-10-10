USERNAME='USERNAME'
tags = ['FRA','CAS','ENG','TUR','BUR','HAB', 'POL','ARA']
variables = ['base_tax','raw_development','military_strength','treasury','estimated_monthly_income','non_overseas_development','manpower',
               'num_of_provinces_in_states','num_of_provinces_in_territories'] 
SPREADSHEET_ID = "12YdppOoZUNZxhXvcY_cRgfXEfRnR_izlBsF8Sin3rw4"

if __name__ == '__main__':
    '''Update first row tags in every sheet.'''
    from Google_sheets import Spreadsheet,get_cellrange
    
    SS=Spreadsheet(SPREADSHEET_ID)
    for var in variables:
        SS.batchUpdate([['Date',*tags]], get_cellrange(var, len(tags)+1))
    SS.batchExecute()
    
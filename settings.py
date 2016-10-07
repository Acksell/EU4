tags = ['FRA','CAS','ENG','TUR','BUR','HAB','DAN', 'POL']
variables = ['base_tax','raw_development','military_strength','treasury','estimated_monthly_income','non_overseas_development','manpower',
               'num_of_provinces_in_states','num_of_provinces_in_territories'] 

if __name__ == '__main__':
    '''Update headers in every sheet.'''
    from Google_sheets import Spreadsheet,get_cellrange
    
    SS=Spreadsheet('12YdppOoZUNZxhXvcY_cRgfXEfRnR_izlBsF8Sin3rw4')
    for var in variables:
        SS.batchUpdate([['Date',*tags]], get_cellrange(var, len(tags)+1))
    SS.batchExecute()
    
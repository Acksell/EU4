# coding: iso-8859-15

# 2016-08-31
# Axel Engström, Sci14

# Scrape an EU4 save file for stats
# Put into csv and upload to google spreadsheets?

import os
import re

USERNAME='Larsson'

savegame_dir = "C:\\Users\\{}\\Documents\\Paradox Interactive\\Europa Universalis IV\\save games".format(USERNAME)
os.chdir(savegame_dir)

def latest_eu4_save():
    files = filter(os.path.isfile, os.listdir(savegame_dir))
    files = [os.path.join(savegame_dir, f) for f in files] # add path to each file
    files.sort(key=lambda x: os.path.getmtime(x))
    return files[-1]

def EU4_scrape(savefile,variables, tags, get_provinces=True): 
    #NOTE reformat to default to catching only humans if tags not specified
    result_table = {tag:{} for tag in tags}
    with open(savefile, 'r') as save:
        for line in range(2):
            date = save.readline() # get date from 2nd line
        # remove var name and dots (yyyy/mm/dd)
        date = date[5:].replace('.','-').replace('.','-')[:-1] #:-1 to remove '\n'
        result_table['date']=date
        save_txt = save.read()
        for tag in tags: # make regex dependent on 
            prov_vars=['num_of_provinces_in_states','num_of_provinces_in_territories']
            if get_provinces and not set(prov_vars).issubset(variables):
                variables += ['num_of_provinces_in_states','num_of_provinces_in_territories']
            for var in variables:
                for patterns in ('human','has_set_government_name','government_rank'):  # json structure is different for humans and AI
                    pattern = r'{0}={{\n\t\t{2}=.*?{1}=(.*?)\n'.format(tag.upper(), var, patterns)
                    value = re.findall(pattern, save_txt, flags=re.DOTALL)
                    if value: break
                try:
                    result_table[tag][var] = value[0].replace('.',',')  #[0] because regex returns a list
                except IndexError as err:
                    os.chdir('C:\\Users\Larsson\Desktop\Programming\Python\Web\EU4-Scraper')
                    f=open('savefile.log','w')
                    f.write(save_txt)
                    f.close()
                    print(pattern)
                    print(tag,var,value)
                    raise err
        return result_table

def get_cellrange(name, rowlength, rowstart=1):
    '''Currently does not support rowlength>25'''
    cellrange=name+'!A{}:'.format(rowstart)
    cellrange+=chr(65+rowlength)+str(rowstart)
    return cellrange

def get_bracket_info():
    """
		subjects={
			"NEV"
			"LOR"
			"BRB"
			"FLA"
			"HOL"
		}
    """
    pass

class SheetNotFound(Exception):pass
    
if __name__ == '__main__':
    import time
    import Google_sheets
    from apiclient import errors
    SPREADSHEET_ID = "12YdppOoZUNZxhXvcY_cRgfXEfRnR_izlBsF8Sin3rw4"
    
    #tags = input('Enter country tags separated by a space: ').upper().split()
    tags = ['FRA','CAS','ENG']
    # non_overseas_development
    variables = ['base_tax','development','treasury','estimated_monthly_income','non_overseas_development'] 
    """		military_strength=65.06998
		military_strength_with_allies=117.03299
		army_strength=14.00861
		navy_strength=3.79999
        score
        inflation
        mercantilism
        manpower
        max_manpower
    """
    previous_modified_time = 0
    SS = Google_sheets.Spreadsheet(SPREADSHEET_ID)
    #any variable works, not just [0] (get_rowdata)
    row_insertion_index=1
    while True:
        try:
            print('listening')
            latest_save = latest_eu4_save()
            latest_modified_time = os.path.getmtime(latest_save)
            isfile=os.path.isfile(latest_save)
            filesize = os.path.getsize(latest_save)
            if latest_modified_time != previous_modified_time and isfile and filesize/1000>2000:
                print('NEW SAVE FOUND! It is at: ',latest_save)
                result_table = EU4_scrape(latest_save, variables, tags)
                
                for var in variables:
                    cellrange = get_cellrange(var, len(tags)+1, rowstart=row_insertion_index)
                    if SS.get_sheet(var):
                        if not SS.get_sheet_values(get_cellrange(var,len(tags)+1)):
                            SS.add_sheet(var)
                            SS.batchUpdate([['Date', *tags]], cellrange)
                            row_insertion_index+=1
                    else:
                        raise SheetNotFound('Sheet \'%s\' does not exist, please create it manually.')
                    values = [result_table[tag][var] for tag in tags]
                    SS.batchUpdate([[result_table['date'], *values]], cellrange)
                SS.batchExecute()
                row_insertion_index+=1
                previous_modified_time = latest_modified_time
            time.sleep(3)
        except errors.HttpError as err:
            print(err)
            time.sleep(15)
        
        
        
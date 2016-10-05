# coding: iso-8859-15

# 2016-08-31
# Axel Engström, Sci14

# Scrape an EU4 save file for stats
# Put into csv and upload to google spreadsheets?

import os
import re

USERNAME='Larsson'

savegame_dir = "C:\\Users\\{}\\Documents\\Paradox Interactive\\Europa Universalis IV\\save games".format(USERNAME)
running_wd=os.getcwd()
os.chdir(savegame_dir)

def latest_eu4_save():
    files = filter(os.path.isfile, os.listdir(savegame_dir))
    files = [os.path.join(savegame_dir, f) for f in files] # add path to each file
    files.sort(key=lambda x: os.path.getmtime(x))
    return files[-1]

def get_subject_nations(save_txt,tag):
    for pattern in ('human','has_set_government_name','government_rank'):  # json structure is different for different nations
        regex = r'{0}={{\n\t\t{2}=.*?{1}={{(.*?)}}'.format(tag.upper(),'subjects',pattern)
        #returns subject nations embedded by whitespaces and quotes
        regex_result = re.findall(regex,save_txt,flags=re.DOTALL)            
        if regex_result: break 
        
    #removes whitespaces
    regex_result=regex_result[0].split()

    #removes quotes and yields subject nation
    for nation in regex_result:
        yield nation.split('"')[1]
    
def EU4_scrape_nations(save_txt,variables, tags, get_provinces=True): 
    #NOTE reformat to default to catching only humans if tags not specified
    result_table = {tag:{} for tag in tags}
    for tag in tags: # make regex dependent on 
        for var in variables:
            for pattern in ('human','has_set_government_name','government_rank'):  # json structure is different for humans and AI
                regex = r'{0}={{\n\t\t{2}=.*?{1}=(.*?)\n'.format(tag.upper(), var, pattern)
                value = re.findall(regex, save_txt, flags=re.DOTALL)
                if value: break
            try:
                result_table[tag][var] = value[0].replace('.',',')  #[0] because regex returns a list
            except IndexError as err:
                os.chdir(running_wd)
                f=open('savefile.log','w')
                f.write(save_txt)
                f.write(pattern)
                f.write('tag:{0} var:{1} value: {2}'.format(tag,var,value))
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
    """generalisation of get_subject_nations()"""
    pass

class SheetNotFound(Exception):pass
    
if __name__ == '__main__':
    import time
    import Google_sheets
    from apiclient import errors
    SPREADSHEET_ID = "12YdppOoZUNZxhXvcY_cRgfXEfRnR_izlBsF8Sin3rw4"
    
    #tags = input('Enter country tags separated by a space: ').upper().split()
    tags = ['FRA','CAS','ENG','DAN','SWE','NOR']
    # non_overseas_development
    variables = ['base_tax','raw_development','treasury','estimated_monthly_income','non_overseas_development','manpower',
                   'num_of_provinces_in_states','num_of_provinces_in_territories'] 
                   
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
                ### Might not want to open save more than once.
                with open(latest_save, 'r') as save:
                    for line in range(2):
                        date = save.readline() # get date from 2nd line
                    # remove var name and dots (yyyy/mm/dd)
                    date = date[5:].replace('.','-').replace('.','-')[:-1] #:-1 to remove '\n'
                    
                    save_txt = save.read()

                    result_table = EU4_scrape_nations(save_txt, variables, tags)
                    
                    for tag in tags:
                        result_table[tag]['subjects']=EU4_scrape_nations(save_txt, ('raw_development'), get_subject_nations(save_txt,tag))
                
                for var in variables:
                    if SS.get_sheet(var):
                        if not SS.get_sheet_values(get_cellrange(var,len(tags)+1)):
                            #SS.add_sheet(var)
                            cellrange = get_cellrange(var, len(tags)+1, rowstart=1)
                            SS.batchUpdate([['Date', *tags]], cellrange)
                            row_insertion_index=2
                    else:
                        raise SheetNotFound('Sheet \'%s\' does not exist, please create it manually and rerun.')
                        
                    values = [result_table[tag][var] for tag in tags]
                    cellrange = get_cellrange(var, len(tags)+1, rowstart=row_insertion_index)
                    SS.batchUpdate([[date, *values]], cellrange)
                SS.batchExecute()
                row_insertion_index+=1
                previous_modified_time = latest_modified_time
            time.sleep(3)
        except errors.HttpError as err:
            print(err)
            time.sleep(15)
        
        
        
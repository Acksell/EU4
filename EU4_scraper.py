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

def get_cellrange(name, rowlength):
    '''Currently does not support rowlength>25'''
    cellrange=name+'!A1:'
    cellrange+=chr(65+rowlength)+'1'
    return cellrange
    
if __name__ == '__main__':
    import time
    import Google_sheets
    SPREADSHEET_ID = "12YdppOoZUNZxhXvcY_cRgfXEfRnR_izlBsF8Sin3rw4"
    
    #tags = input('Enter country tags separated by a space: ').upper().split()
    tags = ['FRA','ARA','CAS','TUR','BUR','ENG','HUN','POL','HAB']
    # non_overseas_development
    variables = ['base_tax','development','treasury','estimated_monthly_income','non_overseas_development']
    previous_modified_time = 0
    while True:
        print('listening')
        latest_save = latest_eu4_save()
        latest_modified_time = os.path.getmtime(latest_save)
        isfile=os.path.isfile(latest_save)
        filesize = os.path.getsize(latest_save)
        if latest_modified_time != previous_modified_time and isfile and filesize/1000>2000:
            print('NEW SAVE FOUND! It is at: ',latest_save)
            result_table = EU4_scrape(latest_save, variables, tags)
            SS = Google_sheets.Spreadsheet(SPREADSHEET_ID)
            for var in variables:
                cellrange = get_cellrange(var,len(tags)+1)
                if SS.get_sheet(var):
                    if not SS.get_sheet_values(cellrange):
                        SS.add_sheet(var)
                        SS.append_values([['Date', *tags]], cellrange)
                else:
                    raise Exception('Clean this up later, your sheet doesnt exist')
                values = [result_table[tag][var] for tag in tags]
                SS.append_values([[result_table['date'], *values]], cellrange)
            previous_modified_time = latest_modified_time
        time.sleep(4)
        
        
        
        
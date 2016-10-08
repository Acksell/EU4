# coding: iso-8859-15

# 2016-08-31
# Axel Engström, Sci14

# Scrape an EU4 save file for stats
# Put into csv and upload to google spreadsheets?

import os
import re

from settings import USERNAME

savegame_dir = "C:\\Users\\{}\\Documents\\Paradox Interactive\\Europa Universalis IV\\save games".format(USERNAME)
running_wd=os.getcwd()
os.chdir(savegame_dir)

def latest_eu4_save():
    files = filter(os.path.isfile, os.listdir(savegame_dir))
    files = [os.path.join(savegame_dir, f) for f in files] # add path to each file
    files.sort(key=lambda x: os.path.getmtime(x))
    return files[-1]
    
def EU4_scrape_nations(save_txt,variables, tags): # Should handle case of a tag not existing anymore.
    result_table={}
    for tag in tags: # make regex dependent on
        result_table[tag]={}
        for var in variables:
            for pattern in ('human','government_rank','has_set_government_name',):  # json structure is different for humans and AI
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
    
def get_subject_nations(save_txt, tag):
    for keypattern in ('human','has_set_government_name','government_rank'):  # json structure is different for different nations
        pattern = r'({0}={{\n\t\t{2}=.*?{1}={{(.*?)}})'.format(tag.upper(), 'subjects', keypattern)
        #returns subject nations embedded by whitespaces and quotes
        regex_result = re.findall(pattern, save_txt, flags=re.DOTALL)
        if regex_result:  
            if regex_result[0][0].count('raw_development') > 1:  # makes sure it doesnt overlap into other nations.
                continue
            else:
                #removes whitespaces
                regex_result=regex_result[0][1].split()
                #removes quotes and yields subject nation
                for nation in regex_result:
                    yield nation.split('"')[1]
                break

def get_bracket_info():
    """generalisation of get_subject_nations()"""
    pass

class SheetNotFound(Exception):pass
    
if __name__ == '__main__':
    import time
    from apiclient import errors
    from Google_sheets import Spreadsheet,get_cellrange
    
    from settings import tags,variables
    
    SPREADSHEET_ID = "12YdppOoZUNZxhXvcY_cRgfXEfRnR_izlBsF8Sin3rw4"
                   
    previous_modified_time = 0
    SS = Spreadsheet(SPREADSHEET_ID)
    #any variable works, not just 'raw_development'
    row_insertion_index = 1 + len(SS.get_sheet_values('raw_development'))
    while True:
        try:
            print('listening...')
            try:
                latest_save = latest_eu4_save()
                isfile=os.path.isfile(latest_save)
                if isfile:
                    latest_modified_time = os.path.getmtime(latest_save)
                    filesize = os.path.getsize(latest_save) # given in bytes
            except FileNotFoundError as err:
                print(err)
                f=open('ErrorLog.txt', 'a')
                f.write(repr(err))
                f.close()
            else:
                if latest_modified_time != previous_modified_time and time.time() - latest_modified_time < 30 and filesize/1000 > 2000 and isfile:
                    print("NEW SAVE FOUND! It is called '%s'" % latest_save.split('\\')[-1])
                    with open(latest_save, 'r') as save:
                        for line in range(2):
                            date = save.readline() # get date from 2nd line
                        # remove var name and dots (yyyy/mm/dd)
                        date = date[5:].replace('.', '-').replace('.', '-')[:-1] #:-1 to remove '\n'
                        
                        save_txt = save.read()
                        result_table = EU4_scrape_nations(save_txt, variables, tags)
                        
                    if int(date.split('-')[1]) in range(1,13,6): # if month is 1 or 7.
                        ### Construct pontogram sheetvalues and add them to the spreadsheet.
                        overlords_and_subjects_tags=[*tags]
                        for tag in tags:
                            subjects=list(get_subject_nations(save_txt, tag))
                            overlords_and_subjects_tags += subjects
                            result_table[tag]['subjects']=EU4_scrape_nations(save_txt, ['raw_development'], subjects)
                    
                        values=[]
                        total_development={}
                        for tag1 in tags:
                            column=[tag1]
                            total_development[tag1]=0
                            for tag2 in overlords_and_subjects_tags:
                                if tag2 == tag1:
                                    dev=int(result_table[tag1]['raw_development'][:-4]) #[:-4] gets rid of comma & trailing 0's
                                    column.append(dev)
                                    total_development[tag1]+=dev
                                elif tag2 in result_table[tag1]['subjects']:
                                    dev=int(result_table[tag1]['subjects'][tag2]['raw_development'][:-4])
                                    column.append(dev)
                                    total_development[tag1]+=dev
                                else:
                                    column.append(0)
                            values.append(column)
                        values=[[date,*overlords_and_subjects_tags],*sorted(values, key=lambda x: total_development[x[0]], reverse=True)]

                        name='Pontogram'
                        if not SS.get_sheet(name):
                            SS.add_sheet(name)
                        SS.clear_values(name)
                        SS.batchUpdate(values, get_cellrange(name, len(tags)+1,
                                         columnlength=len(overlords_and_subjects_tags)+1), majorDimension='COLUMNS')
                            
                    ### Add values to spreadsheet
                    for var in variables:
                        # if no sheet was found, add sheet
                        if not SS.get_sheet(var): 
                            SS.add_sheet(var)  
                        if not SS.get_sheet_values(get_cellrange(var, len(tags)+1)):
                            cellrange = get_cellrange(var, len(tags)+1)
                            SS.batchUpdate([['Date', *tags]], cellrange)
                            row_insertion_index = 2
                        values = [result_table[tag][var] for tag in tags]
                        cellrange = get_cellrange(var, len(tags)+1, rowstart=row_insertion_index)
                        SS.batchUpdate([[date, *values]], cellrange, majorDimension='ROWS')
                    SS.batchExecute()
                    row_insertion_index += 1
                    previous_modified_time = latest_modified_time
                time.sleep(3)
        except errors.HttpError as err:
            print(err)
            f=open('ErrorLog.txt', 'a')
            f.write(repr(err))
            f.close()
            time.sleep(15)
        
        
        
# -*- coding: UTF-8 -*-
# 2016-08-31
# Axel Engström, Sci14

# Scrape EU4 save files for stats and upload to a Google Spreadsheet.

import os
import re
from random import choice
from string import ascii_lowercase

from settings import USERNAME

savegame_dir = "C:\\Users\\{}\\Documents\\Paradox Interactive\\Europa Universalis IV\\save games".format(USERNAME)
running_wd=os.getcwd()
os.chdir(savegame_dir)

def log(filename, mode, *text):
    os.chdir(running_wd)
    with open(filename, mode) as file:
        for output in text:
            file.write(repr(output))
    os.chdir(savegame_dir)

def latest_eu4_save():
    files = filter(os.path.isfile, os.listdir(savegame_dir))
    files = [os.path.join(savegame_dir, f) for f in files] # add path to each file
    files.sort(key=lambda x: os.path.getmtime(x))
    return files[-1]

def EU4_scrape_nations(save_txt,variables, tags): # Should handle case of a tag not existing anymore.
    result_table = {}
    for tag in tags: # make regex dependent on
        result_table[tag] = {}
        for var in variables:
            # FIRST_VARIABLES == get_all_first_variables(), should be found in global scope
            for first_variable in FIRST_VARIABLES:
                # regex used is therefore different for different nations
                regex = r'{0}={{\n\t\t{2}=.*?{1}=(.*?)\n'.format(tag.upper(), var, first_variable)
                value = re.findall(regex, save_txt, flags=re.DOTALL)
                if value: break
            try:
                result_table[tag][var] = value[0].replace('.',',')  #[0] because regex returns a list
            except IndexError as err:
                log('savefile.log','w', save_txt, regex, 'tag:{0} var:{1} value: {2}'.format(tag,var,value))
                print(regex)
                print(tag,var,value)
                raise err
    return result_table

# TODO: just get_bracket_content() of 'subjects' index, incorporate into EU4_scrape_nations
def get_subject_nations(save_txt, tag):
    # FIRST_VARIABLES === get_all_first_variables(), should be found in global scope
    for variable in FIRST_VARIABLES:
        # regex used is therefore different for different nations
        regex = r'({0}={{\n\t\t{2}=.*?{1}={{(.*?)}})'.format(tag.upper(), 'subjects', variable)
        #returns subject nations embedded by whitespaces and quotes
        regex_result = re.findall(regex, save_txt, flags=re.DOTALL)
        if regex_result:
            if regex_result[0][0].count('raw_development') > 1:  # makes sure it doesnt overlap into other nations.
                continue
            else:
                # Extracts the tags from a string of the form "\n\t\t\tTAG1 TAG2 TAG3\n\t\t"
                regex_result = regex_result[0][1].split()
                return regex_result


def random_string(length):
    return ''.join(choice(ascii_lowercase) for x in range(length))

def replace_all(text, char_map):
    '''Returns text with all substrings a replaced with string b'''
    for a,b in char_map.items():
        while a in text:
            text = text.replace(a,b)
    return text

def split_more(text, *split_chars):
    '''split() with more than 1 delimiter.'''
    unique_string = random_string(10)
    while unique_string in text:
        unique_string = random_string(10)
    for char in split_chars:
        text = replace_all(text, {char:unique_string})
    return text.split(unique_string)

def get_bracket_content(text, fetch_amount=1, indent_level=0):
    bracket_count = 0
    break_points = [0]
    fetches = 0
    for i,char in enumerate(text):
        if char == '{':
            if bracket_count == indent_level:
                break_points.append(i)
            bracket_count+=1
        elif char == '}':
            if bracket_count == indent_level+1:
                break_points.append(i)
                fetches += 1
                if fetches >= fetch_amount:
                    break
            bracket_count -= 1
        elif bracket_count == 0 and fetches:
            break
    return [text[break_points[i]:break_points[i+1]+1] for i in range(2*fetches)]

def data_from_startpoint(text, matchstring):
    '''returns a sliced string starting from the first occurance of matchstring'''
    return text[text.index(matchstring):] if matchstring in text else ''

def get_all_first_variables(save_txt):
    '''
    Gets the first variable which is defined in a country's header. This variable name
    is needed for the regular expression scraping the country header to be unambiguous.
    '''
    unique_first_variables = []
    country_content = data_from_startpoint(save_txt, '\ncountries={')
    # float('inf') will fetch all.
    res = get_bracket_content(country_content, fetch_amount=float('inf'), indent_level=1)
    for i in range(1, len(res), 2):
        first_variable = [item for item in split_more(res[i], '\n', '\t', '=') if item][1]
        if first_variable not in unique_first_variables:
            unique_first_variables.append(first_variable)
    return unique_first_variables

def get_players_countries(save_txt):
    '''Returns a dictionary with playernames as keys and their country tag as values.'''
    matchstring = 'players_countries={'
    pc = get_bracket_content(data_from_startpoint(save_txt, matchstring),indent_level=0)
    if pc:
        pc = [i for i in split_more(pc[1], '\n', '\t', '{', '}', '"') if i]
        pc = dict([(pc[i], pc[i+1]) for i in range(0,len(pc),2)])
    else:
        pc={}
    return pc


if __name__ == '__main__':
    import time
    from apiclient import errors
    from Google_sheets import Spreadsheet, get_cellrange

    from settings import SPREADSHEET_ID, tags, variables

    previous_modified_time = 0
    FIRST_VARIABLES = []

    # Initialize the spreadsheet
    initialized = False
    print('Initializing Spreadsheet...')
    while not initialized:
        try:
            SS = Spreadsheet(SPREADSHEET_ID, credentials_dir=running_wd)
        except errors.HttpError as err:
            print(err)
            print('Currently unable to reach the server, will try again in 15 seconds.')
            time.sleep(15)
        else:
            initialized = True
    print('Spreadsheet initialized.')
    #any variable works, not just 'raw_development', it should be the same for every sheet except pontogram.
    row_insertion_index = 1 + len(SS.get_sheet_values('raw_development'))
    players_countries={}

    dot_counter=0
    while True:
        print('listening' + '.'*dot_counter + ' '*(3-dot_counter), end='\r')
        if dot_counter == 3:
            dot_counter=0
        else:
            dot_counter+=1
        try:
            try:
                latest_save = latest_eu4_save()
                isfile=os.path.isfile(latest_save)
                if isfile:
                    latest_modified_time = os.path.getmtime(latest_save)
                    filesize = os.path.getsize(latest_save) # given in bytes
            except FileNotFoundError as err:
                print(err)
                log('errors.log', 'a', err)
            else:
                if latest_modified_time != previous_modified_time and time.time() - latest_modified_time < 30 and filesize/1000 > 2000 and isfile:
                    print("NEW SAVE FOUND! It is called '%s'" % latest_save.split('\\')[-1])
                    with open(latest_save, 'r') as save:
                        for line in range(2):
                            date = save.readline() # get date from 2nd line
                        # remove var name and dots (yyyy/mm/dd)
                        date = date[5:].replace('.', '-').replace('.', '-')[:-1] #:-1 to remove '\n'

                        save_txt = save.read()
                    
                    # Check if a player formed a new nation
                    # BUG: If a player switches steam name during the game, the name stored
                    # will not match the one that is found. Players are therefore advised not to do so.
                    new_players_countries = get_players_countries(save_txt)
                    if len(new_players_countries.items()) > 1:
                        if new_players_countries != players_countries:
                            for player, oldtag in players_countries.items():
                                if player in new_players_countries:
                                    if new_players_countries[player] != oldtag:
                                        print('A new player nation formed!')
                                        tags[tags.index(oldtag)] = new_players_countries[player]
                                        with open('settings.py','a') as f:
                                            f.write('\ntags = %s' % repr(tags))
                                        for var in variables:
                                            SS.batchUpdate([['Date',*tags]], get_cellrange(var, len(tags)+1))
                                        SS.batchExecute()
                            players_countries = new_players_countries

                    if not FIRST_VARIABLES:
                        print('Adjusting for latest patch...')
                        FIRST_VARIABLES = get_all_first_variables(save_txt)
                    print('Scraping tracked tags...')
                    result_table = EU4_scrape_nations(save_txt, variables, tags)

                    if int(date.split('-')[1]) in range(1,13,6): # if month is 1 or 7.
                        ### Construct pontogram sheetvalues and add them to the spreadsheet.
                        overlords_and_subjects_tags=[*tags]
                        print('Scraping subjects...')
                        for tag in tags:
                            subjects = list(get_subject_nations(save_txt, tag))
                            overlords_and_subjects_tags += subjects
                            result_table[tag]['subjects'] = EU4_scrape_nations(save_txt, ['raw_development'], subjects)

                        values=[]
                        total_development={}
                        print('Making Pontogram')
                        referenced_as_overlord=[]
                        referenced_as_subject=[]
                        for tag1 in tags:
                            column = [tag1]
                            total_development[tag1] = 0
                            for tag2 in overlords_and_subjects_tags:
                                if tag2 == tag1 and tag2 not in referenced_as_overlord:
                                    dev = int(result_table[tag1]['raw_development'][:-4]) #[:-4] gets rid of comma & trailing 0's
                                    column.append(dev)
                                    total_development[tag1] += dev
                                    referenced_as_overlord.append(tag2)
                                elif tag2 in result_table[tag1]['subjects'] and tag2 not in referenced_as_subject:
                                    dev = int(result_table[tag1]['subjects'][tag2]['raw_development'][:-4])
                                    column.append(dev)
                                    total_development[tag1] += dev
                                    referenced_as_subject.append(tag2)
                                else:
                                    column.append('')
                            values.append(column)
                        values=[[date, *overlords_and_subjects_tags], 
                                *sorted(values, key=lambda x: total_development[x[0]], reverse=True)]

                        name='Pontogram'
                        if not SS.get_sheet(name):
                            print('Adding sheet %s...' % name)
                            SS.add_sheet(name)
                        SS.clear_values(name)
                        SS.batchUpdate(values, get_cellrange(name, len(tags)+1,
                                         columnlength=len(overlords_and_subjects_tags)+1), majorDimension='COLUMNS')
                    print('Uploading values...')
                    ### Add values to spreadsheet
                    for var in variables:
                        if not SS.get_sheet(var):
                            print('Adding sheet %s...' % var)
                            SS.add_sheet(var)
                        if not SS.get_sheet_values(get_cellrange(var, len(tags)+1)):
                            cellrange = get_cellrange(var, len(tags)+1)
                            SS.batchUpdate([['Date', *tags]], cellrange)
                            row_insertion_index = 2
                        values = [result_table[tag][var] for tag in tags]
                        if any(filter(lambda val: '-' in str(val), values)):
                            log('savefile.log','w', repr(values), '\n', repr(result_table), 
                                '\n--------Save file below-------\n', save_txt)
                        cellrange = get_cellrange(var, len(tags)+1, rowstart=row_insertion_index)
                        SS.batchUpdate([[date, *values]], cellrange, majorDimension='ROWS')
                    SS.batchExecute()
                    row_insertion_index += 1
                    previous_modified_time = latest_modified_time
                    dot_counter=0
                time.sleep(1)
        except errors.HttpError as err:
            print(err)
            log('errors.log', 'a', err)
            time.sleep(15)

# coding: iso-8859-15

# 2016-08-31
# Axel Engström, Sci14

# Scrape an EU4 save file for stats
# Put into csv and upload to google spreadsheets?

import os
import re

USERNAME='username'

savegamedir = "C:\\Users\\{}\\Documents\\Paradox Interactive\\Europa Universalis IV\\save games".format(USERNAME)
os.chdir(savegame_dir)

def latest_eu4_save():
    files = filter(os.path.isfile, os.listdir(savegame_dir))
    files = [os.path.join(savegame_dir, f) for f in files] # add path to each file
    files.sort(key=lambda x: os.path.getmtime(x))
    return files[-1]
    
#tags = input('Enter country tags separated by a space: ').upper().split()
tags = ['pol','teu','liv']
variables = ['base_tax','development','treasury']

def EU4_scrape(variables, tags): 
    #NOTE reformat to default to catching only humans if tags not specified
    result_table = {tag:{} for tag in tags}
    with open(latest_eu4_save, 'r') as save:
        for line in range(2):
            date = save.readline() # get date from 2nd line
        date = date.replace('date=', '')) # remove name, get value
        save_txt = save.read()
        for tag in tags: # make regex dependent on 
            for var in variables:
                for pattern in ('human','government_rank'):  # json structure is different for humans and AI
                    pattern = r'{0}={{\n\t\t{2}=.*?{1}=(.*?)\n'.format(tag.upper(), var, pattern)
                    value = re.findall(pattern, save_txt, flags=re.DOTALL)
                    if value: break
                result_table[tag][var] = value[0]  #[0] because regex returns a list
        return result_table

import os
import sys
import time
import json
import traceback

import helpers

from SaveFile import SaveFile
from pontogram import get_pontogram

class Outputter:
    def __init__(self):
        self.dot_counter=0
    
    def nextdot(self, msg):
        print(msg + '.'*self.dot_counter + ' '*(3-self.dot_counter), end='\r')
        if self.dot_counter > 2:
            self.dot_counter=0
        else:
            self.dot_counter+=1

    def console(self, *msg):
        print(*msg)

class ScraperRunner:
    SAVEGAME_DIR = f"C:\\Users\\{os.getlogin()}\\Documents\\Paradox Interactive\\Europa Universalis IV\\save games"
    RUNNING_DIR = os.getcwd()

    def __init__(self, spreadsheet):
        self.SS = spreadsheet
        self.row_insertion_index = 1 + len(self.SS.get_sheet_values("raw_development"))
        self.player_countries = {}
        self.output = Outputter()
        
        self.previous_modified_time = 0
        self.latest_modified_time = None
        self.latest_save = None
        self.current_dir = os.getcwd()

        self.players_countries={} # defined by savefile
        self.load_settings()

    def load_settings(self):
        with open("settings.json",'r') as settingsfile:
            self.settings = json.load(settingsfile)
        self.tags = self.settings["tags"]

    def switch_directory(self, directory):
        if self.current_dir != directory:    
            os.chdir(directory)
            self.current_dir = self.SAVEGAME_DIR

    def add_sheets(self):
        for var in self.settings["variables"]:
            # Add sheets if not existing
            if not self.SS.get_sheet(var):
                self.output.console('Adding sheet %s...' % var)
                self.SS.add_sheet(var)
        ponto_sheet_name="Pontogram"
        if not self.SS.get_sheet(ponto_sheet_name):
            print('Adding sheet %s...' % ponto_sheet_name)
            self.SS.add_sheet(ponto_sheet_name)


    def run(self):
        """
        Main loop. Looks for save games, parses them and
        uploads values to Google Sheets.
        """
        self.switch_directory(self.SAVEGAME_DIR)
        self.add_sheets()
        while True:
            self.output.nextdot('listening')
            new_save = self.get_new_save()
            if new_save is not None:
                new_save.read_file()  # read file for some initialisation
                self.output.console("NEW SAVE FOUND! It is called '%s'" % self.latest_save.name)
                # checks if player nation formed and updates tags
                self.update_tags()

                if not self.latest_save.first_variables:
                    self.output.console('Adjusting for latest patch...')
                    self.latest_save.set_first_variables()

                self.output.console('Scraping tracked tags...')
                self.latest_save.EU4_scrape_nations(
                    self.settings["variables"],
                    self.tags)
                
                ### Construct pontogram sheetvalues and add them to the spreadsheet.
                if int(self.latest_save.month) in range(1,13,6): # if month is 1 or 7.
                    self.output.console('Scraping subjects...')
                    self.latest_save.scrape_tags_subjects(self.tags)
                    overlords_and_subjects_tags = self.latest_save.overlords_and_subjects_tags # set by scrape_tags_subjects
                    self.output.console('Making Pontogram')
                    values = self.latest_save.get_pontogram(self.tags)
                    # update pontogram
                    print(self.latest_save.result_table)
                    self.SS.clear_values("Pontogram")
                    self.SS.batchUpdate(values, helpers.get_cellrange("Pontogram",
                        len(self.tags)+1,
                        columnlength=len(overlords_and_subjects_tags)+1),
                        majorDimension='COLUMNS')
                self.upload_values() # uploads all variables for each tag.
                # prevent opening of same savefile, only register new ones.
                self.row_insertion_index += 1
                self.previous_modified_time = self.latest_modified_time
            time.sleep(1)

    def upload_values(self):
        self.output.console('Uploading values...')
        ### Add values to spreadsheet
        if self.row_insertion_index==1:
            for var in self.settings["variables"]:
                # initial update
                cellrange = helpers.get_cellrange(var, len(self.tags)+1)
                self.SS.batchUpdate([['Date', *self.tags]], cellrange)
            self.row_insertion_index=2
        for var in self.settings["variables"]:
            values = [self.latest_save.result_table[tag][var] for tag in self.tags]
            cellrange = helpers.get_cellrange(var, len(self.tags)+1, rowstart=self.row_insertion_index)
            self.SS.batchUpdate([[self.latest_save.date, *values]], cellrange,
                majorDimension='ROWS')
        self.SS.batchExecute()

    def get_new_save(self):
        """
        Returns a SaveFile object representing a new save if there is a new save. 
        None otherwise
        """
        try:
            self.latest_save = self.latest_eu4_save()
        # in case of race condition from modifying/deleting file while running
        except FileNotFoundError as err:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            traceback.print_exc()
            self.log('errors.log', 'a', traceback.format_exc())
        else:
            if self.latest_save:
                self.latest_modified_time = self.latest_save.modified
                is_new_save = time.time() - self.latest_modified_time < 30 # less than 30s old
                not_seen_before = self.latest_modified_time != self.previous_modified_time
                correct_size = self.latest_save.filesize/1000 > 2000 # more than 2 MB
                if self.latest_save.isfile and not_seen_before and is_new_save and correct_size:
                    return self.latest_save

    def latest_eu4_save(self):
        """Returns the latest eu4 savefile as a SaveFile object. None if no save games present"""
        self.switch_directory(self.SAVEGAME_DIR) # make sure to be in correct state
        files = filter(os.path.isfile, os.listdir(self.SAVEGAME_DIR)) # filter for only files
        files = [os.path.join(self.SAVEGAME_DIR, f) for f in files] # add path to each file
        files.sort(key=lambda x: os.path.getmtime(x)) # sort files by latest
        if files:
            return SaveFile(files[-1], read_file_on_init=False) # return latest savefile

    def get_new_tags(self):
        """Returns"""
        new_tags=self.tags
        new_players_countries = self.latest_save.get_players_countries()
        if len(new_players_countries.items()) > 1:
            if new_players_countries != self.players_countries:
                for player, oldtag in self.players_countries.items():
                    if player in new_players_countries:
                        if new_players_countries[player] != oldtag:
                            self.output.console('A new player nation formed!')
                            new_tags[new_tags.index(oldtag)] = new_players_countries[player]
                self.players_countries = new_players_countries
        return new_tags

    def update_tags(self):
        tags = self.get_new_tags()
        with open(os.path.join(self.RUNNING_DIR, 'settings.json'), 'w') as settingsfile:
            self.settings["tags"] = tags
            json.dump(self.settings, settingsfile, indent=4)
        for var in self.settings["variables"]:
            self.SS.batchUpdate([['Date',*tags]], helpers.get_cellrange(var, len(tags)+1))
        self.SS.batchExecute()
        self.tags = tags # update state after running all above to make sure in sync.


    def log(self, filename, mode, *text):        
        self.switch_directory(self.RUNNING_DIR)
        with open(filename, mode) as file:
            for output in text:
                file.write(output)
        self.switch_directory(self.SAVEGAME_DIR)


if __name__ == "__main__":
    from Google_sheets import Spreadsheet
    
    ss = Spreadsheet("1lRUNpXrwAOpyp-IGDUtPK9dP3uR8diLRljSgxCO72uE", retry_initialisation=True)

    scraper = ScraperRunner(ss)
    scraper.run()
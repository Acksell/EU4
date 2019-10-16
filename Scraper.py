import os
import sys
import time
import json
import traceback

import helpers

from SaveFile import SaveFile


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

    def run(self):
        """
        Main loop. Looks for save games, parses them and
        uploads values to Google Sheets.
        """
        self.switch_directory(self.SAVEGAME_DIR)
        for var in self.settings["variables"]:
            # Add sheets if not existing
            if not self.SS.get_sheet(var):
                self.output.console('Adding sheet %s...' % var)
                self.SS.add_sheet(var)
        while True:
            self.output.nextdot('listening')
            new_save = self.get_new_save()
            if new_save is not None:
                new_save.read_file()  # read file for some initialisation
                self.output.console("NEW SAVE FOUND! It is called '%s'" % self.latest_save.name)
                # checks if player nation formed and updates tags
                self.update_tags()

            # prevent opening of same savefile, only register new ones.
            self.previous_modified_time = self.latest_modified_time
            time.sleep(1)

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
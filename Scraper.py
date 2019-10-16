import time
import os
import sys
import traceback

import helpers

class Outputter:
    def __init__(self):
        self.dot_counter=0
    
    def nextdot(self, msg):
        print(msg + '.'*self.dot_counter + ' '*(3-self.dot_counter), end='\r')
        if self.dot_counter > 2:
            self.dot_counter=0
        else:
            self.dot_counter+=1


class SaveFile:
    def __init__(self, filepath, read_file_on_init=True):
        self.filepath = filepath
        self.name = filepath.split('\\')[-1]
        self.isfile = os.path.isfile(filepath)
        self.modified = os.path.getmtime(filepath)
        self.filesize = os.path.getsize(filepath) # given in bytes

        self.date=None
        self.save_txt=None
        if read_file_on_init:
            self.read_file() # sets self.date and self.save_text

    def read_file(self):
        """Opens the self.filepath and sets self.date and self.save_text"""
        with open(self.filepath, 'r') as save:
            for line in range(2):
                date = save.readline() # get date from 2nd line
            # remove var name and dots (yyyy/mm/dd)
            self.date = date[5:].replace('.', '-').replace('.', '-')[:-1] #:-1 to remove '\n'
            self.save_txt = save.read()

    def __str__(self):
        return self.name



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
        while True:
            self.output.nextdot('listening')
            new_save = self.get_new_save()
            if new_save is not None:
                new_save.read_file()  # read file for some initialisation
                print("NEW SAVE FOUND! It is called '%s'" % self.latest_save.name)
                print("savefile date",self.latest_save.date)
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
import time
import os

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
    savegame_dir = f"C:\\Users\\{os.getlogin()}\\Documents\\Paradox Interactive\\Europa Universalis IV\\save games"

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
        with open(os.path.join(self.savegame_dir, self.filepath), 'r') as save:
            for line in range(2):
                date = save.readline() # get date from 2nd line
            # remove var name and dots (yyyy/mm/dd)
            self.date = date[5:].replace('.', '-').replace('.', '-')[:-1] #:-1 to remove '\n'
            self.save_txt = save.read()

    def __str__(self):
        return self.name

    @classmethod
    def latest_eu4_save(cls):
        current_dir = os.getcwd() # save current dir to change back to later
        os.chdir(cls.savegame_dir) # change to savegame dir
        files = filter(os.path.isfile, os.listdir(cls.savegame_dir)) # filter for only files
        files = [os.path.join(cls.savegame_dir, f) for f in files] # add path to each file
        files.sort(key=lambda x: os.path.getmtime(x)) # sort files by latest
        os.chdir(current_dir) # change back to working dir
        return cls(files[-1], read_file_on_init=False) # return latest savefile


class ScraperRunner:
    def __init__(self, spreadsheet):
        self.SS = spreadsheet
        self.row_insertion_index = 1 + len(self.SS.get_sheet_values("raw_development"))
        self.player_countries = {}
        self.output = Outputter()

        self.running_dir = os.getcwd()
        
        self.previous_modified_time = 0
        self.latest_modified_time = None
        self.latest_save = None
        
    def run(self):
        while True:
            self.output.nextdot('listening')
            new_save = self.get_latest_save()
            if new_save is not None:
                new_save.read_file()  # read file for some initialisation
                print("NEW SAVE FOUND! It is called '%s'" % self.latest_save.name)
                print("savefile date",self.latest_save.date)
            # prevent opening of same savefile, only register new ones.
            self.previous_modified_time = self.latest_modified_time
            time.sleep(1)

    def get_latest_save(self):
        try:
            self.latest_save = SaveFile.latest_eu4_save()
            self.latest_modified_time = self.latest_save.modified
        # in case of race condition from modifying/deleting file while running
        except FileNotFoundError as err:
            print(err)
            helpers.log('errors.log', 'a', err)
        else:
            is_new_save = time.time() - self.latest_modified_time < 30 # less than 30s old
            not_seen_before = self.latest_modified_time != self.previous_modified_time
            correct_size = self.latest_save.filesize/1000 > 2000 # more than 2 MB
            if self.latest_save.isfile and not_seen_before and is_new_save and correct_size:
                return self.latest_save


if __name__ == "__main__":
    from Google_sheets import Spreadsheet
    
    ss = Spreadsheet("1lRUNpXrwAOpyp-IGDUtPK9dP3uR8diLRljSgxCO72uE", retry_initialisation=True)

    scraper = ScraperRunner(ss)
    scraper.run()
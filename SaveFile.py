import os
import re



import helpers


class SaveFile:
    def __init__(self, filepath, read_file_on_init=True):
        self.filepath = filepath
        self.name = filepath.split('\\')[-1]
        self.isfile = os.path.isfile(filepath)
        self.modified = os.path.getmtime(filepath)
        self.filesize = os.path.getsize(filepath) # given in bytes

        self.date=None
        self.save_txt=None
        self.first_variables=None
        if read_file_on_init:
            self.read_file() # sets self.date and self.save_text
        self.result_table={}

    def read_file(self):
        """Opens the self.filepath and sets self.date and self.save_text"""
        with open(self.filepath, 'r', encoding="cp437") as save:
            for line in range(2):
                date = save.readline() # get date from 2nd line
            # remove var name and dots (yyyy/mm/dd)
            self.date = date[5:].replace('.', '-').replace('.', '-')[:-1] #:-1 to remove '\n'
            self.year, self.month, self.day = self.date.split('-')
            self.save_txt = save.read()

    def get_players_countries(self):
        '''Returns a dictionary with playernames as keys and their country tag as values.'''
        matchstring = 'players_countries={'
        pc = helpers.get_bracket_content(
            helpers.data_from_startpoint(self.save_txt, matchstring),
            indent_level=0
        )
        if pc:
            pc = [i for i in helpers.split_more(pc[1], '\n', '\t', '{', '}', '"') if i]
            pc = dict([(pc[i], pc[i+1]) for i in range(0,len(pc),2)])
        else:
            pc={}
        return pc

    def get_subject_nations(self, tag):
        # FIRST_VARIABLES === get_all_first_variables(), should be found in global scope
        for variable in self.first_variables:
            # regex used is therefore different for different nations
            regex = r'({0}={{\n\t\t{2}=.*?{1}={{(.*?)}})'.format(tag.upper(), 'subjects', variable)
            #returns subject nations embedded by whitespaces and quotes
            regex_result = re.findall(regex, self.save_txt, flags=re.DOTALL)
            if regex_result:
                if regex_result[0][0].count('raw_development') > 1:  # makes sure it doesnt overlap into other nations.
                    continue
                else:
                    # Extracts the tags from a string of the form "\n\t\t\tTAG1 TAG2 TAG3\n\t\t"
                    regex_result = regex_result[0][1].split()
                    return regex_result
        return []

    def set_first_variables(self):
        '''
        Gets the first variable which is defined in a country's header. This variable name
        is needed for the regular expression scraping the country header to be unambiguous.
        '''
        unique_first_variables = []
        country_content = helpers.data_from_startpoint(self.save_txt, '\ncountries={')
        # float('inf') will fetch all.
        res = helpers.get_bracket_content(
            country_content,
            fetch_amount=float('inf'), # wtf, this function should be refactored.
            indent_level=1
        )
        for i in range(1, len(res), 2):
            first_variable = [item for item in helpers.split_more(res[i], '\n', '\t', '=') if item][1]
            if first_variable not in unique_first_variables:
                unique_first_variables.append(first_variable)
        self.first_variables = unique_first_variables
        return unique_first_variables

    def scrape_tags_subjects(self, tags):
        self.overlords_and_subjects_tags=[*tags]
        for tag in tags:
            subjects = list(self.get_subject_nations(tag))
            self.overlords_and_subjects_tags += subjects
            # add subjects to country tag.
            self.result_table[tag]['subjects'] = self.EU4_scrape_nations(['raw_development'], subjects)
        return self.result_table

    def EU4_scrape_nations(self, variables, tags): # Should handle case of a tag not existing anymore.
        result_table = {}
        for tag in tags: # make regex dependent on
            result_table[tag] = {}
            for var in variables:
                # FIRST_VARIABLES == get_all_first_variables(), should be found in global scope
                for first_variable in self.first_variables:
                    # regex used is therefore different for different nations
                    regex = r'{0}={{\n\t\t{2}=.*?{1}=(.*?)\n'.format(tag.upper(), var, first_variable)
                    value = re.findall(regex, self.save_txt, flags=re.DOTALL)
                    if value: break
                try:
                    result_table[tag][var] = value[0].replace('.',',')  #[0] because regex returns a list
                except IndexError as err:
                    log('savefile.log','w', self.save_txt, regex, 'tag:{0} var:{1} value: {2}'.format(tag,var,value))
                    print(regex)
                    print(tag,var,value)
                    raise err
            if self.result_table.get(tag):
                self.result_table[tag].update(result_table)
            else:
                self.result_table[tag]=result_table[tag]
        return result_table

    def get_pontogram(self, tags):
        # Magic works in mysterious ways
        values=[]
        total_development={}
        referenced_as_overlord=[]
        referenced_as_subject=[]
        for tag1 in tags:
            column = [tag1]
            total_development[tag1] = 0
            for tag2 in self.overlords_and_subjects_tags:
                if tag2 == tag1 and tag2 not in referenced_as_overlord:
                    dev = int(self.result_table[tag1]['raw_development'][:-4]) #[:-4] gets rid of comma & trailing 0's
                    column.append(dev)
                    total_development[tag1] += dev
                    referenced_as_overlord.append(tag2)
                elif tag2 in self.result_table[tag1]['subjects'] and tag2 not in referenced_as_subject:
                    dev = int(self.result_table[tag1]['subjects'][tag2]['raw_development'][:-4])
                    column.append(dev)
                    total_development[tag1] += dev
                    referenced_as_subject.append(tag2)
                else:
                    column.append('')
            values.append(column)
        values=[[self.date, *self.overlords_and_subjects_tags], 
                *sorted(values, key=lambda x: total_development[x[0]], reverse=True)]
        return values

    def __str__(self):
        return self.name
def latest_eu4_save(savegame_dir):
    files = filter(os.path.isfile, os.listdir(savegame_dir))
    files = [os.path.join(savegame_dir, f) for f in files] # add path to each file
    files.sort(key=lambda x: os.path.getmtime(x))
    return files[-1]

def log(filename, mode, *text):
    os.chdir(running_wd)
    with open(filename, mode) as file:
        for output in text:
            file.write(repr(output))
    os.chdir(savegame_dir)

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
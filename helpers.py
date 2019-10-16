import random
from string import ascii_lowercase

def get_cellrange(name, rowlength, rowstart=1, columnlength=1, columnstart=1):
    '''Currently does not support rowlength>25'''
    cellrange = name+'!A{}:'.format(rowstart)
    cellrange += chr(65+rowlength) + str(rowstart+columnlength-1)
    return cellrange

def random_string(length):
    return ''.join(random.choice(ascii_lowercase) for x in range(length))

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

def data_from_startpoint(text, matchstring):
    '''returns a sliced string starting from the first occurance of matchstring'''
    return text[text.index(matchstring):] if matchstring in text else ''
    
# TODO: Redo this fucking function altogether. It's a mess.
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


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
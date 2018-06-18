import re

def clean_chars(data):
    ''' remove irregular characters '''
    data = data.replace('\r', '')

    return data

def _replace_ab(data, a, b, sub):
    ''' remove stuff between a and b and replace with sub '''
    start = data.find(a)
    if start >= 0:
        stop = data.find(b, start)
        if stop >= 0:
            data = data[:start] + sub + data[stop + len(b):]
            return True, data

    return False, data

def _remove_ab(data, a, b):
    ''' remove stuff between a and b '''
    return _replace_ab(data, a, b, '')

def remove_comments(data):
    ''' remove comments '''
    found = True
    while found:
        found, data = _remove_ab(data, '/*', '*/')

    found = True
    data += '\n'
    while found:
        found, data = _remove_ab(data, '//', '\n')

    found = True
    data += '\n'
    while found:
        found, data = _remove_ab(data, '#', '\n')

    return data

def clean_format(data):
    ''' clean up format with no content change '''
    # add space to beginning and end
    data = ' ' + data + ' '
    # add spacing for key separators
    for c in [';', '(', ')', '{', '}', '[', ']', ',', '*']:
        data = data.replace(c, ' ' + c + ' ')
    # replace tab and new line with space
    data = data.replace('\t', ' ')
    data = data.replace('\n', ' ')
    # deal with colon
    data = data.replace(':', ' : ')
    # since : has been padded in last line, we expect some space here
    data = re.sub(' *:  : *', '::', data)
    # <> shouldn't have spaces inside them
    data = re.sub('< *', '<', data)
    data = re.sub(' *>', '>', data)
    # reduce all padding to 1 space only
    data = re.sub('   *', ' ', data)
    # * should follow type name
    data = data.replace(' *', '*')

    return data

def replace_keywords(data):
    ''' replace keywords to make parsing easier '''

def _derive_brackets(data):
    ''' find a list of {} in stream '''
    l = []
    for i, c in enumerate(data):
        if c == '{':
            l.append((i, 1))
        elif c == '}':
            l.append((i, -1))

    return l

def _integrate_paths(der, data_length):
    ''' integrate hierarchical paths for each section from the derivative '''
    # 0 is the global level
    level = 0
    stack = []
    paths = []

    # add a ender to trick the loop into picking up the last piece
    der.append([data_length-1, -1])
    for i, e in der:
        # add to stack
        if len(stack) == level:
            # creating a child also increments the parent
            if level > 0:
                stack[level-1] += 1
            stack.append(0)
        else:
            stack[level] += 1
            # clear stacks beyond this one, since we incremented
            stack = stack[:level+1]

        # only keep the relevent stacks as path
        paths.append((i, stack[:level+1]))
        level += e

    return paths

def _assign_path(l, data, path):
    ''' assign data to the nested list defined by path '''
    curr = l
    # create empty lists to prepare for the last item
    for path_level, path_i in enumerate(path[:-1]):
        while len(curr) <= path_i:
            curr.append([])
        curr = curr[path_i]

    # fill the path with data for last iteration
    last_i = path[-1]
    while len(curr) <= last_i:
        curr.append([])
    curr[last_i] = data

def _fulfill_paths(data, paths):
    ''' fetch sections of data based on paths '''
    filled = []
    last_i = -1
    for i, path in paths:
        # create the structure to hold the data
        _assign_path(filled, data[last_i+1:i], path)
        last_i = i

    return filled

def collect_scope(data):
    ''' turn stream data into nested list of scopes '''
    # find the 'derivative' of {}
    der = _derive_brackets(data)

    # find paths by integrating the derivative
    paths = _integrate_paths(der, len(data))

    # fetch data based on paths
    filled = _fulfill_paths(data, paths)

    return filled

def _clean_generic_string(data):
    ''' clean generic string (not in a class) to remove noise '''
    # anything before the last ; is noise
    start = data.rfind(';')
    if start > 0:
        data = data[start+1:]
    # we only care about class
    if 'class' in data:
        # we don't care about inherentence
        data = re.sub('class', '', data)
        data = re.sub(':.*$', '', data)
        data = data.strip()
    else:
        data = ''

    return data

def remove_noise(scopes):
    ''' find and remove stuff we don't care about '''
    for i in range(len(scopes)):
        if isinstance(scopes[i], basestring):
            # we process the strings
            scopes[i] = _clean_generic_string(scopes[i])
        else:
            # for a non-class scope, process deeper
            if not scopes[i-1]:
                scopes[i] = remove_noise(scopes[i])

    # remove empties
    scopes = [a for a in scopes if a]

    # clean hollow lists
    if len(scopes) == 1:
        return scopes[0]
    else:
        return scopes

def class_collapse(scopes):
    ''' collapse nested list of scopes and make map of classes '''
    classes = {}
    for i in range(len(scopes)):
        if not isinstance(scopes[i], basestring):
            # the last in the list must be our class name
            # todo: maybe support nested classes
            name = scopes[i-1]
            # ignore all internal scopes and replace with ;
            value = ';'.join([a for a in scopes[i] if isinstance(a, basestring)])
            classes[name] = value

    return classes

def remove_class_noise(data):
    ''' remove things we don't care about inside a class '''
    for s in ['virtual', 'const', 'override', 'explicit',
              # Qt specific
              'Q_OBJECT', 'slots']:
        data = data.replace(' ' + s + ' ', ' ')

    found = True
    while found:
        found, data = _remove_ab(data, ' typedef', ';')

    data = re.sub('= [^,^;^)]*', '', data)

    return data

def _extract_protection(data, prot):
    ''' extract the protection level '''
    # only look for isolated : , must ignore ::
    start = data.find(' : ')
    if start > 0:
        prot = data[:start].strip()
        data = data[start+3:]
    return data, prot

def _split_name_type(data):
    ''' split a expression to name and type '''
    data = data.strip()
    start = data.rfind(' ')
    if start > 0:
        name = data[start+1:]
        type_ = data[:start]
        return name, type_
    else:
        # not sure what to do, probably ctor / dtor
        return data, ''

def _clean_method_name(data):
    ''' clean name (and param list) of a method '''
    data = re.sub(' *\( *', '(', data)
    data = re.sub(' *\) *', ')', data)
    data = re.sub(' *, *', ', ', data)
    return data

def process_class(data):
    ''' process class text into list of members and methods '''
    lines = []
    prot = 'private'
    for line in data.split(';'):
        # ignore empty expressions
        if not line.strip():
            continue
        line, prot = _extract_protection(line, prot)
        role = 'member'
        name, type_ = _split_name_type(line)
        start = line.find('(')
        if start > 0:
            role = 'method'
            name, type_ = _split_name_type(line[:start])
            name = _clean_method_name(name + line[start:])
        lines.append({
            'prot': prot,
            'role': role,
            'name': name,
            'type': type_
        })

    return lines

def _output_sep():
    ''' output separator '''
    return '-'*40 + '\n'

def _get_marker(prot):
    ''' get the marker for protection level '''
    if prot == 'public':
        return '+'
    elif prot == 'signals':
        return '<'
    elif prot == 'protected':
        return '#'
    elif prot == 'private':
        return '-'
    else:
        # treat others as private
        return '-'

def _output_line(e):
    ''' output a method / member in format '''
    return _get_marker(e['prot']) + e['name'] + ': ' + e['type'] + '\n'

def output_class(class_, lines):
    ''' output class in nice format '''
    s = _output_sep()
    s += class_ + '\n'
    s += _output_sep()
    for e in lines:
        if e['role'] == 'member':
            s += _output_line(e)
    s += _output_sep()
    for e in lines:
        if e['role'] == 'method':
            s += _output_line(e)
    s += _output_sep()

    return s

def get_html(data, output):
    template = '''
<!DOCTYPE html>
<html>
<head>
<style>
input[type=submit],
body {
  font-family: "Liberation Mono";
  font-size: 12pt;
}
footer {
  position: fixed;
  bottom: 10px;
  right: 30px;
}
.adjuster {
  display: flex;
  justify-content: center;
}
.horizontal {
  display: inline-block;
  padding: 10px;
}
</style>
</head>
<body>
<div class="adjuster">
<div class="horizontal">
<form method="POST" action="/timlyrics/hppuml/">
<p>
<span> Input: paste C++ class header here to </span>
<span> <input type="submit" value="convert"/> </span>
</p>
<textarea name="data" cols="80" rows="40">{{data}}</textarea>
</form>
</div>
<div class="horizontal">
<p> Output: UML styled text </p>
<textarea name="data" cols="80" rows="40">{{output}}</textarea>
</div>
</div>
<footer>
<a href="https://github.com/timlyrics/hppuml">github:timlyrics/hppuml</a>
</footer>
</body>
</html>
'''
    return template.replace('{{data}}', data).replace('{{output}}', output)

def run(data):
    ''' entry point for overall process '''
    source_data = data
    data = clean_chars(data)
    data = remove_comments(data)
    data = clean_format(data)

    scopes = collect_scope(data)
    scopes = remove_noise(scopes)

    classes = class_collapse(scopes)
    output = ''
    for class_ in classes:
        data = classes[class_]
        data = remove_class_noise(data)
        lines = process_class(data)
        output += output_class(class_, lines)

    return get_html(source_data, output)

if __name__ == '__main__':

    data = 'class A { public: int foo(); int bar; }'
    if 'data' in Hook['params']:
        data = Hook['params']['data']

    print(run(data))

# extract UML from C++ header
class HppUml(object):

    @staticmethod
    def Cleanse(data):
        # removes block comments
        while True:
            start = data.find('/*')
            if start == -1:
                break
            stop = data.find('*/', start)
            if stop == -1:
                # there is something wrong but we don't know what to do
                break
            data = data[:start] + data[stop+2:]

        # remove line comments and delaratives and new lines
        lines = []
        for line in data.split('\n'):
            line = line.strip()
            if len(line) > 0 and line[0] != '/' and line[0] != '#':
                lines.append(line)
        data = ''.join(lines)

        return data

    @staticmethod
    def CollectClasses(data):
        # extract curly brackets
        data = data.replace('{', '{;')
        classes = {}
        while True:
            # find closing bracket
            stop = data.find('}')
            if stop == -1:
                break
            # find open bracket
            start = data.rfind('{', 0, stop)
            if start == -1:
                break
            # find definition for the brackets
            keyStart = data.rfind(';', 0, start)
            if keyStart == -1:
                keyStart = 0
            keyStart += 1
            key = data[keyStart:start].strip()
            # check if this is a class
            if key.find('class') == 0:
                # remember
                classes[key] = data[start+1:stop]
            # remove from parent data
            data = data[:start] + ';' + data[stop+1:]

        return classes

    @staticmethod
    def ConvertUnit(data):
        if not data or 'typedef' in data:
            return 'bad', ''
        data = data.replace(';','').split('=')[0].replace('virtual','').replace('const','').replace('override','').strip()
        lastWord = data.split(' ')[-1]
        if ')' not in lastWord:
            sep = data.rfind(' ')
            field = data[sep:].strip() + ': ' + data[:sep].strip()
            return 'field', field
        else:
            # method
            # \todo this is not preceise science here, there are exceptions
            stop = data.find('(')
            start = data.rfind(' ', 0, stop)
            if start == -1:
                start = 0
            method = data[start:stop].strip() + '()'
            return 'method', method

    @staticmethod
    def ConvertSection(data):
        fields = []
        methods = []
        for unit in data.split(';'):
            t, content = HppUml.ConvertUnit(unit)
            if t == 'field':
                fields.append(content)
            elif t == 'method':
                methods.append(content)

        return fields, methods

    @staticmethod
    def LevelMarker(level):
        if level == 'public:':
            return '+'
        elif level == 'signals:':
            return '<'
        elif level == 'protected:':
            return '#'
        elif level == 'private:':
            return '-'

    @staticmethod
    def ConvertClass(data):
        # ignore Qt slots
        data = data.replace(' slots:', ':')
        # find protection levels
        levels = ['public:', 'signals:', 'protected:', 'private:']
        idxMap = {0: 'private:'}
        for level in levels:
            idx = -1
            while True:
                idx = data.find(level, idx+1)
                if idx != -1:
                    idxMap[idx] = level
                else:
                    break
        idxs = sorted(idxMap.keys())

        fields = []
        methods = []
        for i in range(len(idxs)):
            level = idxMap[idxs[i]]
            start = idxs[i]+len(level)
            stop = idxs[i+1] if i < len(idxs)-1 else len(data)
            section = data[start:stop]
            myFields, myMethods = HppUml.ConvertSection(section)
            for field in myFields:
                fields.append(HppUml.LevelMarker(level) + field)
            for method in myMethods:
                methods.append(HppUml.LevelMarker(level) + method)

        return fields, methods

    @staticmethod
    def PrintClass(name, fields, methods):
        print('------------------------')
        print(name.split(':')[0].replace('class','').strip())
        print('------------------------')
        for field in fields:
            print(field)
        print('------------------------')
        for method in methods:
            print(method)
        print('------------------------')

    @staticmethod
    def Parse(data):

        data = HppUml.Cleanse(data)
        classes = HppUml.CollectClasses(data)
        for key in classes:
            fields, methods = HppUml.ConvertClass(classes[key])
            HppUml.PrintClass(key, fields, methods)

if __name__ == '__main__':
    fnames = [
        'a.h'
    ]
    e = HppUml()
    for fname in fnames:
        with open(fname, 'r') as f:
            e.Parse(f.read())

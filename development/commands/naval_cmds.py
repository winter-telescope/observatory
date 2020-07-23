#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Naval Fate.

Usage:
  naval_fate.py new <name>...
  naval_fate.py move <x> <y>
  naval_fate.py shoot <x> <y>
  naval_fate.py -h | --help
  naval_fate.py --version

Options:
  -h --help     Show this screen.
  --version     Show version.
  --speed=<kn>  Speed in knots [default: 10].
  --moored      Moored (anchored) mine.
  --drifting    Drifting mine.

"""
#from docopt import docopt
import docopt

def docopt_cmd(func):
    """
    This decorator is used to simplify the try/except block and pass the result
    of the docopt parsing to the called action.
    """
    def fn(arg):
        try:
            opt = docopt.docopt(fn.__doc__, arg)

        except docopt.DocoptExit as e:
            # The DocoptExit is thrown when the args do not match.
            # We print a message to the user and the usage block.

            print('Invalid Command!')
            print(e)
            return

        except SystemExit:
            # The SystemExit exception prints the usage for --help
            # We do not need to do the print here.

            return

        return func( opt)

    fn.__name__ = func.__name__
    fn.__doc__ = func.__doc__
    fn.__dict__.update(func.__dict__)
    return fn

@docopt_cmd
def shoot(args):
    """usage: shoot <x> <y> """

    print(f'shooting at args = {args}')
@docopt_cmd
def new(args):
    """usage: new <name> """

    print(f'new ship = {args}')
    
d = dict({'shoot' :  shoot,
          'new'   :  new})



"""
if __name__ == '__main__':
    arguments = docopt(__doc__, version='Naval Fate 2.0')
    print(arguments)
"""

argv = 'new fart'

arg = docopt.docopt(__doc__,argv = argv)
print(arg)
print()
print()




'''

for fn_name in d.keys():

    arg2 = docopt.docopt(d[fn_name].__doc__,argv)
    print(f'args for function {fn_name} :{arg2}')

#%%
options = docopt.parse_defaults(__doc__)



doc = __doc__
docopt.DocoptExit.usage = docopt.printable_usage(doc)
options = docopt.parse_defaults(doc)
pattern = docopt.parse_pattern(docopt.formal_usage(docopt.DocoptExit.usage), options)
# [default] syntax for argument is disabled
#for a in pattern.flat(Argument):
#    same_name = [d for d in arguments if d.name == a.name]
#    if same_name:
#        a.value = same_name[0].value
argv = docopt.parse_argv(docopt.TokenStream(argv, docopt.DocoptExit), list(options))
pattern_options = set(pattern.flat(docopt.Option))
for ao in pattern.flat(docopt.AnyOptions):
    doc_options = docopt.parse_defaults(doc)
    ao.children = list(set(doc_options) - pattern_options)
    #if any_options:
    #    ao.children += [Option(o.short, o.long, o.argcount)
    #                    for o in argv if type(o) is Option]
#docopt.extras(help, docopt.version, argv, doc)
matched, left, collected = pattern.fix().match(argv)
if matched and left == []:  # better error message if left?
    D = dict((a.name, a.value) for a in (pattern.flat() + collected))
'''
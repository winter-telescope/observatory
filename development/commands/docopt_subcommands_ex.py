#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jul  8 17:23:59 2020

@author: nlourie
"""

# Basic, most common usage of docopt_subcommands

import docopt_subcommands as dsc


# 1. Use the `command` decorator to add subcommands functions.
@dsc.command()
def foo_handler(precommand_args, args):
    """usage: {program} foo <name>

    Apply foo to a name.
    """
    print("Foo, {}".format(args['<name>']))


@dsc.command()
def bar_handler(precommand, args):
    """usage: {program} bar <name>

    Apply bar to a name.
    """
    print("Bar, {}".format(args['<name>']))


# 2. Pass a program name and version string to `main` to run a program with the
# subcommands you defined with the decorators above.

line = 'foo farts'



dsc.main(program='docopt-subcommand-example',argv = line)
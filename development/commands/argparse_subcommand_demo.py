#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jul  9 10:55:22 2020

Argparse subcommand demo from here:
    https://chase-seibert.github.io/blog/2014/03/21/python-multilevel-argparse.html
    
Multi-level argparse in Python (parsing commands like git)
It’s a common pattern for command line tools to have multiple subcommands that 
run off of a single executable. For example, git fetch origin and 
git commit --amend both use the same executable /usr/bin/git to run. 
Each subcommand has its own set of required and optional parameters.

This pattern is fairly easy to implement in your own Python command-line 
utilities using argparse. Here is a script that pretends to be git and 
provides the above two commands and arguments.

#!/usr/bin/env pyt


@author: nlourie
"""

import argparse
import sys


class FakeGit(object):

    def __init__(self, argv = None):
        parser = argparse.ArgumentParser(
            description='Pretends to be git',
            usage='''git <command> [<args>]

The most commonly used git commands are:
   commit     Record changes to the repository
   fetch      Download objects and refs from another repository
''')
        parser.add_argument('command', help='Subcommand to run')
        # parse_args defaults to [1:] for args, but you need to
        # exclude the rest of the args too, or validation will fail
        
        if argv is None:
            self.argv = sys.argv[1:]
            if len(self.argv) < 1:
                   self.argv = ['-h']
        else:
            self.argv = argv.split(' ')
        
        #print(f'self.argv = {self.argv}')
            
        self.command = parser.parse_args(self.argv[0:1]).command
        #print(f'cmdarg = {cmdarg}')
        
        #self.command = cmdarg.command    
        print(f'command = {self.command}')
        
        if not hasattr(self, self.command):
            print('Unrecognized command')
            parser.print_help()
            #sys.exit(1)
            pass
        # use dispatch pattern to invoke method with same name
        else:
            getattr(self, self.command)()

    def commit(self):
        parser = argparse.ArgumentParser(
            description='Record changes to the repository')
        # prefixing the argument with -- means it's optional
        parser.add_argument('--amend', action='store_true')
        # now that we're inside a subcommand, ignore the first
        # TWO argvs, ie the command (git) and the subcommand (commit)
        #args = parser.parse_args(sys.argv[2:])
        self.args = parser.parse_args(self.argv[1:])
        print(f'args = {self.args}')
        print('Running git commit, amend=%s' % self.args.amend)

    def fetch(self):
        parser = argparse.ArgumentParser(
            description='Download objects and refs from another repository')
        # NOT prefixing the argument with -- means it's not optional
        parser.add_argument('repository')
        #args = parser.parse_args(sys.argv[2:])
        self.args = parser.parse_args(self.argv[1:])
        print(f'dir(args) = {self.args._get_args}')
        print(f'args = {self.args}')
        print('Running git fetch, repository=%s' % self.args.repository)


            

if __name__ == '__main__':
    a = FakeGit('fetch -h')
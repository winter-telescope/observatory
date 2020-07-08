#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jul  6 17:42:18 2020


command line interfasce using click


@author: nlourie
"""

import click

@click.group()
def main():
    pass

@main.command()
def hello():
    click.echo('Hello World')
    
@main.command()
@click.argument('n', nargs=1, type = int)
def fartntimes(n):
    print(f'Farting {n} times:')
    for i in range(n):
        print(f'fart {i+1}/{n}')
    
@main.command()
@click.option('--count', default=1, help='number of greetings')
@click.argument('name')
def hello2(count, name):
    for x in range(count):
        print('Hello %s!' % name)    

if __name__ == '__main__':
    #hello()
    #fartNtimes(5)
    #hello2()
    main()
    
    # get a command from the user
    cmd = click.prompt('Enter a Command')
    exec(cmd)
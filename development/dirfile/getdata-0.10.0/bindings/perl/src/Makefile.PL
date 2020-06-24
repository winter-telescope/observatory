# Copyright (C) 2015 D. V. Wiebe
#
##########################################################################
#
# This file is part of the GetData project.
#
# GetData is free software; you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation; either version 2.1 of the License, or (at your
# option) any later version.
#
# GetData is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
#
# bindings/perl/src/Makefile.PL.  Generated from Makefile.PL.in by configure.

use ExtUtils::MakeMaker;

WriteMakefile(
  ABSTRACT => "Perl bindings to the GetData library",
  AUTHOR => 'The GetData Project <getdata-devel@lists.sourceforge.net>',
  VERSION_FROM => "lib/GetData.pm",
  DEFINE => "-DHAVE_CONFIG_H -I../../../src",
  LIBS => ['-L../../../src/.libs/ -lgetdata'],
  INC => '-I../../../src',
  LICENSE => 'lgpl_2_1',
  NAME => "GetData",
  PREREQ_PM => {
    perl => '5.6.0',
    'Math::Complex' => '1.34'
  },
);

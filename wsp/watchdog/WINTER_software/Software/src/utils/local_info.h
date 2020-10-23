/**
 \file local_info
 \brief Local information for this version of the ROBO software
 \details The parameters in this header file are used to define information that
 is used only for this version of the software.  The ROBO utils directory is
 used in multiple projects, so this contains data for this version of the system
 
 Copyright (c) 2009-2021 California Institute of Technology.
 \author Dr. Reed L. Riddle  riddle@caltech.edu
 */

// Use a preprocessor statement to set a variable that checks if the header has 
// already loaded...this avoids loading the header file more than once. 
# ifndef ROBO_LOCAL_H
# define ROBO_LOCAL_H

/// Robotic observer name
const std::string ROBOTIC_OBSERVER = "WINTER";
const std::string ROBOTIC_INSTRUMENT = "WINTER";
const std::string ROBOTIC_SYSTEM = "WINTER";

/// Software version
const std::string ROBOTIC_SOFTWARE_VERSION = "0.1  August 21, 2020";


# endif

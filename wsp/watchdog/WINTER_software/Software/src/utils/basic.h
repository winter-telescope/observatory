/**
 \file common.h
 \brief Common parameters used throughout the ROBO software
 \details this header file includes the common parameters that are used in 
 enough places through the ROBO software that it is simpler to gather them in
 one place.  
 
 Copyright (c) 2009-2011 California Institute of Technology.
 \author Dr. Reed L. Riddle  riddle@caltech.edu
 \note To use this class, define it somewhere near the main() function, but 
 it must be of global scope:
 \code
 ROBO_common common_info(COMMON_CONFIG_FILE);
 int main(int argc, char *argv[])
 \endcode
 \note The COMMON_CONFIG_FILE define statement is modified by the CMakeLists.txt
 file that resides at the top directory of the source code. If a different
 configuration file is desired for the common parameters, change the value there
 and not in this file (the variable is generated during the compilation process).
 
 <b>Version History</b>:
 \verbatim
 2009-07-17:  First complete version
 2010-01-20:  Telemetry system added
 2010-02-25:  Updated error control system to new standard
 \endverbatim
 */

// Use a preprocessor statement to set a variable that checks if the header has 
// already loaded...this avoids loading the header file more than once. 
# ifndef ROBO__BASIC_H
# define ROBO__BASIC_H

// System include files
# include <vector>

// Local include files
# include "local_info.h"

// Error control defines
/// The lower limit of the ROBO error space.  Errors below this are something
/// likely from the system; errors between 100 and 999 are ROBO system errors.
const int ROBO_ERROR_SPACE = 100;
/// Resource error space, set velues for flags to 1000 or above.
const int RESOURCE_ERROR_SPACE = 1000;
/// Fatal error code, use this to flag bad things
const int FATAL_ERROR = -1;
/// No error, use this to flag when things work as expected
const int NO_ERROR = 0;
/// Flag an error, but not one that is fatal in some way
const int ERROR = 1;
/// Pause an exectuion loop with this flag (not technically an error, but can be 
/// used in loops where the ERROR/NO_ERROR flags are used for control).
const int PAUSE_LOOP = 2;

/// ROBO system errors
enum {
  ERROR_FILE_NAME_EMPTY = 100,
  ERROR_FILE_NO_EXIST,
  ERROR_FILE_OPEN,
  ERROR_FILE_CLOSE,
  ERROR_FILE_EMPTY,
  ERROR_MAX_ATTEMPTS_FAIL,
  ERROR_PARAM_BLANK,
  ERROR_DIRECTORY,
  ERROR_SYSTEM_DIRECTORY,
  ERROR_CONTROL_CAUGHT,
  ERROR_FATAL,
  ERROR_OPEN,
  ERROR_CLOSE,
  ERROR_START,
  ERROR_STOP,
  ERROR_STATUS,
  ERROR_FOUND,
  ERROR_TIME_DIFFERENCE,
  ERROR_MOTION,
  ERROR_CLIENT_BUSY,
  ERROR_TIMEOUT,
  ERROR_UNKNOWN
};

/// ROBO control space for each of the classes
enum {
  CLASS_SCIMEASURE_CCD39  =  1000,
  CLASS_BMM_DM            =  2000,
  CLASS_RECONSTRUCTOR     =  3000,
  CLASS_WTI_NPS           =  4000,
  CLASS_ROBO_FILE       =  5000,
  CLASS_AO                =  6000,
  CLASS_AO_CONTROL        =  6100,
  CLASS_ANDOR_IXON        =  7000,
  CLASS_IXON_INTERFACE    =  7100,
  CLASS_LGSD              =  8000,
  CLASS_JDSU_LASER        =  8100,
  CLASS_SERIAL            =  9000,
  CLASS_NEWPORT           = 10000,
  CLASS_ADCD              = 11000,
  CLASS_HIGHLAND          = 12000,
  CLASS_TIP_TILT          = 13000,
  CLASS_PALOMAR_60        = 14000,
  CLASS_XENICS_INGAAS     = 15000,
  CLASS_FILTER            = 16000,
  CLASS_WEATHERD          = 17000,
  CLASS_TELSTATD          = 18000,
  CLASS_TCSD              = 19000,
  CLASS_TELESCOPE         = 20000,
  CLASS_CAMERA            = 21000,
  CLASS_VICD              = 22000,
  CLASS_IRCD              = 23000,
  CLASS_QUEUE             = 24000,
  CLASS_ROBO              = 25000,
  CLASS_HILOCAM_INTERFACE = 26000,
  CLASS_ARCHON_INTERFACE  = 27000,
  CLASS_SENSORS           = 28000,
  CLASS_CAMPBELL_CR3000_INTERFACE = 28100,
  CLASS_LAKESHORE_INTERFACE = 28200,
  CLASS_PFEIFFER_INTERFACE = 28300,
  CLASS_MOTION            = 29000,
  CLASS_PI_HEXAPOD_INTERFACE = 29100,
  CLASS_FITSD             = 30000,
  CLASS_KUKA              = 30100,
  CLASS_EPM               = 30200,
  CLASS_SHUTTERD          = 30300,
  CLASS_POWERD            = 30400,
  CLASS_WH_INTERFACE	    = 30500,
  CLASS_CAMPBELL_CR1000_INTERFACE = 30600,
  CLASS_DATAD             = 30700,
  CLASS_CHILLER_INTERFACE = 30800,
  CLASS_SHUTTER_INTERFACE = 30900,
  CLASS_ILLUMINATOR_INTERFACE = 31000,
  CLASS_ILLUMINATOR       = 31100,
  CLASS_MESSAGE           = 31200,
  CLASS_WATCHDOG           = 31300,
  CLASS_ARM_HEATER        = 31400
};

/// enum used by print_bool to specify the type of output
typedef enum {
  PRINT_BOOL_ON_OFF,
  PRINT_BOOL_TRUE_FALSE,
  PRINT_BOOL_YES_NO,
  PRINT_BOOL_HIGH_LOW
} bool_type;

/*/// Error flag thrown when a file name is empty
 const int ERROR_FILE_NAME_EMPTY = 100;
 /// Error flag thrown when a file doesn't exist
 const int ERROR_FILE_NO_EXIST = 101;
 /// Error flag thrown when a file cannot be opened (likely a permissions issue)
 const int ERROR_FILE_OPEN = 102;
 /// Error flag thrown when a function that is iterating a loop fails to complete
 /// its operation after a number of attempts.
 const int ERROR_MAX_ATTEMPTS_FAIL = 103;
 /// Error flag thrown when a configuration parameter is empty when reading a
 /// configuration file.
 const int ERROR_PARAM_BLANK = 104;
 /// Error flag thrown when a directory can't be accessed.
 const int ERROR_DIRECTORY = 105;*/

// Standard values for various string lengths
/// A really short string length for character strings of a defined length
const int SHORT_LINE_LENGTH = 10;
/// A medium string length for character strings of a defined length
const int MEDIUM_LINE_LENGTH = 25;
/// A standard 80 character  length for character strings of a defined length
const int LINE_LENGTH = 80;
/// A long string length for character strings of a defined length; this is the
/// one to use usually, unless you know a string will definitely be shorter than
/// one of the other lengths
const int STRING_LINE_LENGTH = 1024;

/// Maximum file size supported for image data cubes = 1GB
const unsigned long MAX_IMAGE_DATA_SIZE = 1073741824;

// Flags for time stamp formats
/// Flag to output a time stamp of the format YYYYMMDDHH
const int FILENAME_DAY = 1;
/// Flag to output a time stamp of the format YYYYMMDDHH
const int FILENAME_HOUR = 2;
/// Flag to output a time stamp of the format YYYYMMDD-HHMMSS
const int FILENAME_SECOND = 3;
/// Flag to output a time stamp of the format YYYYMMDD-HHMMSS.SSS
const int FILENAME_MILLISECOND = 4;
/// Flag to output a time stamp of the format YYYYMMDD-HHMMSS.SSSSSS
const int FILENAME_MICROSECOND = 5;
/// Flag to output a time stamp of the format YYYY-MM-DD HH:MM:SS
const int TIMESTAMP = 10;
/// Get a timestamp to an accuracy of a second  YYYY-MM-DD HH:MM:SS
const int SECOND_WHOLE = 11;
/// Get a time stamp to a tenth of a second: YYYY-MM-DD HH:MM:SS.S
const int SECOND_TENTH = 12;
/// Get a time stamp to a hundredth of a second: YYYY-MM-DD HH:MM:SS.SS
const int SECOND_HUNDREDTH = 13;
/// Get a time stamp to a millisecond: YYYY-MM-DD HH:MM:SS.SSS
const int SECOND_MILLI = 14;
/// Get a time stamp to a microsecond: YYYY-MM-DD HH:MM:SS.SSSSSS
const int SECOND_MICRO = 15;

/// Maximum number of attempts for loops that have an attempt limit.
const int MAX_ATTEMPTS = 5;
/// Maximum number of attempts for loops in the robotic system
const int MAX_ROBOTIC_ATTEMPTS = 3;

/// Maximum telemetry data points to push to a file
const int MAX_TELEMETRY_POINTS = 75000;

/// A common bad value to use as a flag
const int BAD_VALUE = -9999;

/// AO operating mode switches
enum {
  AO_MODE_LGS,
  AO_MODE_NGS
};

/// Name for common class log file
# define  COMMON_LOGFILE_NAME   "common"


// Tokenizer for breaking strings up into segments.
int Tokenize(const std::string& str, std::vector<std::string>& tokens,
             const std::string& delimiters);

// Print a boolean as a human readable value
std::string print_bool(bool state, bool_type type = PRINT_BOOL_ON_OFF);

bool get_bool_value(std::string & input);

# endif

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
# ifndef ROBO_COMMON_H
# define ROBO_COMMON_H

// System include files
# include <iostream>
# include <vector>
# include <fstream>
# include <sstream>
//# include <string>
# include <limits.h>
# include <unistd.h>

// Local include files
# include "basic.h"
# include "registry.h"
# include "file_ops.h"
//# include "error.h"

/// Use CMake to define the configuration file for the default common.cfg setup.
/// This file nominally sits in the Config directory with the ROBO software,
/// so it should always be in the package and findable.  If the directory path
/// needs to be hardcoded, then rewrite this define with that as the value
/// instead (example:  # define COMMON_CONFIG_FILE "/home/dir/common.cfg")
# define  COMMON_CONFIG_FILE  "/home/ztf/WINTER/Software/Config/common.cfg"

/// ROBO command and reply codes
enum {
  NO_COMMAND = 0,
  MESSAGE_REPLY,
  ROUTINE_EXIT,
  DAEMON_SHUTDOWN
};

/* Error messages sent from the control function. Make sure there are no spaces
 in these strings since they are part of a message string that will be
 tokenized on spaces. */
const std::string CONTROL_ERROR_ERROR = "ERROR";
const std::string CONTROL_ERROR_NO_ERROR = "NO_ERROR";
const std::string CONTROL_ERROR_FOUND = "ERROR_FOUND";
const std::string CONTROL_ERROR_OPEN = "ERROR_OPEN";
const std::string CONTROL_ERROR_CLOSE = "ERROR_CLOSE";
const std::string CONTROL_ERROR_SET_POSITION = "ERROR_SET_POSITION";
const std::string CONTROL_ERROR_STATUS = "STATUS:";
const std::string CONTROL_ERROR_ERROR_CODE = "ERROR CODE:";
const std::string CONTROL_ERROR_UNKNOWN = "UNKNOWN_ERROR";

/** \class ROBO_common
 \brief Class for common elements used throughout the ROBO software.
 \details This class contains variables that are used throughout the entire
 ROBO software system.  It is simpler to combine them here, and have them
 available to the entire software, than try to drag them around or define them
 as open global variables.
 \note To use this class, define it somewhere near the main() function, but
 it must be of global scope:
 \code
 ROBO_common common_info(COMMON_CONFIG_FILE);
 int main(int argc, char *argv[])
 \endcode
 \note The COMMON_CONFIG_FILE define statement is modified by the CMakeLists.txt
 file that resides at the top directory of the source code. If a different
 configuration file is desired for the common parameters, change the value
 there and not in this file (the variable is generated during the compilation
 process). */
class ROBO_common {
private:
  
  /** \var int user_id
   \details The user ID value from the operating system */
  int user_id;
  
  /** \var std::string config_file
   \details Character string containing file name for configuration file */
  std::string config_file;
  
  // Reads in the common.cfg configuration file.
  void common_config(std::string config_file_in);
  
  /// Assignment operator
  ROBO_common operator= (const ROBO_common & old_common);
  
  /// Copy constructor
  ROBO_common(const ROBO_common & old_common);
  
public:
  
  /** \var ROBO_registry erreg
   \details Error registry for all error codes defined in the program.*/
  ROBO_registry erreg;
  
  /** \var ROBO_registry comreg
   \details Command registry for all command codes defined in the program.*/
  ROBO_registry comreg;
  
  /** \var bool verbose
   \details Verbosity flag.  A value of true outputs messages to stdout,
   a value of false does not.  Set to true for command line applications.*/
  bool verbose;
  
  /** \var std::string home_dir
   \details String containing the home directory of the user running the
   software. */
  std::string home_dir;
  
  /** \var std::string log_dir
   \details String containing the log directory, which is set in
   configuration file common.cfg. */
  std::string log_dir;
  
  /** \var std::string bin_dir
   \details String containing the bin directory where executables live, which is
   set in configuration file common.cfg. */
  std::string bin_dir;
  
  /** \var std::string config_dir
   \details String containing the configuration file directory, which is
   set in configuration file common.cfg. */
  std::string config_dir;
  
  /** \var std::string status_dir
   \details String containing the status directory, which is set in
   configuration file common.cfg. */
  std::string status_dir;
  
  /** \var std::string executable_name
   \details The name of the executable that is currently running. */
  std::string executable_name;
  
  /** \var std::string data_dir
   \details String containing the data directory, which is set in
   configuration file common.cfg. */
  std::string data_dir;
  
  /** \var std::string telemetry_dir
   \details String containing the telemetry directory, which is set in
   configuration file common.cfg. */
  std::string telemetry_dir;
  
  /** \var std::string wfs_data_dir
   \details String containing the WFS data directory, which is set in
   configuration file common.cfg. */
  std::string wfs_data_dir;
  
  /** \var std::string vic_data_dir
   \details String containing the visible camera data directory, which is set in
   configuration file common.cfg. */
  std::string vic_data_dir;
  
  /** \var std::string irc_data_dir
   \details String containing the infrared camera data  directory, which is set in
   configuration file common.cfg. */
  std::string irc_data_dir;
  
  /** \var std::string tip_tilt_dir
   \details String containing the tip tilt data directory, which is set in
   configuration file common.cfg. */
  std::string tip_tilt_dir;
  
  /** \var std::string tip_tilt_dir
   \details String containing the laser closure window file directory,
   which is set in configuration file common.cfg. */
  std::string laser_closure_window_dir;
  
  /** \var std::string tip_tilt_dir
   \details String containing the queue directory, which is set in configuration
   file common.cfg. */
  std::string queue_dir;
  
  /** \var int day_switch_time
   \details Hour of day when the system prepares for the next night of 
   operations by resetting variables, clearing information, that sort of thing.
   It will create a new directory with the date set for the next day.  This 
   fixes an issue where systems create directories for an observing night for 
   the day before, so files end up in the wrong directory for the current 
   observing night. */
  int day_switch_time;
  
  /** \var pid_t pid
   \details Process ID for this executable. */
  pid_t pid;
  
  /** \var std::string log_name
   \details String containing common log name */
  std::string log_name;
  ROBO_logfile log;
  
  /** \var bool using_lock_file
   \details Flag if the software can't find the /proc directory for PID
   tracking and is using the manual lock file system. */
  bool using_lock_file;
  
  
  /**************** set_verbose ****************/
  /** Sets the verbose level for the executable.
   \param [verbose_in] Verbose level
   \note none
   */
  void set_verbose(bool verbose_in){
    if (verbose_in == true){
      this->verbose = true;
    }
    else if (verbose_in == false){
      this->verbose = false;
    }
  }
  /**************** set_verbose ****************/
  
  
  /**************** get_verbose ****************/
  /** Reads the verbose level for the executable.
   \param [verbose_in] Verbose level
   \note none
   */
  bool get_verbose(){
    return (this->verbose);
  }
  /**************** get_verbose ****************/
  
  
  /** Constructor for the class, which sets a few default values.
   \param [config_file)] The configuration file used
   \param [verbose] The verbose flag.  A value of true outputs to the command
   line, a value of false does not.
   \param [config_dir("./")] Sets default value of "./" to the configuration
   directory, in case the configuration file does not have a value.
   \param [data_dir("./")]  Sets a default value of "./" to the configuration
   directory, in case the configuration file does not have a value.
   \param [log_dir("./")]  Sets a default value of "./" to the configuration
   directory, in case the configuration file does not have a value.
   \param [status_dir("./")]   Sets a default value of "./" to the
   configuration directory, in case the configuration file does not have a
   value.
   \param [telemetry_dir("./")]   Sets a default value of "./" to the
   configuration directory, in case the configuration file does not have a
   value.
   \param [user_id(0)]   Sets a default value of "0".
   \param [log_name("common")]   Sets a default name "common" for the common
   log file name shared through the software.   */
  ROBO_common(std::string set_config_file, bool verbose_in):
  user_id(0), config_file(""), verbose(true),
  home_dir("/home/ztf/WINTER/Software/"),
  log_dir("/home/ztf/WINTER/Software/Logs/"),
  config_dir("/home/ztf/WINTER/Software/Config/"),
  status_dir("/home/ztf/WINTER/Software/Status/"),
  executable_name(""), data_dir("/home/ztf/WINTER/Data/"),
  telemetry_dir("/home/ztf/WINTER/Data/Telemetry/"), log_name("common")
  {
    // Read in the configuration file
    this->common_config(set_config_file);
    // Set the verbose flag
    this->verbose = verbose_in;
    
    std::string function("ROBO_common::ROBO_common");
    
    this->log.filename = this->log_dir + COMMON_LOGFILE_NAME + ".log";
    
    std::stringstream message;
    char exe[PATH_MAX];
    memset(exe, 0, sizeof(exe));
    readlink("/proc/self/exe", exe, sizeof(exe)-1);
    
    message << "Robotic software version " << ROBOTIC_SOFTWARE_VERSION
    << ", executable: " << exe;
    this->log.write(function, false, message.str());
    
    this->using_lock_file = false;
    
    
    // Add the basic codes from common.h into the registry
    this->comreg.registry_name = "Command Code Registry";
    this->comreg.add_code(NO_COMMAND, "NO_COMMAND", function, this->log);
    
    this->erreg.registry_name = "Error Code Registry";
    this->erreg.add_code(ERROR_FILE_NAME_EMPTY, "ERROR_FILE_NAME_EMPTY",
                         function, this->log);
    this->erreg.add_code(ERROR_FILE_NO_EXIST, "ERROR_FILE_NO_EXIST",
                         function, this->log);
    this->erreg.add_code(ERROR_FILE_OPEN, "ERROR_FILE_OPEN",
                         function, this->log);
    this->erreg.add_code(ERROR_FILE_CLOSE, "ERROR_FILE_CLOSE",
                         function, this->log);
    this->erreg.add_code(ERROR_FILE_EMPTY, "ERROR_FILE_EMPTY",
                         function, this->log);
    this->erreg.add_code(ERROR_MAX_ATTEMPTS_FAIL, "ERROR_MAX_ATTEMPTS_FAIL",
                         function, this->log);
    this->erreg.add_code(ERROR_PARAM_BLANK, "ERROR_PARAM_BLANK",
                         function, this->log);
    this->erreg.add_code(ERROR_DIRECTORY, "ERROR_DIRECTORY",
                         function, this->log);
    this->erreg.add_code(ERROR_SYSTEM_DIRECTORY, "ERROR_SYSTEM_DIRECTORY",
                         function, this->log);
    this->erreg.add_code(ERROR_CONTROL_CAUGHT, "ERROR_CONTROL_CAUGHT",
                         function, this->log);
    this->erreg.add_code(ERROR_FATAL, "ERROR_FATAL", function, this->log);
    this->erreg.add_code(ERROR_OPEN, "ERROR_OPEN", function, this->log);
    this->erreg.add_code(ERROR_CLOSE, "ERROR_CLOSE", function, this->log);
    this->erreg.add_code(ERROR_START, "ERROR_START", function, this->log);
    this->erreg.add_code(ERROR_STOP, "ERROR_STOP", function, this->log);
    this->erreg.add_code(ERROR_STATUS, "ERROR_STATUS", function, this->log);
    this->erreg.add_code(ERROR_FOUND, "ERROR_FOUND", function, this->log);
    this->erreg.add_code(ERROR_TIME_DIFFERENCE, "ERROR_TIME_DIFFERENCE",
                         function, this->log);
    this->erreg.add_code(ERROR_CLIENT_BUSY, "ERROR_CLIENT_BUSY", function,
                         this->log);
    this->erreg.add_code(ERROR_TIMEOUT, "ERROR_TIMEOUT", function, this->log);
    this->erreg.add_code(ERROR_UNKNOWN, "ERROR_UNKNOWN", function, this->log);
    
    
    
  };
  
  /// Destructor
  ~ROBO_common(){};
  
  // Allow directory_name_check to access the private variables in the class
  friend std::string directory_name_check(std::string original,
                                          std::string config_name, std::string new_directory);
};


class ROBO_status
{
public:
  
  ROBO_file status_file;
  ROBO_file telemetry_file;
  time_t unix_time;
  std::string status_time;
  std::stringstream current_status;
  std::stringstream temp_status;
  
  //    std::string blanks;
  //    const std::string blanks = std::string(100, ' ');
  
  /// Assignment operator
  ROBO_status operator= (const ROBO_status & in_status)
  {
    this->status_file = in_status.status_file;
    this->telemetry_file = in_status.telemetry_file;
    this->unix_time = in_status.unix_time;
    this->status_time = in_status.status_time;
    this->current_status << in_status.current_status.rdbuf();
    this->temp_status << in_status.temp_status.rdbuf();
    
    return(in_status);
  }
  
  ROBO_status (const ROBO_status & in_status)
  {
    this->status_file = in_status.status_file;
    this->telemetry_file = in_status.telemetry_file;
    this->unix_time = in_status.unix_time;
    this->status_time = in_status.status_time;
    this->current_status << in_status.current_status.rdbuf();
    this->temp_status << in_status.temp_status.rdbuf();
  }
  
  ROBO_status(){};
  //:blanks(100, ' ')
  
  
  void initialize(std::string name, std::string status_path,
                  std::string telemetry_path, bool name_fixed = false)
  {
    std::stringstream file;
    
    if (name_fixed == true){
      file << status_path << name;
    }
    else {
      file << status_path << name << "_status";
    }
    this->status_file.filename = file.str();
    file.str("");
    file << telemetry_path << name << ".dat";
    this->telemetry_file.filename = file.str();
    
  };
  
  void print_status(bool print_time = true){
    
    this->status_time = get_current_time(SECOND_MILLI);
    this->unix_time = time(NULL);
    
    // Clear the status string and put the new status string into it
    this->current_status.str("");
    this->current_status << this->temp_status.str();
    this->temp_status.str("");
    
    // Send the status to the running log file with all of the status data
    this->telemetry_file.open_file(OPEN_FILE_APPEND);
    if (print_time == true){
      this->telemetry_file.filestream << this->status_time << " ";
    }
    this->telemetry_file.filestream << this->current_status.str()
    << std::flush;
    this->telemetry_file.close_file();
    
    // Reset the system status file to the beginning and put the status into
    // the file.
    this->status_file.open_file(OPEN_FILE_WRITE);
    //      this->status_file.filestream.seekg(0, std::ios::beg);
    if (print_time == true){
      this->status_file.filestream << this->status_time << " ";
    }
    this->status_file.filestream << this->current_status.str() << std::flush;
    this->status_file.close_file();
  }
  
  void print_status_only(bool print_time = true){
    
    this->status_time = get_current_time(SECOND_MILLI);
    this->unix_time = time(NULL);
    
    // Clear the status string and put the new status string into it
    this->current_status.str("");
    this->current_status << this->temp_status.str();
    this->temp_status.str("");
    
    // Reset the system status file to the beginning and put the status into
    // the file.
    this->status_file.open_file(OPEN_FILE_WRITE);
    if (print_time == true){
      this->status_file.filestream << this->status_time << " ";
    }
    this->status_file.filestream << this->current_status.str() << std::flush;
    this->status_file.close_file();
  }
  
};


//// Tokenizer for breaking strings up into segments.
//int Tokenize(const std::string& str, std::vector<std::string>& tokens,
//              const std::string& delimiters);

// Trip spaces from the ends of strings
void TrimSpaces( std::string& str);

//// Print a boolean as a human readable value
//std::string print_bool(bool state, bool_type type = PRINT_BOOL_ON_OFF);

// Every routine gets some kind of usage statement, so define a prototype here
void usage(char *argv[]);

/// Check if a process is running
int check_process(int argc, char *argv[]);

/// Get information about a named process
int is_process_running(std::string & name, std::vector<int> & pid);

/// Check for a process lock file
int check_lock_file(int argc, char *argv[]);

/// Check for other files
int check_file(std::string executable, int type);

/// Remove a process lock file
//void remove_lock_file(std::string executable);
void remove_lock_file(std::string executable, std::string host = "localhost");

/// Definitions for process file types
enum {
  LOCK_FILE, 
  STOP_FILE, 
  PAUSE_FILE,
  DAYTIME_FILE
};



std::string & replaceAll(std::string & context, const std::string & from, const std::string & to);

//template <typename T>
bool is_float(std::string const& s, float * number, bool failIfLeftoverChars = true);
bool is_int(std::string const& s, int * number, bool failIfLeftoverChars = true);

std::string num_to_string(float value);

int shell_command(const std::string & command, std::string & output,
                  const std::string & mode = "r");

/// Define the common_info variable as an external variable, so that any files
/// that include this file will have access to the variable.
extern ROBO_common common_info;

# endif

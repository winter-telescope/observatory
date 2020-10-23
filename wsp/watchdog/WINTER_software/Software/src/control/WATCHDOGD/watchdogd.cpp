/**
 \file watchdogd.cpp
 \brief Main control program for data system.
 \details This is the server program that runs watchdogd.
 
 Copyright (c) 2009-2011 California Institute of Technology.
 \author Dr. Reed L. Riddle  riddle@caltech.edu
 \note
 
 <b>Version History</b>:
 \verbatim
 2009-11-10:  First complete version
 \endverbatim
 */

// Global include files
# include <cstdlib>
# include <iostream>
# include <fstream>
# include <boost/bind.hpp>
# include <boost/smart_ptr.hpp>
# include <boost/asio.hpp>
# include <boost/thread.hpp>
# include <getopt.h>

// Local include files
# include "common.h"
# include "daemon.h"
# include "watchdogd.h"
# include "watchdogd_server.h"
# include "communications.h"

// Macro statements
# define  N_PROGRAM_FLAGS   13

// Function declarations
void get_program_options(int argc, char **argv, bool &make_daemon, 
                         ROBO_port &port, bool &debug_flag);
void usage(int argc, char *argv[]);

// Global variables

/// Initialize the common_info container, which has basic information about
/// paths, identifications and other items that are used across the code base
/// in various places.  Easier to have this as a global variable than try to
/// embed it somewhere and pass it around.
ROBO_common common_info(COMMON_CONFIG_FILE, true);


/**************** usage ****************/
/**
 Usage statement for the program.
 \param [argv] Argument list for function, to get the executable name
 \note None.
 */
void usage(int argc, char *argv[])
{
  std::stringstream message;
  for (int i=0; i < argc; i++){
    message << argv[i] << " ";
  }
  
  // Print a message on how to use the program
  std::cout
  << "Error executing program, bad option or value entered" << std::endl
  << "  Executed command: " << message.str() << std::endl
  << "Program options:  " << argv[0] << std::endl
  << "  --verbose           Verbose output from program" << std::endl
  << "  --quiet             Quiet output from program" << std::endl
  << "  -d                  Make program into a daemon" << std::endl
  << "  -p                  Daemon connection port" << std::endl
  << "  -h                  Print this usage statement" << std::endl
  << "  --help" << std::endl << std::endl
  ;
  
  // Exit without an error flag.
  remove_lock_file(common_info.executable_name);
  exit(NO_ERROR);
}
/**************** usage ****************/


/**************** get_program_options ****************/
/**
 Gets the command line options and converts them to program settings for
 variables.
 \param [argc] Command line argument count
 \param [argv] Array of character strings for each command line argument
 \param [make_daemon] Flag to daemonize the program
 \note None.
 */
void get_program_options(int argc, char **argv, bool &make_daemon, 
                         ROBO_port &port, bool &debug_flag)
{
  ROBO_logfile log;
  log.filename = common_info.log_dir + common_info.executable_name + ".log";
  log.set_function("get_program_options");
  
  int retval;                         // Return value on command line check
  int program_flags[N_PROGRAM_FLAGS]; // Flags for command line options
//  char *temp[N_PROGRAM_FLAGS];        // Temp strings for variables
  
  // Default value settings
  program_flags[0] = 1;
  for (int i=1; i<N_PROGRAM_FLAGS; i++){
    program_flags[i] = 0;
//    temp[i] = '\0';
  }
  
  // Structure for command line options settings.  The columns are the long
  // option name, the number of arguments, whether to set a flag directly and
  // the output value.
  static struct option long_options[] =
  {
    // These options set a flag.
    {"verbose",       no_argument, &program_flags[0], 1},
    {"quiet",         no_argument, &program_flags[0], 0},
    // These options don't set a flag, we distinguish them by their indices
    {"debug",         no_argument,  0, 'g'},
    {"port",          required_argument, 0, 'p'},
    {"daemonize",     no_argument,       0, 'd'},
    {"help",          no_argument,       0, 'h'},
    {0, 0, 0, 0}
  };
  
  // Get the command line options
  while (1)
  {
    // getopt_long stores the option index here
    int option_index = 0;
    
    // Get the next option.  Note that options that have an argument are
    // followed by a : for the argument (one argument only).
    retval = getopt_long (argc, argv, "s:p:dgh?",
                          long_options, &option_index);
    
    // Detect the end of the options
    if (retval == -1)
      break;
    
    // Switch over the return value
    switch (retval)
    {
        // If this option set a flag, do nothing else now
      case 0:
        if (long_options[option_index].flag != 0)
          break;
        printf ("option %s", long_options[option_index].name);
        if (optarg)
          printf (" with arg %s", optarg);
        printf ("\n");
        break;
      case 'd':
      	make_daemon = true;
        program_flags[2] = 1;
        break;
        
      case 'p':
        port = (ROBO_port) atoi(optarg);
        program_flags[1] = 1;
        break;
        
      case 'g':
        debug_flag = true;
        program_flags[2] = 1;
        break;
        
        // Get a usage statement for help or unknown entries
      case 'h':
      case '?':
      default:
        usage(argc, argv);
    }
  }
  
  // If option arguments are left over, then write a usage statement
  if (optind < argc){
    usage(argc, argv);
  }
  
  
  // Instead of reporting --verbose and --quiet as they are encountered,
  // we report the final status resulting from them and set the flag.
  std::stringstream message("");  // A stream for messages to be logged
  if (program_flags[0] == 1){
    common_info.set_verbose(true);
    log.message << "verbose output flag is set";
    log.write(false);
  }
  else {
    common_info.set_verbose(false);
    log.message << "quiet output flag is set";
    log.write(false);
  }
}
/**************** get_program_options ****************/


/**************** main ****************/
/**
 The main routine.  This launches the routine to take a frame with the CCD39.
 \param [argc] Command line argument count
 \param [argv] Array of character strings for each command line argument
 \note None.
 */
int main(int argc, char *argv[])
{
  // Get the command line options for the program
  bool make_daemon = false;       // Flag to daemonize the program
  bool debug_flag = false;       // Flag to daemonize the program
  ROBO_port port = ROBO_PORT_WATCHDOGD;  // The connection port to the daemon

  // Set the common executable name to the name used to launch this program.
  // This makes sure error messages identify this routine, in case it is
  // compiled with a different name than usual.
  std::vector<std::string> tokens;  // Temporary tokens
  std::string bob(argv[0]);
  Tokenize(bob, tokens, "/");
  common_info.executable_name = tokens[tokens.size()-1];

  // Get the program options
  get_program_options(argc, argv, make_daemon, port, debug_flag);
  
  // Check if the process is already running, exit if it is.  Don't do this if
  // it's running through a debugger, that causes this to fail.
  if (debug_flag == false){
    if (check_process(argc, argv) != NO_ERROR){
      exit(ERROR);
    }
  }
  
  // Set the function name
  std::string function(common_info.executable_name);
  
  try
  {
    
    // Make the program into a daemon if flagged
    if (make_daemon == true){
      ROBO::daemonize();
      common_info.set_verbose(false);
    }
    
    // Create the server object and run the server
    ROBO_watchdog::Server server(port, function);
    server.run();
    
  }
  // Catch standard exceptions and print out what they are, and then exit.  The
  // rest of the ROBO functions should catch local errors, this should only be
  // called if memory or other errors come up.
  catch (std::exception & e){
    ROBO_logfile log;
    log.filename = common_info.log_dir + COMMON_LOGFILE_NAME + ".log";
    log.set_function(function);
    log.message << "Program execution failure, standard exception: " 
    << e.what() << ".\n";
    log.write(true);
    
    // Remove the lock file
    remove_lock_file(common_info.executable_name);
    exit(FATAL_ERROR);
  }
  // Catch any other errors that get through and flag that an unknown error
  // occurred and then exit.  This should never happen.....
  catch (...){
    ROBO_logfile log;
    log.filename = common_info.log_dir + COMMON_LOGFILE_NAME + ".log";
    log.set_function(function);
    log.message << "Program execution failure...unknown cause of failure.\n";
    log.write(true);
    
    // Remove the lock file
    remove_lock_file(common_info.executable_name);
    exit(FATAL_ERROR);
  }
  
  // Remove the lock file
  remove_lock_file(common_info.executable_name);
  
  return 0;
}
/**************** main ****************/

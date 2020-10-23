/**
 \file messaged_test.cpp
 \brief Test control program for system command of the message daemon.
 \details Tests the functionality and control of the message system through the
 messaged interface.
 
 Copyright (c) 2009-2022 California Institute of Technology.
 \author Dr. Reed L. Riddle  riddle@caltech.edu
 \note
 
*/

// Global include files
# include <iostream>
# include <getopt.h>

// Local include files
# include "common.h"
# include "daemon.h"
# include "watchdogd.h"
# include "watchdogd_client.h"

// Macro statements
# define  N_PROGRAM_FLAGS   13

// Function declarations
void get_program_options(int argc, char **argv);
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
  << "  -g                  Use when running a debugger (gdb)" << std::endl
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
void get_program_options(int argc, char **argv, bool & debug_flag)
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
    retval = getopt_long (argc, argv, "s:gh?",
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
  bool debug_flag = false;       // Flag to daemonize the program
  
  // Set the common executable name to the name used to launch this program.
  // This makes sure error messages identify this routine, in case it is
  // compiled with a different name than usual.
  std::vector<std::string> tokens;  // Temporary tokens
  std::string bob(argv[0]);
  Tokenize(bob, tokens, "/");
  common_info.executable_name = tokens[tokens.size()-1];

  // Get the program options
  get_program_options(argc, argv, debug_flag);
  
  // Check if the process is already running, exit if it is.  Don't do this if
  // it's running through a debugger, that causes this to fail.
  if (debug_flag == false){
    if (check_process(argc, argv) != NO_ERROR){
      exit(ERROR);
    }
  }
  
  // Set the function name
  std::string function(common_info.executable_name);
  std::stringstream message;
  

  // Outside try statement for overall error catching
  try {

    
    char host[20], port[20];
    sprintf(host, "localhost");
//    sprintf(host, "192.168.1.3");
    sprintf(port, "%d", ROBO_PORT_WATCHDOGD);

    ROBO_watchdog::Client client(host, port);
    
  	int n = 1;
    while (n != 0){
      
      if (client.get_server_shutdown_flag() == true){
        n = 0;
        continue;
      }

      std::cout << "Main Menu" << std::endl;
      std::cout << "====================" << std::endl;
      std::cout << "a. Start watchdog operations" << std::endl;
      std::cout << "b. Pause watchdog operations" << std::endl;
      std::cout << "" << std::endl;
      std::cout << "x. Exit" << std::endl;
      std::cout << "0. Shutdown all daemons and exit" << std::endl;
      std::cout << "====================" << std::endl;
      std::cout << "Choice?:: ";

      char input[STRING_LINE_LENGTH];
      std::cin.getline(input, STRING_LINE_LENGTH);
    	char choice;
  		choice = input[0];
      std::stringstream request;

      if (client.get_server_shutdown_flag() == true){
        n = 0;
        continue;
      }

  		switch(choice){
          
        case 'a':
        {
          request << ROBO_watchdog::START_WATCHDOG;
          client.send_message(request);
          break;
        }
          
        case 'b':
        {
          request << ROBO_watchdog::PAUSE_WATCHDOG;
          client.send_message(request);
          break;
        }
          
          
        case 'x':
          client.set_client_shutdown_flag(true);
          timeout();
	  			n = 0;
          break;
        case '0':
          request << ROBO_watchdog::SHUTDOWN;
          client.send_message(request);
          n = 0;
          client.set_server_shutdown_flag(true);
          client.set_client_shutdown_flag(true);
          timeout();
          break;
	  		default:
	  			std::cout << "!Invalid Option!" << std::endl << std::endl;
          
      }
    }
  }
  // Catch standard exceptions and print out what they are, and then exit.  The
  // rest of the Robo functions should catch local errors, this should only be
  // called if memory or other errors come up.
  catch (std::exception & e){
    message << "Program execution failure, standard exception: "
    << e.what() << ".\n";
    common_info.log.write(function, true, message.str());
    
    // Remove the lock file
    remove_lock_file(common_info.executable_name);
    exit(FATAL_ERROR);
  }
  // Catch any other errors that get through and flag that an unknown error
  // occurred and then exit.  This should never happen.....
  catch (...){
    message << "Program execution failure...unknown cause of failure.\n";
    common_info.log.write(function, true, message.str());
    
    // Remove the lock file
    remove_lock_file(common_info.executable_name);
    exit(FATAL_ERROR);
  }
  
  // Remove the lock file
  remove_lock_file(common_info.executable_name);
  
  return 0;
}
/**************** main ****************/

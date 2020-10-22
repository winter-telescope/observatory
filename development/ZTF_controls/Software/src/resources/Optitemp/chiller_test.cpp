/**
 \file chiller_test.cpp
 \brief Test software for the PI chiller hardware interfaces.
 \details This software tests the PI chiller hardware interface functions.
 
 Copyright (c) 2009-2015 California Institute of Technology.
 \author Dr. Reed L. Riddle  riddle@caltech.edu
 \note
 */

#  include <iostream>

# include "chiller.h"

// Global variables

/// Initialize the common_info container, which has basic information about
/// paths, identifications and other items that are used across the code base
/// in various places.  Easier to have this as a global variable than try to
/// embed it somewhere and pass it around.
ROBO_common common_info(COMMON_CONFIG_FILE, true);


int main(int argc, char* argv[])
{
  // Check if the process is already running, exit if it is
  if (check_process(argc, argv) != NO_ERROR){
    exit(ERROR);
  }

  // Set the function name
  std::string function(common_info.executable_name);
  
  // Create the class container
  Optitemp::Chiller_control chiller;
  
  // Outside try statement for overall error catching
  try {
    
    bool open = false;
    bool quit = false;
    while (quit == false){
      
      // Show menu options
      std::cout << "        Menu" << std::endl;
      std::cout << "====================" << std::endl;
      std::cout << "a. Open connection" << std::endl;
      std::cout << "b. Close connection" << std::endl;
      std::cout << "r. Read chiller data" << std::endl;
      std::cout << "w. Write temperature setpoint" << std::endl;
      std::cout << std::endl;
      std::cout << "x.     Exit" << std::endl;
      std::cout << "====================" << std::endl;
      std::cout << "Choice?::";
 
      // Get the input
      char input[STRING_LINE_LENGTH];
      std::cin.getline(input, STRING_LINE_LENGTH);
      char choice;
      choice = input[0];
      
      std::stringstream request;
      int response = BAD_VALUE;
      bool reply = true;
      std::string output;
      std::string ss;  // temporary.

      // Switch over the menu options
      switch(choice){
        
        // Open the connection
        case 'a':
          response = chiller.control(ROBO_sensor::OPEN_CONNECTION, "", output);
          if (response == NO_ERROR){
            open = true;
          }
          else{
            std::cout << __FILE__ << ":  Exiting program." << std::endl;
            quit = true;
            reply=false;
          }
          break;
          
          // Close the connection
        case 'b':
          response = chiller.control(ROBO_sensor::CLOSE_CONNECTION, "", output);
          reply=false;
          break;
          
        case 'w':
          std::cout << "Enter temperature setpoint (0-30): ";
          std::getline(std::cin, ss);
          request << ss;
          response = chiller.control(ROBO_sensor::SET_CHILLER_TEMPERATURE,
                                     request.str(), output);
          reply=false;
          break;
          
          // Absolute move in y
        case 'r':
          request << "r ";
          response = chiller.control(ROBO_sensor::READ_DATA, request.str(), 
                                     output);
          std::cout << "output = " << output << std::endl;
          reply=true;
          break;
          
        case 'x':
          std::cout << "Closing connection" << std::endl;
          if (open == true){
            response = chiller.control(ROBO_sensor::CLOSE_CONNECTION, "", 
                                       output);
          }
          reply=false;
          quit = true;
          break;
          
          // Anything else is a bad command
        default:
          std::cout << "!Invalid Option!" << std::endl << std::endl;
          reply = false;
      }
      
      // Print the output from the controller
      if (reply == true){
        std::cout << "Response: " << response << " output: " << output
            << common_info.erreg.get_code(response) << std::endl;
      }
    }
  }
  
  // Catch standard exceptions and print out what they are, and then exit.  The
  // rest of the ROBO functions should catch local errors, this should only be
  // called if memory or other errors come up.
  catch (std::exception & e){
    ROBO_logfile log;
    log.filename = common_info.log_dir + COMMON_LOGFILE_NAME + ".log";
    log.set_function(function);
    log.message << "Program execution failure, standard exception: " << e.what() << ".\n";
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

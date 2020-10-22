/**
 \file file_ops.cpp
 \brief Reading files and configuration files.
 \details Configuration file handling.  Parameters from config files and
 functions to interface with config files are contained here.  Config files
 follow the Bash shell file format for variables.

 Copyright (c) 2009-2011 California Institute of Technology.
 \author Dr. Reed L. Riddle  riddle@caltech.edu
 \note Configuration file format sample:
 \code
 # testing config file

 NAME = "NPS 1"
 N_PLUGS=8
 IP_ADDRESS="192.168.1.10"       # IP address for the NPS
 CONNECTION_TYPE=NETWORK         # Network connection type
 \endcode


 <b>Version History</b>:
 \verbatim
 2009-07-17:  First complete version
 2010-02-25:  Updated error control system to new standard
 \endverbatim
 */

// System include files
# include <iostream>
# include <cstring>
# include <dirent.h>
# include <boost/thread.hpp>
# include <boost/interprocess/sync/file_lock.hpp>
# include <boost/interprocess/sync/scoped_lock.hpp>

// Local include files
# include "file_ops.h"


/**************** ROBO_file::open_file_read ****************/
/**
 Opens files in the ROBO system.  Set the variables robo_file.filename (a
 character string)  *before* calling this function.  This defaults to  open at
 the beginning of the file in read only mode.  Error codes and messages are
 returned on errors accessing the file, success message returned if there are
 no problems.
 \param [robo_file] A standard ROBO_file class variable.
 \note none
 */
int ROBO_file::open_file_read(ROBO_file & robo_file)
{
  // Return an error if the file name is 0 length
  if (robo_file.filename.length() < 1){
    return (ERROR_FILE_NAME_EMPTY);
//    return (robo_file.error.code = ERROR_FILE_NAME_EMPTY);
  }

  // Return an error if the file does not exist in the system
  if (stat(robo_file.filename.c_str(), &robo_file.fileinfo) != 0){
    return (ERROR_FILE_NO_EXIST);
//    return (robo_file.error.code = ERROR_FILE_NO_EXIST);
  }

  // Open the file, and check that it opened properly.
  robo_file.filestream.open(robo_file.filename.c_str(), std::ios::in);
  if (robo_file.filestream.good() == false){
    return (ERROR_FILE_OPEN);
//    return (robo_file.error.code = ERROR_FILE_OPEN);
  }

  // Get the time the file was opened
  this->file_open_time = time(NULL);

  // Everything worked, so flag NO_ERROR.
//  robo_file.error.code = NO_ERROR;
  return (NO_ERROR);
//  return (robo_file.error.code = NO_ERROR);
}
/**************** ROBO_file::open_file_read ****************/


/**************** ROBO_file::open_file_read ****************/
/**
 Opens files in the ROBO system.  Set the variables robo_file.filename (a
 character string)  *before* calling this function.  This defaults to  open at
 the beginning of the file in read only mode.  Error codes and messages are
 returned on errors accessing the file, success message returned if there are
 no problems.
 \param [robo_file] A standard ROBO_file class variable.
 \note none
 */
int ROBO_file::open_file_read(std::string filename)
{
  this->filename = filename;
  // Return an error if the file name is 0 length
  if (this->filename.length() < 1){
    return (ERROR_FILE_NAME_EMPTY);
//    return (robo_file.error.code = ERROR_FILE_NAME_EMPTY);
  }

  // Return an error if the file does not exist in the system
  if (stat(this->filename.c_str(), &this->fileinfo) != 0){
    return (ERROR_FILE_NO_EXIST);
//    return (robo_file.error.code = ERROR_FILE_NO_EXIST);
  }

  // Open the file, and check that it opened properly.
  this->filestream.open(this->filename.c_str(), std::ios::in);
  if (this->filestream.good() == false){
    return (ERROR_FILE_OPEN);
//    return (robo_file.error.code = ERROR_FILE_OPEN);
  }

  // Get the time the file was opened
  this->file_open_time = time(NULL);

  // Everything worked, so flag NO_ERROR.
//  robo_file.error.code = NO_ERROR;
  return (NO_ERROR);
//  return (robo_file.error.code = NO_ERROR);
}
/**************** ROBO_file::open_file_read ****************/


/**************** ROBO_file::open_file ****************/
/**
 Opens files in the ROBO system.  Set the variables robo_file.filename (a
 character string)  *before* calling this function.  This defaults to  open at
 the beginning of the file in read only mode.  Error codes and messages are
 returned on errors accessing the file, success message returned if there are
 no problems.
 \param [robo_file] A standard ROBO_file class variable.
 \param [mode] The mode to use when opening the file (read, write, append, etc)
 \note none
 */
int ROBO_file::open_file(ROBO_FILE_MODE mode)
{
//  std::cout << "a " << std::flush; 
//  std::cout << "filename " << this->filename << " " << std::flush; 
//  std::cout << "a " << std::flush; 
//  std::cout << "length " << this->filename.length() << " " << std::flush; 
  // Return an error if the file name is 0 length
  if (this->filename.length() < 1){
    return (ERROR_FILE_NAME_EMPTY);
  }
//  std::cout << "b " << mode << " " << std::flush; 

  // Return an error if the file does not exist in the system
  if (stat(this->filename.c_str(), &this->fileinfo) != 0 && mode == OPEN_FILE_READ){
    return (ERROR_FILE_NO_EXIST);
  }
//  std::cout << "c " << std::flush; 

  // Get the file mode for opening the file
  std::ios::openmode open_mode;
  switch (mode){
  case OPEN_FILE_READ:
  	open_mode = std::ios::in;
  	break;
  case OPEN_FILE_WRITE:
  	open_mode = std::ios::out;
  	break;
  case OPEN_FILE_REWRITE:
  	open_mode = std::ios::out|std::ios::trunc;
  	break;
  case OPEN_FILE_APPEND:
  	open_mode = std::ios::out|std::ios::app|std::ios::ate;
  	break;
  default:
    return (ERROR_FILE_OPEN);
  }
//  std::cout << "d " << open_mode << " " << std::flush; 

  // Open the file, and check that it opened properly.
  this->filestream.open(this->filename.c_str(), open_mode);
//  std::cout << "z " << std::flush; 
  if (this->filestream.good() == false){
    return (ERROR_FILE_OPEN);
  }
//  std::cout << "e " << std::flush; 

  // Get the time the file was opened
  this->file_open_time = time(NULL);
//  std::cout << "f " << std::endl << std::flush; 

  // Everything worked, so flag NO_ERROR.
  return (NO_ERROR);
}
/**************** ROBO_file::open_file ****************/


/**************** ROBO_file::close_file ****************/
/**
 Closes files in the ROBO system.  Error codes and messages are
 returned on errors accessing the file, success message returned if there are
 no problems.
 \note none
 */
int ROBO_file::close_file()
{
  // Close the file stream if it is open
  if (this->filestream.is_open() == true){
    this->filestream.flush();
    this->filestream.close();
  }
  // It's an error if the file stream is not open
  else {
    return (ERROR_FILE_CLOSE);
  }

  // Everything worked, so flag NO_ERROR.
  return (NO_ERROR);
}
/**************** ROBO_file::close_file ****************/


/**************** ROBO_file::check_time ****************/
bool ROBO_file::modified()
{
//std::cout << "  a " << this->filename.c_str() << std::endl << std::flush;
  if (stat(this->filename.c_str(), &this->fileinfo) != 0){
    return (true);
  }
//  std::cout << "  b" << std::endl << std::flush;

  
//  printf("mod: %f open: %f diff: %f\n", this->fileinfo.st_mtime, 
//  this->file_open_time, this->fileinfo.st_mtime - this->file_open_time);

  if (this->fileinfo.st_mtime > this->file_open_time){
    return (true);
  }
  
  return (false);
}
/**************** ROBO_file::check_time ****************/


/**************** ROBO_config::read_config ****************/
/**
 Reads configuration files.  Configuration files must be in the standard Bash
 script file format for variables, with comments set behind a #.  Gets variable
 and parameter pairs, and the number of variables, from the file.

 Configuration file format sample:
 \verbatim
 # testing config file

 NAME = "NPS 1"
 N_PLUGS=8
 IP_ADDRESS="192.168.1.10"       # IP address for the NPS
 CONNECTION_TYPE=NETWORK         # Network connection type
 \endverbatim
 \param [config] A standard Config class variable, which inherits the properties
 of ROBO_file.
 \note none
 */
//int ROBO_config::read_config(ROBO_config & config)
int ROBO_config::read_config()
{
  // Open the configuration file for reading, return on an error
  int err;
  if ((err = this->open_file(OPEN_FILE_READ)) != NO_ERROR){
    return (err);
  }

  // We are grabbing two elements from a line in the file, of the format
  // "VARIABLE=VALUE".  There may be comments, on a line by themselves or after
  // the statement to set the variable, and there may be blank lines.  This
  // while loop handles all of those options.

  std::string line;     // Temporary string to read file lines into
  size_t index1, index2; // String indexing variables
  int i = 0;            // Counts the number of parameter lines read from file

  // Clear the vectors to load the new information from the config file
  this->vars.clear();
  this->params.clear();
  
  // Get a line from the file as long as they are available
  while (getline(this->filestream, line)) {
    // Lines with variables have to be more than 2 characters long for there to
    // be a variable statement on them.
    if (line.length() > 2){

      // If the first character is a #, ignore it.
      if (line.at(0) == '#'){
        continue;
      }

      // At this point, all that is left to check are VARIABLE=VALUE pairs, plus
      // possibly comments tagged on the end of the line.
      else {
        // Find the = delimiter in the line
        index1 = line.find_first_of("=");
        // Put the variable name into the vector holding the names
        this->vars.push_back(line.substr(0, index1));

        // Look for configuration parameters in a vector format (i.e. surrounded
        // by parentheses).
        if ((index2 = line.find_last_of("(")) == std::string::npos){
          
          // Look for quotes around the variable value.  Quotes are required for
          // variables that have spaces in them (name strings for example).
          if ((index2 = line.find_last_of("\"")) == std::string::npos){
            // No quote strings, check for a comment at the end of the line
            if ((index2 = line.find_first_of("#")) == std::string::npos){
              // No comment, so get the index of the end of the comment
              // and set the value into the vector.
              index2 = line.find_first_of("\t\0");
              this->params.push_back(line.substr(index1+1, index2-index1));
            }
            
            // There is a comment, get the index and put the value (note the
            // different index value for the line substring).
            else {
              index2 = line.find_first_of(" \t#");
              this->params.push_back(line.substr(index1+1, index2-index1-1));
            }
          }
          
          // Quotes change the substring index again, so find the position of the
          // two quote characters in the string and get the value.
          else {
            index1 = line.find_first_of("\"") + 1;
            index2 = line.find_last_of("\"");
            this->params.push_back(line.substr(index1, index2-index1));
          }
        }

        // A vector was found, so strip the part between the parentheses out and
        // save it
        else {
          index1 = line.find_first_of("(") + 1;
          index2 = line.find_last_of(")");
          this->params.push_back(line.substr(index1, index2-index1));
        }
      }
    }

    // For lines of less than 2 characters, we just loop to the next line
    else {
      continue;
    }

    // Increment the number of values read successfully
    i++;
  }

  // Set the number of elements to the number of elements read
  this->n_elements = i;
  // Close the file stream
  this->close_file();

  // Flag that there were no errors.
  return (NO_ERROR);
}
/**************** ROBO_config::read_config ****************/


/**************** Config::read_config ****************/
/**
 Reads configuration files.  Configuration files must be in the standard Bash
 script file format for variables, with comments set behind a #.  Gets variable
 and parameter pairs, and the number of variables, from the file.

 Configuration file format sample:
 \verbatim
 # testing config file

 NAME = "NPS 1"
 N_PLUGS=8
 IP_ADDRESS="192.168.1.10"       # IP address for the NPS
 CONNECTION_TYPE=NETWORK         # Network connection type
 \endverbatim
 \param [config] A standard Config class variable, which inherits the properties
 of ROBO_file.
 \note none
 */
int Config::read_config(Config & config)
{
  // Open the configuration file for reading, return on an error
  int err;
	if ((err = config.open_file_read(config)) != NO_ERROR){
    return (err);
  }

  // We are grabbing two elements from a line in the file, of the format
  // "VARIABLE=VALUE".  There may be comments, on a line by themselves or after
  // the statement to set the variable, and there may be blank lines.  This
  // while loop handles all of those options.

  std::string line;     // Temporary string to read file lines into
  size_t index1, index2; // String indexing variables
  int i = 0;            // Counts the number of parameter lines read from file

  // Clear the vectors to load the new information from the config file
  this->vars.clear();
  this->params.clear();
  
  // Get a line from the file as long as they are available
  while (getline(config.filestream, line)) {
    // Lines with variables have to be more than 2 characters long for there to
    // be a variable statement on them.
    if (line.length() > 2){

      // If the first character is a #, ignore it.
      if (line.at(0) == '#'){
        continue;
      }

      // At this point, all that is left to check are VARIABLE=VALUE pairs, plus
      // possibly comments tagged on the end of the line.
      else {
        // Find the = delimiter in the line
        index1 = line.find_first_of("=");
        // Put the variable name into the vector holding the names
        config.vars.push_back(line.substr(0, index1));

        // Look for configuration parameters in a vector format (i.e. surrounded
        // by parentheses).
        if ((index2 = line.find_last_of("(")) == std::string::npos){
          
          // Look for quotes around the variable value.  Quotes are required for
          // variables that have spaces in them (name strings for example).
          if ((index2 = line.find_last_of("\"")) == std::string::npos){
            // No quote strings, check for a comment at the end of the line
            if ((index2 = line.find_first_of("#")) == std::string::npos){
              // No comment, so get the index of the end of the comment
              // and set the value into the vector.
              index2 = line.find_first_of("\t\0");
              config.params.push_back(line.substr(index1+1, index2-index1));
            }
            
            // There is a comment, get the index and put the value (note the
            // different index value for the line substring).
            else {
              index2 = line.find_first_of(" \t#");
              config.params.push_back(line.substr(index1+1, index2-index1-1));
            }
          }
          
          // Quotes change the substring index again, so find the position of the
          // two quote characters in the string and get the value.
          else {
            index1 = line.find_first_of("\"") + 1;
            index2 = line.find_last_of("\"");
            config.params.push_back(line.substr(index1, index2-index1));
          }
        }

        // A vector was found, so strip the part between the parentheses out and
        // save it
        else {
          index1 = line.find_first_of("(") + 1;
          index2 = line.find_last_of(")");
          config.params.push_back(line.substr(index1, index2-index1));
        }
      }
    }

    // For lines of less than 2 characters, we just loop to the next line
    else {
      continue;
    }

    // Increment the number of values read successfully
    i++;
  }

  // Set the number of elements to the number of elements read
  config.n_elements = i;
  // Close the file stream
  config.close_file();
  //  config.filestream.close();
  // Flag that there were no errors.
//  config.error.code = NO_ERROR;
  return (NO_ERROR);
//  return (config.error.code);
}
/**************** Config::read_config ****************/


/**************** ROBO_error::Handle_error ****************/
/**
 Handles any general errors from the ROBO system. These are not the resource
 specific ones, but instead errors that can happen across the entire system.
 Things like file operation errors or allocation errors should be handled
 in here.  Error codes in error.h.
 \param [error] Class containing information about the error to handle
 \note none
 */
int handle_error_message(int error_code, std::string param,
                         std::string & outmsg)
{
  // If the error code is outside the error space (100-999), then it should be a
  // basic system error, so we throw again to have the system deal with it.
  if (error_code < ROBO_ERROR_SPACE){
    throw;
  }
  
  // Initialize fatal_error flag
  int fatal_error = NO_ERROR;
  
  // Clear the message string so we can use it for the error message
  std::stringstream message;
  message << "error code: " << error_code << " ";
  
  // Switch on the error code
  switch(error_code){
      // Empty file name in a file open call
    case (ERROR_FILE_NAME_EMPTY):
      message << "no file name entered!";
      fatal_error = FATAL_ERROR;
      break;
      // The file that was called does not exist at the specified location
    case (ERROR_FILE_NO_EXIST):
      message << "file \"" << param << "\" does not exist!";
      fatal_error = FATAL_ERROR;
      break;
      // The file could not be opened
    case (ERROR_FILE_OPEN):
      message << "error opening file \"" << param << "\"!";
      fatal_error = FATAL_ERROR;
      break;
      // A loop reached the maximum attempts to do something
    case (ERROR_MAX_ATTEMPTS_FAIL):
      message << param << " exceeded maximum attempts, shutting the program down!";
      break;
      // Blank parameter in a config file
    case (ERROR_PARAM_BLANK):
      message << "common configuration file variable " << param
              << " is blank, using default.";
      break;
      // A directory error that can't be fixed
    case (ERROR_DIRECTORY):
      message << "directory " << param << " is missing and cannot be created.";
      break;
      // A system directory error that can't be fixed
    case (ERROR_SYSTEM_DIRECTORY):
      message << "Fatal error detected, exiting!  Unable to create "
              << " system directory " << param;
      fatal_error = FATAL_ERROR;
      break;
      
    case ERROR_CONTROL_CAUGHT:
      message << "Error caught, error control in process, incrementing "
              << "counter to " << param << " and returning";
      break;
      
    case ERROR_UNKNOWN:
      message << "Unknown error code (" << error_code << "), function " << param;
      break;
      
    case ERROR_FATAL:
      message << "Fatal error encountered, terminating program!";
      break;
      
      // Some other error code, which really should not happen!
    default:
      message << "Unspecified error code.";
  }
  
  // Write the error string to the log file and return the fatal_error code
  outmsg = message.str();
  return (fatal_error);
}
/**************** ROBO_error::Handle_error ****************/


///**************** directory_name_check ****************/
///**
// Checks the directory to make sure that the string passed points to a directory
// on the system.  Includes an original directory that is used as a default.  If
// the directory does not exist, this attempts to create it.
// \param [original] The variable for the original directory
// \param [config_name] The name of the configuration file variable for the directory
// \param [new_directory] The new directory value
// \note none
// */
//std::string directory_name_check(std::string original, std::string config_name,
//                                 std::string new_directory)
//{
//  std::string function("directory_name_check");  // Function name
//  std::string test_string;  // String constructed to test directory
//  char test_char;           // Character to test directory
//  ROBO_error error;       // Error class created to log errors
//  error.type = CLASS_ROBO_FILE;
//  error.log_name = common_info.log_name;
//  
//  // If the new directory string is empty, flag that and set the test string to
//  // the original directory that is passed in
//  if (new_directory.length() < 1){
//    error.code = ERROR_PARAM_BLANK;
//    error.params[0] << config_name.c_str();
//    error.Handle_error(error);
//    test_string = original;
//  }
//  // Do some tests on the new_directory string to set the directory path
//  else {
//    // If the directory is in the current directory, set it
//    if (new_directory.compare(0, 2, "./") == 0){
//      test_string = new_directory;
//    }
//    // If the new directory does not lead with a /, then we presume it is made
//    // in the home directory root level and set the string up for it
//    else if ((test_char = new_directory[0]) != '/'){
//      test_string = common_info.home_dir + '/' + new_directory;
//    }
//    // Otherwise, we take the string verbatim
//    else {
//      test_string = new_directory;
//    }
//  }
//  
//  // Add a / to the end of the string, so we don't make an error somewhere
//  // by assuming a / is present at the end of the string and muck up a directory
//  // path
//  if (test_string[test_string.length()-1] != '/'){
//    test_string = test_string + '/';
//  }
//  
//  // Make sure the directory exists
//  DIR *dirp;    // Pointer to the directory
//  // Try to open the new directory; if it does not exist then the pointer is NULL
//  if ((dirp = opendir(test_string.c_str())) == NULL){
//    // If it did not exist, then try to make it.  If it cannot be made, then
//    // flag an error and return a string of ""
//    if ((mkdir(test_string.c_str(), S_IRWXU | S_IRWXG | S_IROTH | S_IXOTH)) != 0){
//      //    if ((mkdir(test_string.c_str(), 0775)) != 0){
//      error.code = ERROR_DIRECTORY;
//      error.params[0] << config_name.c_str();
//      error.Handle_error(error);
//      return ("");
//    }
//    // If the directory was made, send a message about that to the log
//    else {
//      ROBO_logfile log;
//      log.filename = common_info.log_dir + COMMON_LOGFILE_NAME + ".log";
//      //      log.set_function("directory_name_check");
//      //      log.open_file(OPEN_FILE_APPEND);
//      std::stringstream message;
//      message << "Directory " << test_string.c_str()
//      << " does not exist, created it.";
//      log.write(function, true, message.str());
//    }
//  }
//  // If the directory already existed, close it.
//  else {
//    closedir(dirp);
//  }
//  
//  // Return the string with the new directory path when the tests are successful
//  return (test_string);
//}
///**************** directory_name_check ****************/


/**************** directory_check ****************/
/**
 Checks the directory to make sure that the string passed points to a directory
 on the system.  Includes an original directory that is used as a default.  If
 the directory does not exist, this attempts to create it.
 \param [original] The variable for the original directory
 \param [config_name] The name of the configuration file variable for the directory
 \param [new_directory] The new directory value
 \note none
 */
bool directory_check(std::string directory)
{
//  ROBO_error error;       // Error class created to log errors
//  error.type = CLASS_ROBO_FILE;
//  error.log_name = common_info.log_name;
  
  ROBO_logfile log;
  log.set_function("directory_check");
  std::stringstream dir;
  dir << getenv("HOME") << "/Software/Logs/" << COMMON_LOGFILE_NAME << ".log";
  log.filename = dir.str();

  // Make sure the directory exists
  DIR *dirp;    // Pointer to the directory
  // Try to open the new directory; if it does not exist then the pointer is NULL
  if ((dirp = opendir(directory.c_str())) == NULL){
    // If it did not exist, then try to make it.  If it cannot be made, then
    // flag an error and return a string of ""
    if ((mkdir(directory.c_str(), S_IRUSR | S_IWUSR | S_IXUSR)) != 0){
//      error.code = ERROR_DIRECTORY;
//      error.params[0] << directory.c_str();
//      error.Handle_error(error);
    	std::string message;
      handle_error_message(ERROR_DIRECTORY, directory.c_str(), message);
      log.write(true);
     return false;
    }
    // If the directory was made, send a message about that to the log
    else {
//      ROBO_logfile log;
//      log.set_function("directory_check");
//      log.filename = common_info.log_dir + COMMON_LOGFILE_NAME + ".log";
      //      log.open_file(OPEN_FILE_APPEND);
      log.message << "Directory " << directory.c_str()
      << " does not exist, created it.";
      log.write(true);
    }
  }
  // If the directory already existed, close it.
  else {
    closedir(dirp);
  }
  
  return true;
}
/**************** directory_check ****************/



///**************** directory_name_check ****************/
///**
// Checks the directory to make sure that the string passed points to a directory
// on the system.  Includes an original directory that is used as a default.  If
// the directory does not exist, this attempts to create it.
// \param [original] The variable for the original directory
// \param [config_name] The name of the configuration file variable for the directory
// \param [new_directory] The new directory value
// \note none
// */
//bool directory_check(std::string directory)
//{
//  ROBO_error error;       // Error class created to log errors
//	error.type = CLASS_ROBO_FILE;
//	error.log_name = common_info.log_name;
//
//  // Make sure the directory exists
//  DIR *dirp;    // Pointer to the directory
//  // Try to open the new directory; if it does not exist then the pointer is NULL
//  if ((dirp = opendir(directory.c_str())) == NULL){
//    // If it did not exist, then try to make it.  If it cannot be made, then
//    // flag an error and return a string of ""
//    if ((mkdir(directory.c_str(), S_IRUSR | S_IWUSR | S_IXUSR)) != 0){
//      error.code = ERROR_DIRECTORY;
//      error.params[0] << directory.c_str();
//      error.Handle_error(error);
//      return false;
//    }
//    // If the directory was made, send a message about that to the log
//    else {
//      ROBO_logfile log;
//      log.set_function("directory_check");
//      log.filename = common_info.log_dir + COMMON_LOGFILE_NAME + ".log";
////      log.open_file(OPEN_FILE_APPEND);
//      log.message << "Directory " << directory.c_str()
//									<< " does not exist, created it.";
//      log.write(true);
//    }
//  }
//  // If the directory already existed, close it.
//  else {
//    closedir(dirp);
//  }
//
//  return true;
//}
///**************** directory_name_check ****************/
//
//
/**************** ROBO_logfile::write ****************/
/**
 Create a thread to write log entries to the log file
 \param [err] Flag if the message is an error message or just a log entry
 \note none
 */
void ROBO_logfile::write(int err)
{
  try {
/*  std::string msg;      // Temp message string
  std::string func;     // Temp string for function name
  unsigned int counter; // Counter to track thread order

//  std::cout << ", write_1: " << this->function.str() << " " 
//          << print_bool(err, PRINT_BOOL_TRUE_FALSE) << " " << this->message.str()
//          << " " << this->thread_count << std::endl << std::flush;
  // Create a thread to write the data.  This copies the data and timestamp
  // information into the temporary variables and creates a thread to
  // write the data.  Note that thread_count is incremented after the thread
  // is created.
//  this->log_thread = boost::thread(&ROBO_logfile::write_log, this,
//                                    msg = this->message.str(), err,
//                                    func = this->function.str());
  this->log_thread = boost::thread(&ROBO_logfile::write_log, this,
                                    msg = this->message.str(), err,
                                    func = this->function.str(),
                                    counter = this->thread_count++);
//  counter = this->thread_count);
  this->log_thread.detach();
*/
  this->write_log2(this->message.str(), err, this->function.str());

  
  // Clear the message string
  this->message.str("");
  }
  catch (boost::thread_resource_error error){
    this->thread_exception++;
    std::cout << "   Caught ROBO_logfile thread resource error: " 
        << this->thread_exception << ", write_1: " << this->function.str() << " " 
        << print_bool(err, PRINT_BOOL_TRUE_FALSE) << " " << this->message.str()
        << std::endl << std::flush;
//    << " " << this->thread_count << std::endl << std::flush;
  }
}
/**************** ROBO_logfile::write ****************/


/**************** ROBO_logfile::write ****************/
/**
 Create a thread to write log entries to the log file
 \param [err] Flag if the message is an error message or just a log entry
 \note none
 */
void ROBO_logfile::write(std::string func, int err, std::string message)
{
  try {
//    std::string msg;      // Temp message string
//    std::string func;     // Temp string for function name
    unsigned int counter; // Counter to track thread order

  //  std::cout << ", write_0: " << this->function.str() << " " 
  //          << print_bool(err, PRINT_BOOL_TRUE_FALSE) << " " << this->message.str()
  //          << " " << this->thread_count << std::endl << std::flush;
    // Create a thread to write the data.  This copies the data and timestamp
    // information into the temporary variables and creates a thread to
    // write the data.  Note that thread_count is incremented after the thread
    // is created.
  //  this->log_thread = boost::thread(&ROBO_logfile::write_log, this,
  //                                    message, err, function);
//    this->log_thread = boost::thread(&ROBO_logfile::write_log, this,
//                                      message, err, function,
//                                      counter = this->thread_count++);
//    this->log_thread.detach();


//    this->log_thread = boost::thread(&ROBO_logfile::write_log2, this,
//                                          message, err, function);

//    this->log_thread.detach();

//    boost::mutex::scoped_lock lock(this->log_mutex);
//    this->thread_count++;
//    lock.unlock();
    
    //    this->log_thread.detach();
    
    this->write_log2(message, err, func);
    
    // Clear the message string
    this->message.str("");
  }
  catch (boost::thread_resource_error error){
    this->thread_exception++;
    std::cout << "   Caught ROBO_logfile thread resource error: " 
        << this->thread_exception << ", write_0: " << func << " " 
        << print_bool(err, PRINT_BOOL_TRUE_FALSE) << " " << message
        << std::endl << std::flush;
//    << " " << this->thread_count << std::endl << std::flush;
  }
}
/**************** ROBO_logfile::write ****************/


void ROBO_logfile::write_log2(std::string message, int error, std::string func)
{
//  while (this->thread_count != 0){
//    usleep(rand() % 100 + 1);
//  }
  
  std::string current_time;   // String to hold the time stamp
  // Get the current time stamp, with format YYYY-MM-DD HH:HH:SS
  current_time = get_current_time(SECOND_MILLI);

  std::stringstream logstring;      // Stream to construct log string
  // If there is no error, then we build a normal string.  With an error, we
  // include ERROR in the string in the hope that someone reading the log file
  // will notice it (and of course to use grep to get errors out)
  logstring << current_time << " (" << func << "): ";
//  if (error == true){
//    logstring << " ERROR";
//  }
  if (error == LOG_ERROR){
    logstring << "ERROR ";
  }
  else if (error == LOG_WARNING){
    logstring << "WARNING ";
  }
  else if (error == LOG_DEBUG){
    logstring << "DEBUG ";
  }
  else if (error == LOG_EMERGENCY){
    logstring << "EMERGENCY ";
  }
  logstring << " " << message << std::endl;

  try {
    
    // Create the file if the file does not exist in the system
    if (stat(this->filename.c_str(), &this->fileinfo) != 0){
      this->open_file(OPEN_FILE_WRITE);
      this->close_file();
    }
    
    boost::interprocess::file_lock f_lock(this->filename.c_str());
    
    {
      boost::interprocess::scoped_lock<boost::interprocess::file_lock> e_lock(f_lock);
      boost::mutex::scoped_lock lock(this->log_mutex);

      // Open the log file to write to it
      this->open_file(OPEN_FILE_APPEND);

      // Dump the log string to the log file.
//      this->filestream << logstring.str() << std::flush;
      this->filestream << logstring.str();// << this->filestream.flush();
      // If the verbose flag is set, output to stdout
    
      // Increment log_count so the next thread can write to the log
//      this->log_count++;
    
      // Close the log file
      this->close_file();
      
      // Unblock the thread.
    //    lock.unlock();
    
      lock.unlock();
      e_lock.unlock();
      }
    
    //      need to fix this so that we get verbose printing back
//    if (common_info.verbose == true && this->quiet == false){
      std::cout << logstring.str() << std::flush;
//    }
    
//    boost::mutex::scoped_lock lock(this->log_mutex);
//    this->thread_count--;
//    lock.unlock();

  }
  catch(boost::interprocess::interprocess_exception err){
    std::cout << "Couldn't find file |" << this->filename.c_str() << "| to lock!"
        << std::endl << std::flush;
    std::cout << "Message: " << logstring.str() << std::flush;
  }
    
}


/**************** ROBO_logfile::write_log ****************/
/**
 Write strings to a log file.  A time stamp is placed in the file, followed by
 the message string passed.  This creates a thread for each log entry.
 \param [message] The message string to write
 \param [error] Flag to note if this is an error message
 \param [function] Name of function passing message to log file
 \param [counter] Thread counter for the log file
 \note Currently, this could remain stuck if log_count never increases or
 gets out of order.  An upgrade to time out and write the log message should
 be added at some future time.
 */
void ROBO_logfile::write_log(std::string message, int error, std::string func,
                unsigned int counter)
//void ROBO_logfile::write_log(std::string message, bool error, std::string function)
{
  // Wait until the log counter comes around to this thread.  Each time an
  // entry is sent to the log file, a thread is created and given the value
  // in counter.  The log_count variable tracks which log entries have been
  // written; this keeps the log in order of when messages are sent and
  // avoids race conditions.  When the counter is equal to log_count, this
  // thread writes the log file.
  while (counter != this->log_count){
    usleep(1000);
  }

//  while (this->lock_file(CHECK_FILE) == ERROR){
//    usleep(1000);
//  }

    // Block the thread with a mutex while working, keeps anything else from
    // writing into the file
//    boost::mutex::scoped_lock lock(this->log_mutex);

    // Open the log file to write to it
//    this->open_file(OPEN_FILE_APPEND);
    
    std::string current_time;   // String to hold the time stamp
    // Get the current time stamp, with format YYYY-MM-DD HH:HH:SS
    current_time = get_current_time(SECOND_MILLI);

    std::stringstream logstring;      // Stream to construct log string
    // If there is no error, then we build a normal string.  With an error, we
    // include ERROR in the string in the hope that someone reading the log file
    // will notice it (and of course to use grep to get errors out)
    logstring << current_time << " (" << func << "):";
    if (error == true){
      logstring << " ERROR";
    }
    logstring << " " << message << std::endl;

    try {
    // Open the log file to write to it
    this->open_file(OPEN_FILE_APPEND);
    
    boost::interprocess::file_lock f_lock(this->filename.c_str());
    
    {
      boost::interprocess::scoped_lock<boost::interprocess::file_lock> e_lock(f_lock);
      boost::mutex::scoped_lock lock(this->log_mutex);

    // Dump the log string to the log file.
    this->filestream << logstring.str() << std::flush;
    // If the verbose flag is set, output to stdout

    // Increment log_count so the next thread can write to the log
    this->log_count++;

    // Close the log file
    this->close_file();
    
    // Unblock the thread.
//    lock.unlock();

    lock.unlock();
    e_lock.unlock();
  }
  
  // Close the log file
//  this->close_file();
   
//      need to fix this so that we get verbose printing back
//    if (common_info.verbose == true && this->quiet == false){
      std::cout << logstring.str() << std::flush;
//    }

  }
  catch(boost::interprocess::interprocess_exception err){
    std::cout << "Couldn't find file |" << this->filename.c_str() << "| to lock!"
        << std::endl << std::flush;
    std::cout << "Message: " << logstring.str() << std::flush;
  }
/*  // Create the lock file
  this->lock_file(MAKE_FILE);
  
  // Block the thread with a mutex while working, keeps anything else from
  // writing into the file
  boost::mutex::scoped_lock lock(this->log_mutex);

  // Open the log file to write to it
  this->open_file(OPEN_FILE_APPEND);
  
  std::string current_time;   // String to hold the time stamp
  // Get the current time stamp, with format YYYY-MM-DD HH:HH:SS
  current_time = get_current_time(SECOND_MILLI);

  std::stringstream logstring;      // Stream to construct log string
  // If there is no error, then we build a normal string.  With an error, we
  // include ERROR in the string in the hope that someone reading the log file
  // will notice it (and of course to use grep to get errors out)
  logstring << current_time << " (" << function << "):";
  if (error == true){
    logstring << " ERROR";
  }
  logstring << " " << message << std::endl;

  // Dump the log string to the log file.
  this->filestream << logstring.str() << std::flush;
  // If the verbose flag is set, output to stdout
  if (common_info.verbose == true && this->quiet == false){
    std::cout << logstring.str() << std::flush;
  }

  // Increment log_count so the next thread can write to the log
  this->log_count++;

  // Close the log file
  this->close_file();
  
  // Unblock the thread.
  lock.unlock();

  // Remove the lock file
  this->lock_file(REMOVE_FILE);*/
}
/**************** ROBO_logfile::write_log ****************/


/**************** ROBO_logfile::write_log_config ****************/
/**
 Write configuration information from a configuration file to a log file.
 A time stamp is placed in the file, followed by the configuration parameters
 and variables.
 \param [variables] The config file variables
 \param [values] The values for the variables
 \param [config_file] The name of the config file read
 \note none
 */
void ROBO_logfile::write_log_config(std::vector<std::string> variables,
                      std::vector<std::string> values, std::string config_file)
{
//  while (this->lock_file(CHECK_FILE) == ERROR){
//    usleep(1000);
//  }
  
    // Open the log file to write to it
//    this->open_file(OPEN_FILE_APPEND);
    
    std::string current_time;   // String to hold the time stamp
    // Get the current time stamp, with format YYYY-MM-DD HH:HH:SS
    current_time = get_current_time(SECOND_MILLI);

    // Read the configuration variables into a string
    std::stringstream logstring;      // Stream to construct log string
    // Pretty header for the string
    logstring << current_time << ": Configuration file \"" << config_file
              << "\" read in successfully.  Variable values: " << std::endl;
    std::vector<std::string>::const_iterator var, val;  // Iterators
    // Set the first iterator to the beginning of the config variable vector
    val = values.begin();
    // Loop through the variables and add them to the string in the format
    // "variable=value" for each vector element (this uses iterators to keep
    // the vectors straight and loops over the variable vector)
    for(var=variables.begin(); var!=variables.end(); var++){
      logstring << "\t" << *var << "=\"" << *val << "\"" << std::endl;
      val++;
    }

    try {
      // Open the log file to write to it
      this->open_file(OPEN_FILE_APPEND);
      
    boost::interprocess::file_lock f_lock(this->filename.c_str());
    
    {
      boost::interprocess::scoped_lock<boost::interprocess::file_lock> e_lock(f_lock);
      boost::mutex::scoped_lock lock(this->log_mutex);

    // Dump the log string to the log file.
    this->filestream << logstring.str() << std::flush;

    // Close the log file
//    this->close_file();
    
    lock.unlock();
    e_lock.unlock();
  }
  
  // Close the log file
//  this->close_file();
  
  }
  catch(boost::interprocess::interprocess_exception err){
    std::cout << "Couldn't find file |" << this->filename.c_str() << "| to lock!" 
        << std::endl << std::flush;
    std::cout << "Message: " << logstring.str() << std::flush;
  }

/*  // Create the lock file
  this->lock_file(MAKE_FILE);
  
  // Open the log file to write to it
  this->open_file(OPEN_FILE_APPEND);
  
  std::string current_time;   // String to hold the time stamp
  // Get the current time stamp, with format YYYY-MM-DD HH:HH:SS
  current_time = get_current_time(SECOND_MILLI);

  // Read the configuration variables into a string
  std::stringstream logstring;      // Stream to construct log string
  // Pretty header for the string
  logstring << current_time << ": Configuration file \"" << config_file
            << "\" read in successfully.  Variable values: " << std::endl;
  std::vector<std::string>::const_iterator var, val;  // Iterators
  // Set the first iterator to the beginning of the config variable vector
  val = values.begin();
  // Loop through the variables and add them to the string in the format
  // "variable=value" for each vector element (this uses iterators to keep
  // the vectors straight and loops over the variable vector)
  for(var=variables.begin(); var!=variables.end(); var++){
    logstring << "\t" << *var << "=\"" << *val << "\"" << std::endl;
    val++;
  }

  // Dump the log string to the log file.
  this->filestream << logstring.str() << std::flush;

  // Close the log file
  this->close_file();
  
  // Remove the lock file
  this->lock_file(REMOVE_FILE);*/
}
/**************** ROBO_logfile::write_log_config ****************/


/**************** ROBO_logfile::get_function ****************/
/**
 Get the name of the function for the log file.
 \note none
 */
std::string ROBO_logfile::get_function()
{
  return (this->function.str());
}
/**************** ROBO_logfile::get_function ****************/


/**************** ROBO_logfile::set_function ****************/
/**
 Set the name of the function for the log file.
 \param [name] The name of the function
 \note none
 */
void ROBO_logfile::set_function(std::string name)
{
  this->function.str("");
  this->function << name;
}
/**************** ROBO_logfile::set_function ****************/


/**************** ROBO_logfile::close_file ****************/
/**
 Closes files in the ROBO system.  Error codes and messages are
 returned on errors accessing the file, success message returned if there are
 no problems.
 \note none
 */
int ROBO_logfile::close_file()
{
//std::cout << " logfunc: " << this->function.str() << std::flush;
  // Close the file stream if it is open
  if (this->filestream.is_open() == true){
//    std::cout << " r " << std::flush;
    this->filestream.flush();
//    std::cout << " s " << std::flush;
    this->filestream.close();
//    std::cout << " t " << std::flush;
//    this->log_thread.join();
//    std::cout << " u " << std::flush;
  }
  // It's an error if the file stream is not open
  else {
//    std::cout << " v " << std::flush << std::endl;
    return (ERROR_FILE_CLOSE);
  }
//  std::cout << " w " << std::flush << std::endl;

  // Everything worked, so flag NO_ERROR.
  return (NO_ERROR);
}
/**************** ROBO_logfile::close_file ****************/


/**************** ROBO_logfile::close_file ****************/
/**
 Closes files in the ROBO system.  Error codes and messages are
 returned on errors accessing the file, success message returned if there are
 no problems.
 \note none
 */
int ROBO_logfile::close_file(std::string func)
{
std::cout << " logfunc: " << func << std::flush;
  // Close the file stream if it is open
  if (this->filestream.is_open() == true){
    std::cout << " r " << std::flush;
    this->filestream.flush();
    std::cout << " s " << std::flush;
    this->filestream.close();
    std::cout << " t " << std::flush;
//    this->log_thread.join();
    std::cout << " u " << std::flush;
  }
  // It's an error if the file stream is not open
  else {
    std::cout << " v " << std::flush << std::endl;
    return (ERROR_FILE_CLOSE);
  }
  std::cout << " w " << std::flush << std::endl;

  // Everything worked, so flag NO_ERROR.
  return (NO_ERROR);
}
/**************** ROBO_logfile::close_file ****************/


/**************** ROBO_logfile::lock_file ****************/
int ROBO_logfile::lock_file(int mode)
{
  std::string function("ROBO_logfile::lock_file");
  std::stringstream file_name;
  std::stringstream message;

  // Build the file root, log directory + execurable name
  file_name << this->filename << ".lock";

  switch (mode){
    case ROBO_logfile::CHECK_FILE:
    {
      std::string line;     // Temporary string to read file lines into
      ROBO_file file;     // File class container
      file.filename = file_name.str();
      if (file.open_file_read(file.filename) == NO_ERROR){
        // Get the current time
        struct timeval tv;    // System time structure
        gettimeofday(&tv, NULL);
        double now = tv.tv_sec + (float)tv.tv_usec / 1000000; 
        // Get time in lock file
        getline(file.filestream, line);
        double time = atof(line.c_str());
     
        if (now - time > 1){
          int err = this->lock_file(REMOVE_FILE);
          if (err == ERROR){
            return (ERROR);
          }
        }
        else {
          return (ERROR);
        }
        
      }  
    }
    break;
    case ROBO_logfile::MAKE_FILE:
    {
      ROBO_file file;     // File class container
      file.filename = file_name.str();
      if (file.open_file(OPEN_FILE_WRITE) == NO_ERROR){
        // Get the current time
        struct timeval tv;    // System time structure
        gettimeofday(&tv, NULL);
        // Write this information to the file, so the rest of the system can
        // determine when a process started running
        file.filestream << tv.tv_sec << "." << tv.tv_usec << std::endl;
        file.close_file();
      }
      // Log that the file could not be created
      else {
        message << "unable to make log lock file: " << file_name.str();
//        ROBO_logfile log;     // Log file class container
//        log.filename = common_info.log_dir + common_info.executable_name + ".log";
//        log.open_file(OPEN_FILE_APPEND);
//        log.write(function, true, message.str());
        this->write(function, true, message.str());
        // Return a bad message
        return (ERROR);
      }
    }
    break;
    case ROBO_logfile::REMOVE_FILE:
    {
      std::string filename(file_name.str());
      // See if the file exists
      if (access(filename.c_str(), F_OK) == 0){
        if (remove(filename.c_str()) != 0){
          message << "unable to remove log lock file: " << file_name.str() << " error: "
            << strerror(errno);
//          ROBO_logfile log;     // Log file class container
//          log.filename = common_info.log_dir + common_info.executable_name + ".log";
//          log.open_file(OPEN_FILE_APPEND);
//          log.write(function, true, message.str());
          this->write(function, true, message.str());
          return (ERROR);
        }
      }
    }
    break;
  }
  
  return (NO_ERROR);
}
/**************** ROBO_logfile::lock_file ****************/


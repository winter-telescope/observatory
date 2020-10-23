/**
 \file common.h
 \brief Common functions used throughout the ROBO software
 \details Functions in this file are used in many places in the ROBO software,
 and with the ROBO_common class variables.

 Copyright (c) 2009-2011 California Institute of Technology.
 \author Dr. Reed L. Riddle  riddle@caltech.edu

 <b>Version History</b>:
 \verbatim
 2009-07-17:  First complete version
 2010-02-25:  Updated error control system to new standard
 \endverbatim
 */

// System include files
# include <ctime>
# include <cstdlib>
# include <iostream>
# include <iomanip>
# include <sys/time.h>
# include <dirent.h>
# include <vector>

// Local include files
# include "common.h"
# include "file_ops.h"

/**************** directory_name_check ****************/
/**
 Checks the directory to make sure that the string passed points to a directory
 on the system.  Includes an original directory that is used as a default.  If
 the directory does not exist, this attempts to create it.
 \param [original] The variable for the original directory
 \param [config_name] The name of the configuration file variable for the directory
 \param [new_directory] The new directory value
 \note none
 */
std::string directory_name_check(std::string original, std::string config_name,
                                 std::string new_directory)
{
  std::string function("directory_name_check");  // Function name
  std::string test_string;  // String constructed to test directory
  char test_char;           // Character to test directory
  ROBO_logfile log;
  log.filename = common_info.log_dir + COMMON_LOGFILE_NAME + ".log";
//  ROBO_error error;       // Error class created to log errors
//	error.type = CLASS_ROBO_FILE;
//	error.log_name = common_info.log_name;

  // If the new directory string is empty, flag that and set the test string to
  // the original directory that is passed in
  if (new_directory.length() < 1){
//    error.code = ERROR_PARAM_BLANK;
//    error.params[0] << config_name.c_str();
//    error.Handle_error(error);
  	std::string message;
    handle_error_message(ERROR_PARAM_BLANK, config_name.c_str(), message);
    log.write(function, true, message);
    test_string = original;
  }
  // Do some tests on the new_directory string to set the directory path
  else {
    // If the directory is in the current directory, set it
    if (new_directory.compare(0, 2, "./") == 0){
      test_string = new_directory;
    }
    // If the new directory does not lead with a /, then we presume it is made
    // in the home directory root level and set the string up for it
    else if ((test_char = new_directory[0]) != '/'){
      test_string = common_info.home_dir + '/' + new_directory;
    }
    // Otherwise, we take the string verbatim
    else {
      test_string = new_directory;
    }
  }

  // Add a / to the end of the string, so we don't make an error somewhere
  // by assuming a / is present at the end of the string and muck up a directory
  // path
  if (test_string[test_string.length()-1] != '/'){
    test_string = test_string + '/';
  }

  // Make sure the directory exists
  DIR *dirp;    // Pointer to the directory
  // Try to open the new directory; if it does not exist then the pointer is NULL
  if ((dirp = opendir(test_string.c_str())) == NULL){
    // If it did not exist, then try to make it.  If it cannot be made, then
    // flag an error and return a string of ""
    if ((mkdir(test_string.c_str(), S_IRWXU | S_IRWXG | S_IROTH | S_IXOTH)) != 0){
//    if ((mkdir(test_string.c_str(), 0775)) != 0){
//      error.code = ERROR_DIRECTORY;
//      error.params[0] << config_name.c_str();
//      error.Handle_error(error);
    	std::string message;
      handle_error_message(ERROR_DIRECTORY, config_name.c_str(), message);
      return ("");
    }
    // If the directory was made, send a message about that to the log
    else {
//      ROBO_logfile log;
//      log.filename = common_info.log_dir + COMMON_LOGFILE_NAME + ".log";
//      log.set_function("directory_name_check");
//      log.open_file(OPEN_FILE_APPEND);
      std::stringstream message;
      message << "Directory " << test_string.c_str()
									<< " does not exist, created it.";
      log.write(function, true, message.str());
    }
  }
  // If the directory already existed, close it.
  else {
    closedir(dirp);
  }

  // Return the string with the new directory path when the tests are successful
  return (test_string);
}
/**************** directory_name_check ****************/


/**************** ROBO_common::common_config ****************/
/**
 Reads in a configuration file to define the common parameters for the ROBO
 software.  This configuration file should include a CONFIG_DIR variable for
 other configuration files that reside in the same place as the common config
 file.  The configuration file must be set up with variable=value pairs in the
 same format as a Bash script:
 \code
 # Configuration file directory
 CONFIG_DIR="/home/bob/Config/"
 \endcode
 \param [config_file] The configuration file to read for the common parameters
 \note This routine is critical, if it fails then the entire program needs
 to abort and the path to the configuration file must be fixed by the
 user (it's either a failure on compiling or a missing file).

 */
void ROBO_common::common_config(std::string config_file_in)
{
  std::string function("ROBO_common::common_config");
  std::stringstream message;
//  int attempts = 1;     // Number of times to try to get the configuration
//  ROBO_error error;   // Create an error container for any errors that happen
//	error.type = CLASS_ROBO_FILE;
//	error.log_name = common_info.log_name;
//
//  // Set the fatal error flag
//  error.fatal_error = NO_ERROR;

  ROBO_logfile log;
  log.filename = common_info.log_dir + COMMON_LOGFILE_NAME + ".log";

  // Get the user home directory
  this->home_dir = getenv("HOME");
  // Get the user ID.
  this->user_id = getuid();

  // On success, attempts will be set to 0, otherwise it should max out.
//  while (attempts != 0 && attempts < MAX_ATTEMPTS){
//    try {
      this->config_file = config_file_in;

      // Read the configuration file.
      Config config(this->config_file);

  // If reading the common config file fails, exit the program.  If it fails
  //  then the entire program needs to abort and the path to the configuration
  // file must be fixed by the user (it's either a failure on compiling or a
  // missing file).
      int error_code;
      error_code = config.read_config(config);
      if (error_code != NO_ERROR){
        message << "file error thrown, error code: "
                << common_info.erreg.get_code(error_code) << ". Exiting!";
        log.write(function, true, message.str());
        exit(-1);
      }
//      error.code = config.read_config(config);
//      if (error.code != NO_ERROR){
//        error.params[0] << config_file;
//      	throw (error);
//      }


      // Set the parameter values, do some error checking along the way
      int i = 0;            // Loop index variable
      std::string test;     // A testing variable to check directory names
      for (i=0; i<config.n_elements; i++){
        // Look for the configuration file directory variable
        if (config.vars[i].find("CONFIG_DIR", 0) != std::string::npos){
          // If the directory test returns something, set the variable
          if ((test = directory_name_check(common_info.config_dir, config.vars[i],
                                      config.params[i])) != ""){
            common_info.config_dir = test;
          }
        }

        // Look for the data directory variable
        else if (config.vars[i].find("BIN_DIR", 0) != std::string::npos){
          // If the directory test returns something, set the variable
          if ((test = directory_name_check(common_info.data_dir, config.vars[i],
                                           config.params[i])) != ""){
            common_info.bin_dir = test;
          }
        }

        // Look for the data directory variable
        else if (config.vars[i].find("DATA_DIR", 0) != std::string::npos){
          // If the directory test returns something, set the variable
          if ((test = directory_name_check(common_info.data_dir, config.vars[i],
                                           config.params[i])) != ""){
            common_info.data_dir = test;
          }
        }

        // Look for the log file directory variable
        else if (config.vars[i].find("LOG_DIR", 0) != std::string::npos){
          // If the directory test returns something, set the variable
         if ((test = directory_name_check(common_info.log_dir, config.vars[i],
                                           config.params[i])) != ""){
            common_info.log_dir = test;
          }
        }

        // Look for the status directory variable
        else if (config.vars[i].find("STATUS_DIR", 0) != std::string::npos){
          // If the directory test returns something, set the variable
          if ((test = directory_name_check(common_info.status_dir, config.vars[i],
                                           config.params[i])) != ""){
            common_info.status_dir = test;
          }
        }

        // Look for the telemetry directory variable
        else if (config.vars[i].find("TELEMETRY_DIR", 0) != std::string::npos){
          // If the directory test returns something, set the variable
          if ((test = directory_name_check(common_info.telemetry_dir, config.vars[i],
                                           config.params[i])) != ""){
            common_info.telemetry_dir = test;
          }
        }
        
        // Look for the telemetry directory variable
        else if (config.vars[i].find("QUEUE_DIR", 0) 
                 != std::string::npos){
          // If the directory test returns something, set the variable
          if ((test = directory_name_check(common_info.tip_tilt_dir, config.vars[i],
                                           config.params[i])) != ""){
            common_info.queue_dir = test;
          }
        }

        // Look for the date switch variable
        else if (config.vars[i].find("DAY_SWITCH_TIME", 0)
                 != std::string::npos){
          common_info.day_switch_time = atoi(config.params[i].c_str());
        }
      }

//      // Everything worked, so get out of the loop.
//      attempts = 0;
//
//      // Log a message that the configuration was found successfully. An error
//      // will be thrown and this skipped if there is a problem
//      ROBO_logfile log;
//      log.filename = common_info.log_dir + COMMON_LOGFILE_NAME + ".log";
////      log.open_file(OPEN_FILE_APPEND);
  // Log a message that the configuration was found successfully.
  log.write_log_config(config.vars, config.params, this->config_file);
  message << "successfully read config file " << this->config_file;
  log.write(function, false, message.str());
//    }
//    // Catch any errors thrown, pass them to the error catching function
//    catch (ROBO_error & error){
//      // Get the error message
//    	error.fatal_error = error.Handle_error(error);
//      // If we get to the maximum attempts, throw an error
//      if (attempts++ == MAX_ATTEMPTS){
//      	error.code = MAX_ATTEMPTS;
//      	error.fatal_error = error.Handle_error(error);
//      }
//      // This routine is critical, if it fails then the entire program needs
//      // to abort and the path to the configuration file must be fixed by the
//      // user (it's either a failure on compiling or a missing file).
//      exit(-1);
//    }
//  }
}
/**************** ROBO_common::common_config ****************/


/**************** void Tokenize ****************/
/**
 Creates a vector of tokens from an input string.  Call is like this:
 \code
 Tokenize(str, tokens, ",<'> " );
 \endcode
 More than one token can be used in the call, but it's probably safer to use a
 single token if possible.  The string is not changed, and the new tokens go
 into the vector of strings.
 passed to the function.
 \param [str] String to tokenize
 \param [tokens] Vector of strings that tokens are put into
 \param [delimiters] Optional delimiter for separating string into tokens.
 There can be more than one, and space is the default.
 \note This was taken from the internet, several examples are available online.
 */
int Tokenize(const std::string& str,
              std::vector<std::string>& tokens,
              const std::string& delimiters = " ")
{
  // Clear the tokens vector, we only want to putput new tokens
  tokens.clear();
  
  // If the string is zero length, return now with no tokens
  if (str.length() == 0){
  	return(0);
  }
  
  // Skip delimiters at beginning.
  std::string::size_type lastPos = str.find_first_not_of(delimiters, 0);
  // Find first "non-delimiter".
  std::string::size_type pos     = str.find_first_of(delimiters, lastPos);

  std::string quote("\"");
  int quote_start = str.find(quote); //finds first quote mark
  int quote_end;
  bool quotes_found = false;
  
  if (quote_start != std::string::npos){
    quote_end = str.find(quote, quote_start + 1); //finds second quote mark
  }
  else {
    quote_start = -1;
  }
//  std::cout << std::endl << " tokenizer: " << str.length() << " |" << str << "| " << quote_start
//      << " " << quote_end << " " << lastPos << " " << pos 
//      << std::endl << std::flush;

  while (std::string::npos != pos || std::string::npos != lastPos)
  {
    if (quotes_found == true){
      tokens.push_back(str.substr(lastPos + 1, pos - lastPos - 2));
      pos++;
      lastPos = str.find_first_not_of(delimiters, pos);
      quotes_found = false;
    }

    else {
    // Found a token, add it to the vector.
    tokens.push_back(str.substr(lastPos, pos - lastPos));
 
    // Skip delimiters.  Note the "not_of"
    lastPos = str.find_first_not_of(delimiters, pos);
    }
    
    // If the next character is a quote, grab between the quotes 
    if (std::string::npos != lastPos && lastPos == quote_start){
      pos = str.find_first_of("\"", lastPos + 1) + 1;
      quotes_found = true;
    }
    // Otherwise, find next "non-delimiter"
    else {
      pos = str.find_first_of(delimiters, lastPos);
    }
//    std::cout << lastPos << " " << pos << std::endl ;
//    timeout();
  }
  
//  for(int i=0; i < tokens.size(); i++){
//    std::cout << i << " " << tokens[i] << std::endl;
//  }
  
  return(tokens.size());
}
/**************** void Tokenize ****************/


/**************** TrimSpaces ****************/
/**
 Trims off empty strings from an input string; the string is changed in place.
 \param [str] The string to trim
 \note This was found onine at
 http://sarathc.wordpress.com/2007/01/31/how-to-trim-leading-or-trailing-spaces-of-string-in-c/
 */
void TrimSpaces( std::string & str)
{
  // Trim Both leading and trailing spaces
  size_t startpos = str.find_first_not_of(" \t"); // Find the first character position after excluding leading blank spaces
  size_t endpos = str.find_last_not_of(" \t"); // Find the first character position from reverse af

  // if all spaces or empty return an empty string
  if(( std::string::npos == startpos ) || ( std::string::npos == endpos))
  {
    str = "";
  }
  else
    str = str.substr( startpos, endpos-startpos+1 );

  /*
   // Code for  Trim Leading Spaces only
   size_t startpos = str.find_first_not_of(" \t"); // Find the first character position after excluding leading blank spaces
   if( string::npos != startpos )
   str = str.substr( startpos );
   */

  /*
   // Code for Trim trailing Spaces only
   size_t endpos = str.find_last_not_of(" \t"); // Find the first character position from reverse af
   if( string::npos != endpos )
   str = str.substr( 0, endpos+1 );
   */
}
/**************** TrimSpaces ****************/


/**************** print_bool ****************/
/**
 Prints out a string based on the value of the boolean passed to it.
 \param [state] The state of the boolean, <i>true</i> or <i>false</i>.
 \param [type] The type of string to print. This parameter is optional and
 defaults to printing ON or OFF.
 */
std::string print_bool(bool state, bool_type type){
  // Return a string based on the true/false value of the input variable.
  switch (type) {
    case (PRINT_BOOL_ON_OFF):
      if (state == true)
        return ("ON");
      else if (state == false)
        return ("OFF");
      // If somehow the boolean is some other value, return a bad value
      else
        return ("BAD VALUE");
    
    case (PRINT_BOOL_TRUE_FALSE):
      if (state == true)
        return ("TRUE");
      else if (state == false)
        return ("FALSE");
      // If somehow the boolean is some other value, return a bad value
      else
        return ("BAD VALUE");
    
  case (PRINT_BOOL_YES_NO):
    if (state == true)
      return ("YES");
    else if (state == false)
      return ("NO");
    // If somehow the boolean is some other value, return a bad value
    else
      return ("BAD VALUE");
      
  case (PRINT_BOOL_HIGH_LOW):
    if (state == true)
      return ("HIGH");
    else if (state == false)
      return ("LOW");
    // If somehow the boolean is some other value, return a bad value
    else
      return ("BAD VALUE");
  
  // Type not recognized. This should never happen.
  default:
    return ("BAD VALUE");
  }
}
/**************** print_bool ****************/



std::string & replaceAll(std::string & context, const std::string & from, const std::string & to)
{
    size_t lookHere = 0;
    size_t foundHere;
    while((foundHere = context.find(from, lookHere)) != std::string::npos)
    {
          context.replace(foundHere, from.size(), to);
          lookHere = foundHere + to.size();
    }
    return context;
}

//template <typename T>
bool is_float(std::string const& s, float * number, bool failIfLeftoverChars)
{
  std::istringstream i(s);
//  T x;
  char c;
  if (!(i >> *number) || (failIfLeftoverChars && i.get(c)))
//    throw BadConversion("convertToDouble(\"" + s + "\")");
    return false;
  else
    return true;
}

bool is_int(std::string const& s, int * number, bool failIfLeftoverChars)
{
  std::istringstream i(s);
//  T x;
  char c;
  if (!(i >> *number) || (failIfLeftoverChars && i.get(c)))
//    throw BadConversion("convertToDouble(\"" + s + "\")");
    return false;
  else
    return true;
}

//template<typename T>
std::string num_to_string(float value)
{
	std::stringstream temp;
	temp << value;
	return (temp.str());
}

bool get_bool_value(std::string & input)
{
//  if (atoi(input.c_str()) == 1){
  if (input.compare("ON") == 0){
  	return(true);
  }
  else if (input.compare("TRUE") == 0){
    return(true);
  }
  else if (input.compare("YES") == 0){
    return(true);
  }
  else if (input.compare("HIGH") == 0){
    return(true);
  }
  else if (atoi(input.c_str()) == 1){
    return(true);
  }
  else {
  	return(false);
  }
}

int shell_command(const std::string & command, std::string & output,
                  const std::string & mode)
{
  // Create the stringstream
  std::stringstream sout;
  
  // Run Popen
  FILE *in;
  char buff[1024];
  
  // Test output
  if(!(in = popen(command.c_str(), mode.c_str()))){
    return 1;
  }
  
  // Parse output
  while(fgets(buff, sizeof(buff), in)!=NULL){
    sout << buff;
  }
  
  // Close
  int exit_code = pclose(in);
  
  // set output
  output = sout.str();
  
  // Return exit code
  return (exit_code == 0);
}




/**
 \file registry.h
 \brief Registers error and command codes through the system
 \details Header file containing definitions for the registry system that is 
 used to track command and error codes through the system.  The common_info 
 class contains the two registries, so they are available code wide.
 
 Copyright (c) 2009-2011 California Institute of Technology.
 \author Dr. Reed L. Riddle  riddle@caltech.edu
 
 <b>Version History</b>:
 \verbatim
 2010-04-19:  Split off of common.h file
 \endverbatim
 */

// Use a preprocessor statement to set a variable that checks if the header has
// already loaded...this avoids loading the header file more than once.
# ifndef REGISTRY_H
# define REGISTRY_H

// System include files
# include <iostream>
# include <vector>
# include <sstream>
//# include <boost/thread.hpp>

// Local include files
//# include "common.h"
# include "file_ops.h"


/** \class ROBO_registry        
 \brief Class for code registry.
 \details This class defines the code registry.  Any class that has
 codes associated with its behavior should register the codes and a string for
 each code into this class.  When a function is called, the function 
 calls into this class to retrieve the string associated with the code.
 \note None.*/
class ROBO_registry {
private:
  
  /** \var mutable boost::mutex mutex
   \details Mutex to block when registry is accessed by threads. */
  mutable boost::mutex mutex;

  /** \var std::vector<int> codes
   \details The codes contained in the registry.  Codes must be unique values. */
  std::vector<int> codes;
  
  /** \var std::vector<std::string> strings
   \details The string that corresponds to each code */
  std::vector<std::string> strings;
  
  /** \var std::vector<int> registries
   \details Registries that have been loaded. */
  std::vector<int> registries;
  
public:
  
  /// Registry code groups that are known to the codebase
  enum {
    ARCHON_REGISTRY,
    ARM_HEATER_REGISTRY,
    CAMERA_REGISTRY,
    DATA_REGISTRY,
    EPM_REGISTRY,
    FILTER_REGISTRY,
    FITS_REGISTRY,
    ILLUMINATOR_REGISTRY,
    KUKA_REGISTRY,
    MESSAGE_REGISTRY,
    MOTION_REGISTRY,
    POWER_REGISTRY,
    QUEUE_REGISTRY,
    ROBO_REGISTRY,
    SENSOR_REGISTRY,
    SHUTTER_REGISTRY,
    TCS_REGISTRY,
    WEATHER_REGISTRY,
    WATCHDOG_REGISTRY
  };
  
  /** \var std::string registry
   \details The name of the registry */
  std::string registry_name;
  
  /**************** ROBO_registry::add_code ****************/
  /** Add a code and the corresponding string to the registry.
   \param [code] The code to add
   \param [string] The string used to define the code
   \return NO_ERROR if successful, ERROR if a matching code is already in the 
   registry
   \note This is almost always going to be run as part of a constructor.
   */
  void add_code(int code, std::string in_string, std::string function, 
                ROBO_logfile & log)
  {
    boost::lock_guard<boost::mutex> lock(this->mutex);
    for (unsigned int i = 0; i < this->codes.size(); i++){
      if (code == this->codes[i]){
        log.write(function, true, this->errmsg(code, in_string));
        return;
      }
    }
    this->codes.push_back(code);
    this->strings.push_back(in_string);
  }
  /**************** ROBO_registry::add_code ****************/
  
  
  /**************** ROBO_registry::get_code ****************/
  /** Get the string corresponding to a code from the registry.
   \param [code] The code to get
   \return The string used to define the code, of form [code:string]
   \note None.
   */
  std::string get_code(int code)
  {
    std::stringstream message;
    boost::lock_guard<boost::mutex> lock(this->mutex);
    for (unsigned int i = 0; i < this->codes.size(); i++){
      if (code == this->codes[i]){
        message << " [" << code << ":" << this->strings[i] << "] ";
        return (message.str());
      }
    }
    message << " [" << code << ":NOT_FOUND_IN_REGISTRY] ";
    return (message.str());
  }
  /**************** ROBO_registry::get_code ****************/
  
  
  /**************** ROBO_registry::get_code ****************/
  /** Dump an error message for a code found already in the registry when 
   running add_code.
   \param [code] The code to add
   \param [string] The string used to define the code
   \return The string used to define the code
   \note You can make your own error message when add_code fails, this just
   creates a standard string that can be used.
   */
  std::string errmsg(int code, std::string string)
  {
    std::stringstream message;
    message << "code [" << code << ":" << string << "] already found in "
    					<< "registry " << this->registry_name;
    return (message.str());
  }
  /**************** ROBO_registry::get_code ****************/
  
  
  /**************** ROBO_registry::registry_loaded ****************/
  /** Checks if a set of codes have been loaded into the registry.
   \param [code] The registry code group to check
   \return True if code is found, false if not
   \note None.
   */
  bool check_registry(int code)
  {
    boost::lock_guard<boost::mutex> lock(this->mutex);
    for (unsigned int i = 0; i < this->registries.size(); i++){
      if (code == this->registries[i]){
        return (true);
      }
    }
    return (false);
  }
  /**************** ROBO_registry::registry_loaded ****************/
  
  
  /**************** ROBO_registry::add_registry ****************/
  /** Add a registry group to the registry vector, so we can check for multiple entries of an entire group.
   \param [code] The code to add
   \param [string] The string used to define the code
   \return NO_ERROR if successful, ERROR if a matching code is already in the 
   registry
   \note This is almost always going to be run as part of a constructor.
   */
  void add_registry(int code)
  {
    boost::lock_guard<boost::mutex> lock(this->mutex);
    for (unsigned int i = 0; i < this->registries.size(); i++){
      if (code == this->registries[i]){
        return;
      }
    }
    this->registries.push_back(code);
  }
  /**************** ROBO_registry::add_registry ****************/
  
  
};


# endif

/**
 \file watchdogd.h
 \brief Header file for the watchdog system.
 \details This is the header file for the routines that handle functions that
 monitor and restart the robotic system if it fails.
 
 Copyright (c) 2016-2021 California Institute of Technology.
 \author Dr. Reed L. Riddle  riddle@caltech.edu
 \note
*/

// Use a preprocessor statement to set a variable that checks if the header has
// already loaded...this avoids loading a header file more than once.
# ifndef WATCHDOGD_H
# define WATCHDOGD_H

// Global include files
# include <iostream>
# include <string>
# include <boost/thread.hpp>

// Local include files
# include "common.h"
//# include "state.h"
# include "communications.h"
# include "registry.h"


/** \namespace ROBO_watchdog
 Namespace for the ROBO_watchdog data synchronization functions */
namespace ROBO_watchdog {

  /// Command codes for watchdogd operattions
  enum {
    START_WATCHDOG = CLASS_WATCHDOG,
    PAUSE_WATCHDOG,
    SHUTDOWN,
    EMERGENCY_SHUTDOWN,
    PROCESS_INFO
  };

  /// Error codes for watchdogd operattions
  enum {
    ERROR_CONFIGURATION_FILE = CLASS_WATCHDOG,
    ERROR_START_WATCHDOG,
    ERROR_PAUSE_WATCHDOG,
    WATCHDOGD_ERROR_DAEMON_CONNECTION,
    WATCHDOGD_CONTROL_COMMAND_ERROR,
    WATCHDOGD_CONTROL_COMMAND_BUSY,
    WATCHDOGD_ERROR_CONTROL_ERROR,
    WATCHDOGD_CONTROL_STATUS_ERROR,
    WATCHDOGD_CLIENT_MESSAGE_ERROR,
		ERROR_UNKNOWN
  };
  
  /************** ROBO_watchdog::data_registry_codes **************/
  /**
   Function to enter ROBO_watchdog command and error registry codes into the 
   registries for printing the codes.
   \param [log] Log object that contains the logging interface
   \note None.
   */
  inline void watchdog_registry_codes(ROBO_logfile & log)
  {
    // If these codes have already been added to the registry, skip execution
    if (common_info.comreg.check_registry(ROBO_registry::WATCHDOG_REGISTRY) == true){
      return;
    }

    // Add this function to the registries list
    std::string function("ROBO_watchdog::watchdog_registry_codes");
    common_info.comreg.add_registry(ROBO_registry::WATCHDOG_REGISTRY);
    
    // Add the command registry codes
    common_info.comreg.add_code(ROBO_watchdog::START_WATCHDOG,
                                "ROBO_watchdog::START_WATCHDOG",
                                function, log);
    common_info.comreg.add_code(ROBO_watchdog::PAUSE_WATCHDOG,
                                "ROBO_watchdog::PAUSE_WATCHDOG",
                                function, log);
    common_info.comreg.add_code(ROBO_watchdog::SHUTDOWN,
                                "ROBO_watchdog::SHUTDOWN",
                                function, log);
    common_info.comreg.add_code(ROBO_watchdog::EMERGENCY_SHUTDOWN,
                                "ROBO_watchdog::EMERGENCY_SHUTDOWN",
                                function, log);
    common_info.comreg.add_code(ROBO_watchdog::PROCESS_INFO,
                                "ROBO_watchdog::PROCESS_INFO",
                                function, log);
    
    // Add the error registry codes
    common_info.erreg.add_code(ROBO_watchdog::ERROR_CONFIGURATION_FILE,
                               "ROBO_watchdog::ERROR_CONFIGURATION_FILE",
                               function, log);
    common_info.erreg.add_code(ROBO_watchdog::ERROR_START_WATCHDOG,
                               "ROBO_watchdog::ERROR_START_WATCHDOG",
                               function, log);
    common_info.erreg.add_code(ROBO_watchdog::ERROR_PAUSE_WATCHDOG,
                               "ROBO_watchdog::ERROR_PAUSE_WATCHDOG",
                               function, log);
    common_info.erreg.add_code(ROBO_watchdog::WATCHDOGD_ERROR_DAEMON_CONNECTION,
                               "ROBO_watchdog::WATCHDOGD_ERROR_DAEMON_CONNECTION",
                               function, log);
    common_info.erreg.add_code(ROBO_watchdog::WATCHDOGD_CONTROL_COMMAND_ERROR,
                               "ROBO_watchdog::WATCHDOGD_CONTROL_COMMAND_ERROR",
                               function, log);
    common_info.erreg.add_code(ROBO_watchdog::WATCHDOGD_CONTROL_COMMAND_BUSY,
                               "ROBO_watchdog::WATCHDOGD_CONTROL_COMMAND_BUSY",
                               function, log);
    common_info.erreg.add_code(ROBO_watchdog::WATCHDOGD_ERROR_CONTROL_ERROR,
                               "ROBO_watchdog::WATCHDOGD_ERROR_CONTROL_ERROR",
                               function, log);
    common_info.erreg.add_code(ROBO_watchdog::WATCHDOGD_CONTROL_STATUS_ERROR,
                               "ROBO_watchdog::WATCHDOGD_CONTROL_STATUS_ERROR",
                               function, log);
    common_info.erreg.add_code(ROBO_watchdog::WATCHDOGD_CLIENT_MESSAGE_ERROR,
                               "ROBO_watchdog::WATCHDOGD_CLIENT_MESSAGE_ERROR",
                               function, log);
    common_info.erreg.add_code(ROBO_watchdog::ERROR_UNKNOWN,
                               "ROBO_watchdog::ERROR_UNKNOWN",
                               function, log);
  }
  /************** ROBO_watchdog::data_registry_codes **************/

  
  /// Number of watchdogd output telemetry items
  const int NUM_WATCHDOGD_PARAMS = 6;

  /** \class State
 	 \brief Monitors state of messaging system
 	 \details This class is used to monitor the state of the messaging system. */
  class State {
  private:
    
    /**************** FITS_file::data_swap ****************/
    /**
     This is used to swap between two State state class objects.  This is 
     used when constructing class objects with assignment or copy construction.
     \param [first] The first object to swap (swap into this)
     \param [second] The second object to swap (swap from this)
     */
    friend void watchdog_swap(ROBO_watchdog::State & first,
                            ROBO_watchdog::State & second)
    {
      // By swapping the members of two classes, the two classes are effectively
      // swapped.
      std::swap(first.update_time, second.update_time);
      std::swap(first.status_time, second.status_time);
      std::swap(first.error_code, second.error_code);
      std::swap(first.initialized, second.initialized);
    }
    /**************** FITS_file::data_swap ****************/
    
  public:
    
    /** \var boost::mutex state_mutex
     \details Mutex to lock thread variables */
    boost::mutex state_mutex;

    /** \var ROBO_time update_time
     \details Time that the state information was updated */
    ROBO_time update_time;
    
    /** \var time_t status_time
     \details UNIX time that the state information was updated */
    time_t status_time;
    
    /** \var int error_code
     \details Error code returned from the server */
    int error_code;
    
    /** \var bool initialized
     \details Initialization state flag */
    bool initialized;
    
    /** \var bool updated
     \details Flag if the status has been updated */
    bool updated;


    
    /**************** ROBO_watchdog::State::State ****************/
    /**
     This function constructs the data sync state class
     */
    State()
    {
      // Initialize the class
      this->initialize_class();
    }
    /**************** ROBO_watchdog::State::State ****************/
    
    
    /**************** ROBO_watchdog::State::~State ****************/
    /**
     This is the destructor for the data sync state class.
     */
    ~State()
    {
    }
    /**************** ROBO_watchdog::State::~State ****************/
    
    
    /**************** ROBO_watchdog::State::State ****************/
    /**
     This is the copy constructor for the data sync state class.
     */
    State(ROBO_watchdog::State & in_state)
    {
      watchdog_swap(*this, in_state);
    }
    /**************** ROBO_watchdog::State::State ****************/

    
    /**************** ROBO_watchdog::State::State ****************/
    /**
     This is the operator= constructor for the data sync state class.
     */
    State operator=(ROBO_watchdog::State & in_state)
    {
      watchdog_swap(*this, in_state);
      
      return *this;
    }
    /**************** ROBO_watchdog::State::State ****************/

    
    /************ ROBO_watchdog::State::initialize_class ************/
    /**
     Initializes the data sync state class variables to default values.
     */
    void initialize_class()
    {
      this->status_time = 0;
      this->initialized = false;
      this->error_code = NO_ERROR;
    }
    /************ ROBO_watchdog::State::initialize_class ************/
    
    
    /************* ROBO_watchdog::State::load_state *************/
    /**
     Loads the status string into the state class variables
     \param[status_message] A formatted string that contains the status
     */
    int load_state(std::string status_message)
    {
      // Break the message into tokens
      std::vector<std::string> tokens;  // Temporary tokens
      int err = Tokenize(status_message, tokens, " ");
      if (err == ROBO_watchdog::NUM_WATCHDOGD_PARAMS){
        // Unix time
        this->status_time = atoi(tokens[1].c_str());
        
        // Date and clock-time
        std::string temp = tokens[2] + " " + tokens[3];
        this->update_time.set_time(temp, ROBO_time::TIMEFMT_Y_M_D_H_M_S);
        
        // Initialized flag
        this->initialized = atoi(tokens[4].c_str());
        
        //Error code
        this->error_code = atoi(tokens[5].c_str());
      }
      
      // Return an error if there are not the right number of tokens
      else {
        return(ERROR);
      }
      
      return(NO_ERROR);
    }
    /************* ROBO_watchdog::State::load_state *************/
    
  };
  
}

# endif

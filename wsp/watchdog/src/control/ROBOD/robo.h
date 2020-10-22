/**
 \file robo.h
 \brief Header file for control software for Robo_AO robotic system.
 \details This is the header file for the routines that handle the basic class 
 and state monitoring of the robotic daemons and subsystems.
 
 Copyright (c) 2016-2021 California Institute of Technology.
 \author Dr. Reed L. Riddle  riddle@caltech.edu
 \note
*/

// Use a preprocessor statement to set a variable that checks if the header has
// already loaded...this avoids loading a header file more than once.
# ifndef ROBO_H
# define ROBO_H

// Global include files
# include <iostream>
# include <string>
//# include <boost/thread.hpp>

// Local include files
# include "common.h"
# include "state.h"
# include "communications.h"
# include "registry.h"


namespace ROBO_robotic {

  const int COMMAND_TIMEOUT_ATTEMPTS = 4;

  enum {
    INITIALIZE_SYSTEM = CLASS_ROBO,
    SHUTDOWN_SYSTEM,
    START_OPERATIONS,
    PAUSE_OPERATIONS,
    STOP_OPERATIONS,
    OPEN_MOSAIC_SYSTEM,
    CLOSE_MOSAIC_SYSTEM,
    RESET_MOSAIC_SYSTEM,
    KILL_MOSAIC_SYSTEM,
    SETUP_MOSAIC_OBSERVATION,
    TAKE_MOSAIC_IMAGE,
    OPEN_DATA_SYSTEM,
    CLOSE_DATA_SYSTEM,
    RESET_DATA_SYSTEM,
    KILL_DATA_SYSTEM,
    OPEN_FILTER_SYSTEM,
    CLOSE_FILTER_SYSTEM,
    RESET_FILTER_SYSTEM,
    KILL_FILTER_SYSTEM,
    OPEN_FITS_SYSTEM,
    CLOSE_FITS_SYSTEM,
    RESET_FITS_SYSTEM,
    KILL_FITS_SYSTEM,
    OPEN_GUIDE_SYSTEM,
    CLOSE_GUIDE_SYSTEM,
    RESET_GUIDE_SYSTEM,
    KILL_GUIDE_SYSTEM,
    OPEN_ILLUMINATOR_SYSTEM,
    CLOSE_ILLUMINATOR_SYSTEM,
    RESET_ILLUMINATOR_SYSTEM,
    KILL_ILLUMINATOR_SYSTEM,
    OPEN_MESSAGE_SYSTEM,
    CLOSE_MESSAGE_SYSTEM,
    RESET_MESSAGE_SYSTEM,
    KILL_MESSAGE_SYSTEM,
    OPEN_MONITOR_SYSTEM,
    CLOSE_MONITOR_SYSTEM,
    RESET_MONITOR_SYSTEM,
    KILL_MONITOR_SYSTEM,
    OPEN_MOTION_SYSTEM,
    CLOSE_MOTION_SYSTEM,
    RESET_MOTION_SYSTEM,
    KILL_MOTION_SYSTEM,
    OPEN_POWER_SYSTEM,
    CLOSE_POWER_SYSTEM,
    RESET_POWER_SYSTEM,
    KILL_POWER_SYSTEM,
    OPEN_QUEUE_SYSTEM,
    CLOSE_QUEUE_SYSTEM,
    RESET_QUEUE_SYSTEM,
    KILL_QUEUE_SYSTEM,
    OPEN_SHUTTER_SYSTEM,
    CLOSE_SHUTTER_SYSTEM,
    RESET_SHUTTER_SYSTEM,
    KILL_SHUTTER_SYSTEM,
    OPEN_TCS_SYSTEM,
    CLOSE_TCS_SYSTEM,
    RESET_TCS_SYSTEM,
    KILL_TCS_SYSTEM,
    OPEN_WATCHDOG_SYSTEM,
    CLOSE_WATCHDOG_SYSTEM,
    RESET_WATCHDOG_SYSTEM,
    KILL_WATCHDOG_SYSTEM,
    OPEN_WEATHER_SYSTEM,
    CLOSE_WEATHER_SYSTEM,
    RESET_WEATHER_SYSTEM,
    KILL_WEATHER_SYSTEM,

    
    
    
    
    SHUTDOWN,
    EMERGENCY_SHUTDOWN,
    PROCESS_INFO
  };

  
  enum {
    ERROR_INITIALIZE_SYSTEM = CLASS_ROBO,
    ERROR_SHUTDOWN_SYSTEM,
    ERROR_START_NIGHT_OPERATIONS,
    ERROR_STOP_NIGHT_OPERATIONS,
    ERROR_START_OPERATIONS,
    ERROR_PAUSE_OPERATIONS,
    ERROR_STOP_OPERATIONS,
    ERROR_MOSAIC_POWER_ON,
    ERROR_MOSAIC_POWER_OFF,
    ERROR_OPEN_MOSAIC_SYSTEM,
    ERROR_CLOSE_MOSAIC_SYSTEM,
    ERROR_RESET_MOSAIC_SYSTEM,
    ERROR_SETUP_MOSAIC_OBSERVATION,
    ERROR_TAKE_MOSAIC_IMAGE,
    ERROR_VIC_TIMEOUT,
    ERROR_VIC_CONNECTION,
    ERROR_VIC_COMMAND_FAILED,
    ERROR_WATCHDOG_TIMEOUT,
    ERROR_WATCHDOG_CONNECTION,
    ERROR_DATA_TIMEOUT,
    ERROR_DATA_STATUS,
    ERROR_DATA_CONNECTION,
    ERROR_DATA_COMMAND_FAILED,
    ERROR_OPEN_DATA,
    ERROR_CLOSE_DATA,
    ERROR_FILTER_TIMEOUT,
    ERROR_FILTER_STATUS,
    ERROR_FILTER_CONNECTION,
    ERROR_FILTER_COMMAND_FAILED,
    ERROR_FILTER_NOT_AUTOMATED,
    ERROR_FILTER_TELESCOPE_POSITION,
    ERROR_FILTER_POWER,
    ERROR_OPEN_FILTER,
    ERROR_CLOSE_FILTER,
    ERROR_FITS_TIMEOUT,
    ERROR_FITS_STATUS,
    ERROR_FITS_CONNECTION,
    ERROR_FITS_COMMAND_FAILED,
    ERROR_OPEN_FITS,
    ERROR_CLOSE_FITS,
    ERROR_GUIDE_TIMEOUT,
    ERROR_GUIDE_STATUS,
    ERROR_GUIDE_CONNECTION,
    ERROR_GUIDE_COMMAND_FAILED,
    ERROR_OPEN_GUIDE,
    ERROR_CLOSE_GUIDE,
    ERROR_FOCUS_TIMEOUT,
    ERROR_FOCUS_STATUS,
    ERROR_FOCUS_CONNECTION,
    ERROR_FOCUS_COMMAND_FAILED,
    ERROR_OPEN_FOCUS,
    ERROR_CLOSE_FOCUS,
    ERROR_ILLUMINATOR_CONNECTION,
    ERROR_ILLUMINATOR_COMMAND_FAILED,
    ERROR_ILLUMINATOR_STATUS,
    ERROR_ILLUMINATOR_TIMEOUT,
    ERROR_OPEN_ILLUMINATOR,
    ERROR_CLOSE_ILLUMINATOR,
    ERROR_MESSAGE_CONNECTION,
    ERROR_MESSAGE_COMMAND_FAILED,
    ERROR_MESSAGE_TIMEOUT,
		ERROR_MESSAGE_STATUS,
    ERROR_OPEN_MESSAGE,
    ERROR_CLOSE_MESSAGE,
    ERROR_MONITOR_TIMEOUT,
    ERROR_MONITOR_STATUS,
    ERROR_MONITOR_CONNECTION,
    ERROR_MONITOR_COMMAND_FAILED,
    ERROR_OPEN_MONITOR,
    ERROR_CLOSE_MONITOR,
    ERROR_MOTION_TIMEOUT,
    ERROR_MOTION_STATUS,
    ERROR_MOTION_CONNECTION,
    ERROR_MOTION_COMMAND_FAILED,
    ERROR_OPEN_MOTION,
    ERROR_CLOSE_MOTION,
    ERROR_POWER_TIMEOUT,
    ERROR_POWER_STATUS,
    ERROR_POWER_CONNECTION,
    ERROR_POWER_COMMAND_FAILED,
    ERROR_POWER_INITIALIZE,
    ERROR_POWER_SHUTDOWN,
    ERROR_OPEN_POWER,
    ERROR_CLOSE_POWER,
    ERROR_QUEUE_TIMEOUT,
    ERROR_QUEUE_STATUS,
    ERROR_QUEUE_CONNECTION,
    ERROR_QUEUE_COMMAND_FAILED,
    ERROR_OPEN_QUEUE,
    ERROR_CLOSE_QUEUE,
    ERROR_SHUTTER_TIMEOUT,
    ERROR_SHUTTER_STATUS,
    ERROR_SHUTTER_CONNECTION,
    ERROR_SHUTTER_COMMAND_FAILED,
    ERROR_SHUTTER_FAILURE,
    ERROR_OPEN_SHUTTER,
    ERROR_CLOSE_SHUTTER,
    ERROR_TCS_TIMEOUT,
    ERROR_TCS_STATUS,
    ERROR_TCS_CONNECTION,
    ERROR_TCS_COMMAND_FAILED,
    ERROR_TCS_STOW_POSITION,
    ERROR_TCS_STOW_MODE,
    ERROR_OPEN_TCS,
    ERROR_CLOSE_TCS,
    ERROR_WEATHER_TIMEOUT,
    ERROR_WEATHER_STATUS,
    ERROR_WEATHER_CONNECTION,
    ERROR_WEATHER_COMMAND_FAILED,
    ERROR_OPEN_WEATHER,
    ERROR_CLOSE_WEATHER,
    ERROR_CONFIGURATION_FILE,
    ERROR_MORNING_DATA_SYNC,
    ERROR_MORNING_UPDATE_FILE,
    ROBOD_ERROR_DAEMON_CONNECTION,
    ROBOD_CONTROL_COMMAND_ERROR,
    ROBOD_CONTROL_COMMAND_BUSY,
    ROBOD_ERROR_CONTROL_ERROR,
    ROBOD_CONTROL_STATUS_ERROR,
    ROBOD_CLIENT_MESSAGE_ERROR,
		ERROR_UNKNOWN
  };
  
  
  enum {
    STATUS_GOOD,
    STATUS_PAUSE,
    STATUS_WEATHER_PAUSE,
    STATUS_ERROR,
    STATUS_SHUTDOWN,
    STATUS_DAYTIME,
    STATUS_UNKNOWN
  };
  
  const std::string status_names[] = {
    "STATUS_GOOD",
    "STATUS_PAUSE",
    "STATUS_WEATHER_PAUSE",
    "STATUS_ERROR",
    "STATUS_SHUTDOWN",
    "STATUS_DAYTIME",
    "STATUS_UNKNOWN"
  };
  
  enum {
    MODE_STOPPED,
    MODE_DAYTIME,
    MODE_NIGHTTIME,
    MODE_CALIBRATION,
    MODE_OBSERVING,
    MODE_MORNING_STOP,
    MODE_SHUTDOWN,
    MODE_UNKNOWN
  };
  
  const std::string mode_names[] = {
    "MODE_STOPPED",
    "MODE_DAYTIME",
    "MODE_NIGHTTIME",
    "MODE_CALIBRATION",
    "MODE_OBSERVING",
    "MODE_MORNING_STOP",
    "MODE_SHUTDOWN",
    "MODE_UNKNOWN"
  };
  
  enum {
    GOOD,
    ERROR,
    PAUSED,
    STARTED,
    INITIALIZING,
    READY,
    SHUTTING_DOWN,
    STOPPED,
    CALIBRATIONS,
    OPEN_DOME,
    CLOSE_DOME,
    POINTING_TELESCOPE,
    STOW_TELESCOPE,
    MOVE_FOCUS,
    GET_POINTING_IMAGE,
    EXCHANGE_FILTER,
    MOSAIC_SETUP,
    MOSAIC_OBSERVATION,
    MOSAIC_FLAT_FIELD,
    MOSAIC_DARK_FRAME,
    MOSAIC_BIAS_FRAME,
    READING_QUEUE,
    AUTOFOCUS
  };
  
  const std::string state_names[] = {
    "GOOD",
    "ERROR",
    "PAUSED",
    "STARTED",
    "INITIALIZING",
    "READY",
    "SHUTTING_DOWN",
    "STOPPED",
    "CALIBRATIONS",
    "OPEN_DOME",
    "CLOSE_DOME",
    "POINTING_TELESCOPE",
    "STOW_TELESCOPE",
    "MOVE_FOCUS",
    "GET_POINTING_IMAGE",
    "EXCHANGE_FILTER",
    "MOSAIC_SETUP",
    "MOSAIC_OBSERVATION",
    "MOSAIC_FLAT_FIELD",
    "MOSAIC_DARK_FRAME",
    "MOSAIC_BIAS_FRAME",
    "READING_QUEUE",
    "AUTOFOCUS"
  };
  
  enum {
    DATA_GUIDE_SYSTEM,
    DATA_SYNC_SYSTEM,
    DATA_SYSTEM,
    FILTER_SYSTEM,
    FITS_SYSTEM,
    FOCUS_SYSTEM,
    GUIDE_SYSTEM,
    ILLUMINATOR_SYSTEM,
    MESSAGE_SYSTEM,
    MONITOR_SYSTEM,
    MOSAIC_SYSTEM,
    MOTION_SYSTEM,
    POWER_SYSTEM,
    QUEUE_SYSTEM,
    SHUTTER_SYSTEM,
    TCS_SYSTEM,
    WEATHER_SYSTEM,
    ROBOTIC_SYSTEM,
    UNKNOWN_MODE
  };
  
  const std::string system_names[] = {
    "Data guide system",
    "Data sync system",
    "Data system",
    "Filter system",
    "FITS system",
    "Focus system",
    "Guide system",
    "Illuminator system",
    "Message system",
    "Monitor system",
    "Mosaic system",
    "Motion system",
    "Power system",
    "Queue system",
    "Shutter system",
    "TCS system",
    "Weather system",
    "Robotic system",
    "Unknown mode"
  };

  
  void robo_registry_codes(ROBO_logfile & log);

  /** \class State
   \brief Contains the state of the robotic system.
   \details Monitors the operational state of the robotic system...this
   prints log information about what the system is doing.  */
  class State
  {
  private:
    
    
    
    bool preparing_observation;
    
    bool exchanging_filter;
    
    bool observation_prepared;

    bool point_telescope;

    bool telescope_pointed;

    bool start_science;
    
    bool science_started;
    
    bool science_complete;
    
    bool mark_queue;
    
    bool write_data;
    
    bool reading_data;
    
    bool data_written;
    
    bool focus_loop;
    
    bool focus_complete;
    
    bool stop_observing;
    
    void initialize_class();
    

  public:
    
    /** \var mutable boost::mutex state_mutex
     \details Mutex for blocking state variables */
    mutable boost::mutex state_mutex;
    
    enum {
      PREPARE_OBSERVATION_FLAG,
      OBSERVATION_PREPARED_FLAG,
      EXCHANGE_FILTER_FLAG,
      POINT_TELESCOPE_FLAG,
      TELESCOPE_POINTED_FLAG,
      START_SCIENCE_FLAG,
      SCIENCE_STARTED_FLAG,
      SCIENCE_COMPLETE_FLAG,
      MARK_QUEUE_FLAG,
      WRITE_DATA_FLAG,
      READING_DATA_FLAG,
      DATA_WRITTEN_FLAG,
      FOCUS_LOOP_FLAG,
      FOCUS_COMPLETE_FLAG,
      STOP_OBSERVING_FLAG
    };
    
    
    bool automated;
    
    int current;
    
    int previous;
    
    int operating_mode;

    bool system_initialized;

    bool observing;
    
    bool handling_error;
    
    bool morning_shutdown;
    
    std::string mosaic_name;
    
    std::string sync_site;
    
    bool shutdown_flag;

    bool calibration_complete;
    bool stop_calibration;
    bool mosaic_error;
    int mosaic_failures;
    
    bool weather_pause;
    double weater_start;
    double weather_lost_time;
    time_t total_observing_time;
    
    bool filter_error;
    
    bool fits_sync;

    bool ready_for_operations;
    
    bool force_daytime_mode;

    //    /** \var std::vector<std::string> strings
//     \details The string that corresponds to each state */
//    std::vector<std::string> strings;
    
    State()
    {
      this->initialize_class();
    }
    
    bool good();
    
    void reset(bool reset_all = false);
    
    void change_flag(int flag, bool value);

    bool get_flag(int flag);
    
    int change_state(int value);
    
    void previous_state(int value);

    int get_state();

  };
  
  

  const int NUM_ROBOD_PARAMS_NOT_INITIALIZED = 5;
  const int NUM_REQUIRED_ROBOD_PARAMETERS = 6;

  class Robo_state {
  private:
    
    /**************** FITS_file::swap ****************/
    /**
     This is used to swap between two Robo_state state class objects.  This is 
     used when constructing class objects with assignment or copy construction.
     \param [first] The first object to swap (swap into this)
     \param [second] The second object to swap (swap from this)
     */
    friend void robo_swap(ROBO_robotic::Robo_state & first,
                            ROBO_robotic::Robo_state & second)
    {
      // By swapping the members of two classes, the two classes are effectively
      // swapped.
      std::swap(first.update_time, second.update_time);
      std::swap(first.status_time, second.status_time);
      std::swap(first.error_code, second.error_code);
      std::swap(first.initialized, second.initialized);
      std::swap(first.connection_open, second.connection_open);
      std::swap(first.current_state, second.current_state);
    }
    /**************** FITS_file::swap ****************/
    
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
    
    bool connection_open;
    
    int current_state;
    
    
    /**************** ROBO_robotic::Robo_state::Robo_state ****************/
    /**
     This function constructs the Motion state class
     */
    Robo_state()
    {
      // Initialize the class
      this->initialize_class();
    }
    /**************** ROBO_robotic::Robo_state::Robo_state ****************/
    
    
    /**************** ROBO_robotic::Robo_state::~Robo_state ****************/
    /**
     This is the destructor for the Motion state class.
     */
    ~Robo_state()
    {
    }
    /**************** ROBO_robotic::Robo_state::~Robo_state ****************/
    
    
    /**************** ROBO_robotic::Robo_state::Robo_state ****************/
    /**
     This is the copy constructor for the Motion state class.
     */
    Robo_state(ROBO_robotic::Robo_state & in_state)
    {
      robo_swap(*this, in_state);
      //    this->swap(*this, in_motion);
    }
    /**************** ROBO_robotic::Robo_state::Robo_state ****************/

    
    //    Motion operator= (ROBO_state::Motion in_state);
    /**************** ROBO_robotic::Robo_state::Robo_state ****************/
    /**
     This is the operator= constructor for the Motion state class.
     */
    Robo_state operator=(ROBO_robotic::Robo_state & in_state)
    {
      robo_swap(*this, in_state);
      //    this->swap(*this, in_motion);
      
      return *this;
    }
    /**************** ROBO_robotic::Robo_state::Robo_state ****************/

    
    /************ ROBO_robotic::Robo_state::initialize_class ************/
    /**
     Initializes the motion state class variables to default values.
     */
    void initialize_class()
    {
      this->status_time = 0;
      this->initialized = false;
      this->updated = false;
      this->error_code = NO_ERROR;
      this->current_state = NO_ERROR;
    }
    /************ ROBO_robotic::Robo_state::initialize_class ************/
    
    
    /************* ROBO_robotic::Robo_state::load_state *************/
    /**
     Loads the status string into the state class variables
     \param[status_message] A formatted string that contains the status
     */
    int load_state(std::string status_message)
    {
      std::stringstream message;
      // Break the message into tokens
      std::vector<std::string> tokens;  // Temporary tokens
      int err = Tokenize(status_message, tokens, " ");
      if (err < ROBO_robotic::NUM_ROBOD_PARAMS_NOT_INITIALIZED){
        return(ERROR);
      }
      
      //Unix time
      this->status_time = atoi(tokens[1].c_str());
      
      //Date and clock-time
      std::string temp = tokens[2] + " " + tokens[3];
      this->update_time.set_time(temp, ROBO_time::TIMEFMT_Y_M_D_H_M_S);
      
      this->initialized = atoi(tokens[4].c_str());
      
      // If the system is not initialized, then there are only
      // NUM_MOTION_PARAMS_NOT_INITIALIZED parameters
      
      if (err == ROBO_robotic::NUM_ROBOD_PARAMS_NOT_INITIALIZED){
        this->error_code = NO_ERROR;
      }
      
      else if (err >= ROBO_robotic::NUM_REQUIRED_ROBOD_PARAMETERS)
      {
        this->error_code = atoi(tokens[5].c_str());
      }
      
      // Return an error if there are not the right number of tokens
      else {
        return(ERROR);
      }
      
      return(NO_ERROR);
    }
    /************* ROBO_robotic::Robo_state::load_state *************/
    
  };
  
}

# endif

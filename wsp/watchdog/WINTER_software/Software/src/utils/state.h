/**
 \file state.h
 \brief State classes for Robo_AO robotic system.
 \details This header file defines the classes for the states of the various
 ROBO subsystems.  States monitor what is happening in each of the subsystems
 during operations.
 
 Copyright (c) 2009-2011 California Institute of Technology.
 \author Dr. Reed L. Riddle  riddle@caltech.edu
 \note
 
 <b>Version History</b>:
 \verbatim
 2009-11-10:  First complete version
 \endverbatim
 */

// Use a preprocessor statement to set a variable that checks if the header has
// already loaded...this avoids loading a header file more than once.
# ifndef ROBO_STATE_H
# define ROBO_STATE_H

// Global include files
# include <boost/thread.hpp>

// Local include files
# include "basic.h"
# include "communications.h"
//# include "robo_camera.h"


namespace ROBO_state {
  
  class Daemon_state {
  
  public:
    
    /** \var mutable boost::mutex ao_control_mutex
     \details Mutex for blocking AO control variables */
    mutable boost::mutex control_mutex;
    
    bool daemon_shutdown;
    
    int command;
    int last_command;
    int command_error;
    bool command_error_found;
    int old_command_error;
    int command_attempts;
    int error;
    bool error_found;
    int old_error;
    int error_attempts;
    time_t command_error_time;
    time_t error_time;
    time_t timeout;
    
//    std::string daemon_message;
    /** \var std::vector<std::string> reply_params
     \details Parameters in a message from the server. */
    std::vector<std::string> reply;
    

    bool waiting;
    
    Daemon_state();

    void initialize_command_error();

    void initialize_error();

  };

  
  class LGS_daemon_state:  public Daemon_state {
    
    public :
    
      bool autowindow_closed;
      time_t window_time;
      bool window_closed;

      int error_code;
      float laser_temperature;
      float chiller_temperature;
      float laser_current;
      time_t laser_time;
      bool shutter_closed;
      bool interlock_closed;
      bool laser_on;
      float laser_power;

      
    LGS_daemon_state();

    int load_state(std::string status_message);
    
  };
  
  
  class AO_daemon_state:  public Daemon_state
  {
    
  public:
    
    /** \var double wfs_run_time
     \details Running time for the current AO system run, in seconds */
    float wfs_run_time;
    
    /** \var int num_wfs_frames
     \details Number of frames taken while the loop was running */
    int num_wfs_frames;
    
    /** \var int wfs_current_frame_rate
     \details Frame rate measured during operations, in Hz */
    float wfs_current_frame_rate;
    
    int wfs_loop_count;
    int wfs_frame_skips;
    int wfs_ndropped_frames;
    
    /** \var double tt_run_time
     \details Running time for the current AO system run, in seconds */
    float tt_run_time;
    
    /** \var int num_tt_frames
     \details Number of frames taken while the loop was running */
    int num_tt_frames;
    
    /** \var int tt_current_frame_rate
     \details Frame rate measured during operations, in Hz */
    float tt_current_frame_rate;
    
    int tt_loop_count;
    int tt_frame_skips;
    int tt_ndropped_frames;
    
    // AO performance
    unsigned int min;
    unsigned int max;
    unsigned int median;
    float focus;
    float leaky_average;
    float r0_est;
    float average_intensity;
    float secondary_focus;
    
    time_t status_time;
    time_t last_status_time;
    
    float focus_sum;
    float intensity_sum;
    int num_focus_points;
    int num_obs_seconds;
    float average_focus;
    float focus_limits[2];
    float intensity_limits[3];
    bool focus_update;
    int bad_state;
    
    AO_daemon_state();
    
    int load_state(std::string status_message);

  };


  
  
  
  
  
  class Tip_Tilt {
    
  public:
    
    /** \var boost::mutex state_mutex
     \details Mutex to lock thread variables */
    boost::mutex state_mutex;
    
    float low_light_value;
    float centroid[2];
    double fwhm;
    float platescale;
    double max_flux;
    double rotation;
    int error;
    double current_time;

    bool updated;
    bool image_good;
    
    Tip_Tilt();

    int load_state(std::string status_message);

    std::string server_message();

  };
  
  
  
  /*
   * Motion commands
   */  

  const int NUM_MOTION_PARAMS_NOT_INITIALIZED = 5;
  const int NUM_REQUIRED_MOTION_PARAMETERS = 11;

  enum {
    MOTION_OPEN_CONNECTION = CLASS_MOTION,
    MOTION_READ_DATA,
    MOTION_PROCESS_INFO,
    MOTION_TESTING,
    MOTION_SHUTDOWN,
    MOTION_EMERGENCY_SHUTDOWN,
    MOTION_CHECK_ERROR,
    MOTION_RELOAD_CONFIGURATION,

    MOTION_AXIS_MOVE_ABS,
    MOTION_AXIS_MOVE_REL,
    MOTION_AXIS_GET_INFO,
    MOTION_AXIS_HOME_AXIS,
    MOTION_AXIS_HOME_ALL,
    MOTION_EMERGENCY_STOP,
    MOTION_SEND_COMMAND,
    MOTION_SET_PIVOT,
    MOTION_CLOSE_CONNECTION,

    MOTION_FIRST = MOTION_OPEN_CONNECTION,
    MOTION_LAST  = MOTION_CLOSE_CONNECTION
  };
  
  /*
   * Motion errors.
   */
  enum {
    ERROR_MOTION_OPEN_CONNECTION = CLASS_MOTION,
    ERROR_MOTION_CLOSE_CONNECTION,
    ERROR_MOTION_INITIALIZED,
    ERROR_MOTION_INITIALIZE_FAILED,
    ERROR_MOTION_NOT_INITIALIZED,
    ERROR_MOTION_DAEMON_CONNECTION,
    ERROR_MOTION_CONTROL_COMMAND_ERROR,
    ERROR_MOTION_ERROR_CONTROL_ERROR,
    ERROR_MOTION_CONTROL_STATUS_ERROR,
    ERROR_MOTION_SOCKET_WRITE_ERROR,
    ERROR_MOTION_SOCKET_SELECT_ERROR,
    ERROR_MOTION_SOCKET_READ_ERROR,
    ERROR_MOTION_DEVICE_TIMEOUT,
    ERROR_MOTION_INVALID_AXIS_IDENTIFIER,
    ERROR_MOTION_INVALID_PIVOT_POINT_ID,
    ERROR_MOTION_TIMEOUT,

    ERROR_MOTION_AXIS_MOVE_ABS,
    ERROR_MOTION_AXIS_MOVE_REL,
    ERROR_MOTION_AXIS_HOME_AXIS,
    ERROR_MOTION_AXIS_HOME_ALL,
    ERROR_MOTION_SEND_COMMAND,
    ERROR_MOTION_SET_PIVOT,
    
    ERROR_MOTION_UNKNOWN,
    
    ERROR_MOTION_FIRST = ERROR_MOTION_OPEN_CONNECTION,
    ERROR_MOTION_LAST  = ERROR_MOTION_UNKNOWN
  };
  
  void motion_registry_codes(ROBO_logfile & log);
  
  class Motion {
  private:
    
    /**************** FITS_file::swap ****************/
    /**
     This is used to swap between two Motion state class objects.  This is used when
     constructing class objects with assignment or copy construction.
     \param [first] The first object to swap (swap into this)
     \param [second] The second object to swap (swap from this)
     */
    friend void motion_swap(ROBO_state::Motion & first, ROBO_state::Motion & second)
    {
      // By swapping the members of two classes, the two classes are effectively
      // swapped.
      std::swap(first.updated, second.updated);
      std::swap(first.update_time, second.update_time);
      std::swap(first.status_time, second.status_time);
      std::swap(first.error_code, second.error_code);
      std::swap(first.initialized, second.initialized);
      std::swap(first.connection_open, second.connection_open);
      std::swap(first.current_state, second.current_state);
      std::swap(first.moving, second.moving);
      std::swap(first.current_focus, second.current_focus);
      std::swap(first.inst_positions, second.inst_positions);
      std::swap(first.controller_error_state, second.controller_error_state);
      std::swap(first.axes_positions, second.axes_positions);
      std::swap(first.axes_on_target_status_values, second.axes_on_target_status_values);
      std::swap(first.pivot_point_position, second.pivot_point_position);
    }
    /**************** FITS_file::swap ****************/
   // void swap(ROBO_state::Motion & first, ROBO_state::Motion & second);

  public:
    
    /** \var bool updated
     \details Flag if the status has been updated */
    bool updated;
    
    /** \var boost::mutex state_mutex
     \details Mutex to lock thread variables */
    boost::mutex state_mutex;
    
    ROBO_time update_time;
    
    time_t status_time;
    
    /** \var int error_code
     \details Error code returned from the server */
    int error_code;
    
    bool initialized;
    
    bool connection_open;
    
    int current_state;

    // Is-the-stage-moving flag
    bool moving;
    
    float current_focus;
    float current_tip;
    float current_tilt;

    //a status string, general purpose
    std::string status;

    // Instrument coordinates
    std::vector<float>inst_positions;

    std::vector<int> controller_error_state;

    // Hexapod coordinates
    std::vector<float> axes_positions;

    std::vector<int> axes_on_target_status_values;

    std::vector<float> pivot_point_position;
    
    Motion();

    ~Motion();

    Motion(ROBO_state::Motion & in_motion);
    
//    Motion operator= (ROBO_state::Motion in_state);
    /**************** ROBO_state::Motion::Motion ****************/
    /**
     This is the operator= constructor for the Motion state class.
     */
    Motion operator=(ROBO_state::Motion & in_motion)
    {
    	motion_swap(*this, in_motion);
  //    this->swap(*this, in_motion);
      
      return *this;
    }
    /**************** ROBO_state::Motion::Motion ****************/


    void initialize_class();
    
    int load_state(std::string status_message);
    
    void copy_state(const Motion & in_state);
    
  };

  /****************** Stuff for Illuminator class *************/

  const int NUM_ILLUMINATOR_PARAMS_NOT_INITIALIZED = 5;
  const int NUM_REQUIRED_ILLUMINATOR_PARAMETERS = 8;

  enum {
    ILLUMINATOR_OPEN_CONNECTION = CLASS_ILLUMINATOR,
    ILLUMINATOR_READ_DATA,
    ILLUMINATOR_WRITE_DATA,
    ILLUMINATOR_PROCESS_INFO,
    ILLUMINATOR_TESTING,
    ILLUMINATOR_SHUTDOWN,
    ILLUMINATOR_EMERGENCY_SHUTDOWN,
    ILLUMINATOR_CHECK_ERROR,
    ILLUMINATOR_RELOAD_CONFIGURATION,
    ILLUMINATOR_START_SEQUENCE,
    ILLUMINATOR_RESET,
    ILLUMINATOR_INIT,
    ILLUMINATOR_TRIGGER,
    ILLUMINATOR_SET_FILTER,
    ILLUMINATOR_SET_SEQUENCE,

    ILLUMINATOR_CLOSE_CONNECTION,

    ILLUMINATOR_FIRST = ILLUMINATOR_OPEN_CONNECTION,
    ILLUMINATOR_LAST  = ILLUMINATOR_CLOSE_CONNECTION
  };

  enum {
    ERROR_ILLUMINATOR_OPEN_CONNECTION = CLASS_ILLUMINATOR,
    ERROR_ILLUMINATOR_CLOSE_CONNECTION,
    ERROR_ILLUMINATOR_INITIALIZED,
    ERROR_ILLUMINATOR_INITIALIZE_FAILED,
    ERROR_ILLUMINATOR_NOT_INITIALIZED,
    ERROR_ILLUMINATOR_DAEMON_CONNECTION,
    ERROR_ILLUMINATOR_CONTROL_COMMAND_ERROR,
    ERROR_ILLUMINATOR_CONTROL_ERROR,
    ERROR_ILLUMINATOR_ERROR_CONTROL_ERROR,
    ERROR_ILLUMINATOR_CONTROL_STATUS_ERROR,
    ERROR_ILLUMINATOR_SOCKET_REQUEST_ERROR,
    ERROR_ILLUMINATOR_SOCKET_WRITE_ERROR,
    ERROR_ILLUMINATOR_SOCKET_SELECT_ERROR,
    ERROR_ILLUMINATOR_SOCKET_READ_ERROR,
    ERROR_ILLUMINATOR_DEVICE_TIMEOUT,
    ERROR_ILLUMINATOR_WRITE_DATA_ERROR,
    ERROR_ILLUMINATOR_CRC_FAILURE,
    ERROR_ILLUMINATOR_RESET_FAILURE,
    ERROR_ILLUMINATOR_INIT_FAILURE,
    ERROR_ILLUMINATOR_SET_ADDRESS_FAILURE,
    ERROR_ILLUMINATOR_TRIGGER_FAILURE,
    ILLUMINATORD_ERROR_DAEMON_CONNECTION,
    ERROR_ILLUMINATOR_SET_FILTER_FAILURE,
    ERROR_ILLUMINATOR_FILTER_TOKENIZER_ERROR,
    ERROR_ILLUMINATOR_NO_SEQ_NUMBER_FOUND,
    ERROR_ILLUMINATOR_SEQUENCE_TOKENIZER_ERROR,
    ERROR_ILLUMINATOR_NO_LED_SEQUENCE_FOUND,
    ERROR_ILLUMINATOR_UNKNOWN_CONTROLLER_ERROR,
    ERROR_ILLUMINATOR_CALIB_SEND_FAILURE,

    ERROR_ILLUMINATOR_UNKNOWN_COMMAND,

    ERROR_ILLUMINATOR_FIRST = ERROR_ILLUMINATOR_OPEN_CONNECTION,
    ERROR_ILLUMINATOR_LAST  = ERROR_ILLUMINATOR_UNKNOWN_COMMAND
  };

  void illuminator_registry_codes(ROBO_logfile & log);

  class Illuminator {

  private:

    /**************** ROBO_state::Illuminator::swap ****************/
     /**
     This is used to swap between two Illuminator class objects.  This is used
     when constructing class objects with assignment or copy construction.
     \param [first] The first object to swap (swap into this)
     \param [second] The second object to swap (swap from this)
     */
    friend void illuminator_swap(ROBO_state::Illuminator & first,
                          ROBO_state::Illuminator & second)
    {
      // By swapping the members of two classes, the two classes are effectively
      // swapped.
      std::swap(first.update_time, second.update_time);
      std::swap(first.status_time, second.status_time);
      std::swap(first.error_code, second.error_code);
      std::swap(first.initialized, second.initialized);
      std::swap(first.connection_open, second.connection_open);
      std::swap(first.current_state, second.current_state);
      std::swap(first.updated, second.updated);
      std::swap(first.controller_error_msg, second.controller_error_msg);
      std::swap(first.system_status, second.system_status);
      std::swap(first.controller_errors, second.controller_errors);
      std::swap(first.illuminator_data, second.illuminator_data);
    }
    /**************** ROBO_state::Shutter_state::swap ****************/

  public:

    /** \var boost::mutex state_mutex
     \details Mutex to lock thread variables */
    boost::mutex state_mutex;

    ROBO_time update_time;

    time_t status_time;

    /** \var int error_code
     \details Error code returned from the server */
    int error_code;

    bool initialized;

    bool connection_open;

    int current_state;

    /** \var bool updated
     \details Flag if the status has been updated */
    bool updated;
    
    //Illuminator specific:  Just making this up...
    std::string controller_error_msg;
    std::string system_status;
    std::string configuration_string;  //Config string for Illuminator Arduino
    std::vector<int> controller_errors;  //Generalized error value vector
    std::vector<int> illuminator_data;  //I don't know what this is Errors?

    Illuminator(){}

    ~Illuminator(){}

    Illuminator(ROBO_state::Illuminator & in_state)
    {
      illuminator_swap( *this, in_state);
    }

//    Illuminator operator= (const Illuminator & in_state);
    /************* ROBO_state::Illuminator::Illuminator *************/
    /**

     */
    Illuminator operator= (const Illuminator & in_state)
    {
      this->initialize_class();

      this->copy_state(in_state);

      return *this;
    }
    /************* ROBO_state::Illuminator::Illuminator *************/

    void initialize_class();

    int load_state(std::string status_message);

    void copy_state(const Illuminator & in_state);

  };  

  /*
   * Shutter daemon stuff
   */

  const int NUM_SHUTTER_PARAMS_NOT_INITIALIZED = 5;
  const int NUM_REQUIRED_SHUTTER_PARAMETERS = 20;

  /// Defines control commands that can be sent to the the Shutter daemon
  enum {
    SHUTTER_OPEN_CONNECTION = CLASS_SHUTTERD,
    SHUTTER_CLOSE_CONNECTION,
    SHUTTER_OPEN_SHUTTER,
    SHUTTER_CLOSE_SHUTTER,
    SHUTTER_START_EXPOSURE,
    SHUTTER_RESET_SHUTTER,
    SHUTTER_GET_STATUS,
    SHUTTER_RELOAD_CONFIGURATION,
    SHUTTER_SHUTDOWN,
    SHUTTER_EMERGENCY_SHUTDOWN,
    SHUTTER_CHECK_ERROR,
    SHUTTER_PROCESS_INFO,
    SHUTTER_TESTING
  };

  /**
   Error codes for Shutter daemon.  First value must be class value so it
   doesn't overlap with global error codes. */
  enum {
    ERROR_SHUTTER_N_PARAMS = CLASS_SHUTTERD,
    ERROR_SHUTTER_OPEN_CONNECTION,
    ERROR_SHUTTER_INITIALIZED,
    ERROR_SHUTTER_NOT_INITIALIZED,
    ERROR_SHUTTER_CLOSE_CONNECTION,
    ERROR_SHUTTER_OPEN_SHUTTER,
    ERROR_SHUTTER_CLOSE_SHUTTER,
    ERROR_SHUTTER_START_EXPOSURE,
    ERROR_SHUTTER_UNKNOWN_CONFIG,
    ERROR_SHUTTER_RESET_SHUTTER,
    ERROR_SHUTTER_COMMUNICATIONS,
    ERROR_SHUTTER_COMMUNICATIONS_RESET,
    ERROR_SHUTTER_STATUS_THREAD,
    ERROR_SHUTTER_DAEMON_CONNECTION,
    ERROR_SHUTTER_CONTROL_COMMAND_ERROR,
    ERROR_SHUTTER_CONTROL_ERROR,
    ERROR_SHUTTER_CONTROL_STATUS_ERROR,
    ERROR_SHUTTER_SOCKET_REQUEST_ERROR,
    ERROR_SHUTTER_SOCKET_WRITE_ERROR,
    ERROR_SHUTTER_SOCKET_SELECT_ERROR,
    ERROR_SHUTTER_SOCKET_READ_ERROR,
    ERROR_SHUTTER_DEVICE_TIMEOUT,
		ERROR_SHUTTERD_DAEMON_CONNECTION,
		ERROR_SHUTTERD_COMMAND_BUSY,
    ERROR_SHUTTER_UNKNOWN_COMMAND
  };

  // Defined states for shutter position
  enum {
    SHUTTER_OPEN,
    SHUTTER_CLOSED,
    SHUTTER_UNKNOWN
  };

  const std::string shutter_positions[] = {
    "SHUTTER_OPEN",
    "SHUTTER_CLOSED",
    "SHUTTER_UNKNOWN"
  };

  /**************** ROBO_state::registry_codes ****************/
   /**
    Registry codes for the SHUTTERD namespace.  These are registered in the
    constructor for the class and should never be necessary unless this class
    is loaded.
    \note none
    */

//   void shutter_registry_codes(ROBO_logfile & log);

   inline void shutter_registry_codes(ROBO_logfile & log)
   {
     std::string function("ROBO_state::registry_codes");

    if (common_info.comreg.check_registry(ROBO_registry::SHUTTER_REGISTRY) == true){
        return;
    }

    common_info.comreg.add_registry(ROBO_registry::SHUTTER_REGISTRY);

     common_info.comreg.add_code(ROBO_state::SHUTTER_OPEN_CONNECTION,
                                 "ROBO_state::SHUTTER_OPEN_CONNECTION", function, log);
     common_info.comreg.add_code(ROBO_state::SHUTTER_CLOSE_CONNECTION,
                                 "ROBO_state::SHUTTER_CLOSE_CONNECTION", function, log);
     common_info.comreg.add_code(ROBO_state::SHUTTER_OPEN_SHUTTER,
                                 "ROBO_state::SHUTTER_OPEN_SHUTTER", function, log);
     common_info.comreg.add_code(ROBO_state::SHUTTER_CLOSE_SHUTTER,
                                 "ROBO_state::SHUTTER_CLOSE_SHUTTER", function, log);
     common_info.comreg.add_code(ROBO_state::SHUTTER_START_EXPOSURE,
                                 "ROBO_state::SHUTTER_START_EXPOSURE", function, log);
     common_info.comreg.add_code(ROBO_state::SHUTTER_RESET_SHUTTER,
                                 "ROBO_state::SHUTTER_RESET_SHUTTER", function, log);
     common_info.comreg.add_code(ROBO_state::SHUTTER_GET_STATUS,
                                 "ROBO_state::SHUTTER_GET_STATUS", function, log);
     common_info.comreg.add_code(ROBO_state::SHUTTER_RELOAD_CONFIGURATION,
                                 "ROBO_state::SHUTTER_RELOAD_CONFIGURATION", function, log);
     common_info.comreg.add_code(ROBO_state::SHUTTER_SHUTDOWN,
                                 "ROBO_state::SHUTTER_SHUTDOWN", function, log);
     common_info.comreg.add_code(ROBO_state::SHUTTER_EMERGENCY_SHUTDOWN,
                                 "ROBO_state::SHUTTER_EMERGENCY_SHUTDOWN", function, log);
     common_info.comreg.add_code(ROBO_state::SHUTTER_CHECK_ERROR,
				"ROBO_state::SHUTTER_CHECK_ERROR", function, log);
     common_info.comreg.add_code(ROBO_state::SHUTTER_PROCESS_INFO,
                                 "ROBO_state::SHUTTER_PROCESS_INFO", function, log);

     common_info.erreg.add_code(ROBO_state::ERROR_SHUTTER_N_PARAMS,
                                "ROBO_state::ERROR_SHUTTER_N_PARAMS", function,log);
     common_info.erreg.add_code(ROBO_state::ERROR_SHUTTER_OPEN_CONNECTION,
                                "ROBO_state::ERROR_SHUTTER_OPEN_CONNECTION",
                                function,log);
     common_info.erreg.add_code(ROBO_state::ERROR_SHUTTER_INITIALIZED,
                                "ROBO_state::ERROR_SHUTTER_INITIALIZED", function,log);
     common_info.erreg.add_code(ROBO_state::ERROR_SHUTTER_NOT_INITIALIZED,
                                "ROBO_state::ERROR_SHUTTER_NOT_INITIALIZED",
                                function,log);
     common_info.erreg.add_code(ROBO_state::ERROR_SHUTTER_CLOSE_CONNECTION,
                                "ROBO_state::ERROR_SHUTTER_CLOSE_CONNECTION",
                                function,log);
     common_info.erreg.add_code(ROBO_state::ERROR_SHUTTER_OPEN_SHUTTER,
                                "ROBO_state::ERROR_SHUTTER_OPEN_SHUTTER", function,log);
     common_info.erreg.add_code(ROBO_state::ERROR_SHUTTER_CLOSE_SHUTTER,
                                "ROBO_state::ERROR_SHUTTER_CLOSE_SHUTTER", function, log);
     common_info.erreg.add_code(ROBO_state::ERROR_SHUTTER_START_EXPOSURE,
                                "ROBO_state::ERROR_SHUTTER_START_EXPOSURE",
                                function, log);
     common_info.erreg.add_code(ROBO_state::ERROR_SHUTTER_UNKNOWN_CONFIG,
                               "ROBO_state::ERROR_SHUTTER_UNKNOWN_CONFIG",
                               function, log);
     common_info.erreg.add_code(ROBO_state::ERROR_SHUTTER_RESET_SHUTTER,
                                "ROBO_state::ERROR_SHUTTER_RESET_SHUTTER", function, log);
     common_info.erreg.add_code(ROBO_state::ERROR_SHUTTER_COMMUNICATIONS,
                                "ROBO_state::ERROR_SHUTTER_COMMUNICATIONS",
                                function, log);
     common_info.erreg.add_code(ROBO_state::ERROR_SHUTTER_COMMUNICATIONS_RESET,
                                "ROBO_state::ERROR_SHUTTER_COMMUNICATIONS_RESET",
                                function, log);
     common_info.erreg.add_code(ROBO_state::ERROR_SHUTTER_STATUS_THREAD,
                                "ROBO_state::ERROR_SHUTTER_STATUS_THREAD", function,log);
     common_info.erreg.add_code(ROBO_state::ERROR_SHUTTER_DAEMON_CONNECTION,
                                "ROBO_state::ERROR_SHUTTER_DAEMON_CONNECTION",
                                function, log);
     common_info.erreg.add_code(ROBO_state::ERROR_SHUTTER_CONTROL_COMMAND_ERROR,
                                "ROBO_state::ERROR_SHUTTER_CONTROL_COMMAND_ERROR",
                                function, log);
     common_info.erreg.add_code(ROBO_state::ERROR_SHUTTER_CONTROL_ERROR,
                                "ROBO_state::ERROR_SHUTTER_CONTROL_ERROR", function, log);
     common_info.erreg.add_code(ROBO_state::ERROR_SHUTTER_CONTROL_STATUS_ERROR,
                                "ROBO_state::ERROR_SHUTTER_CONTROL_STATUS_ERROR",
                                function, log);
     common_info.erreg.add_code(ROBO_state::ERROR_SHUTTER_SOCKET_REQUEST_ERROR,
                                "ROBO_state::ERROR_SHUTTER_SOCKET_REQUEST_ERROR",
                                function, log);
     common_info.erreg.add_code(ROBO_state::ERROR_SHUTTER_SOCKET_WRITE_ERROR,
                                "ROBO_state::ERROR_SHUTTER_SOCKET_WRITE_ERROR",
                                function, log);
     common_info.erreg.add_code(ROBO_state::ERROR_SHUTTER_SOCKET_SELECT_ERROR,
                                "ROBO_state::ERROR_SHUTTER_SOCKET_SELECT_ERROR",
                                function, log);
     common_info.erreg.add_code(ROBO_state::ERROR_SHUTTER_SOCKET_READ_ERROR,
                                "ROBO_state::ERROR_SHUTTER_SOCKET_READ_ERROR",
                                function, log);
     common_info.erreg.add_code(ROBO_state::ERROR_SHUTTER_DEVICE_TIMEOUT,
                                "ROBO_state::ERROR_SHUTTER_DEVICE_TIMEOUT",
                                function, log);
     common_info.erreg.add_code(ROBO_state::ERROR_SHUTTERD_DAEMON_CONNECTION,
                                "ROBO_state::ERROR_SHUTTER_DEVICE_TIMEOUT",
                                function, log);
     common_info.erreg.add_code(ROBO_state::ERROR_SHUTTERD_COMMAND_BUSY,
                                "ROBO_state::ERROR_SHUTTERD_COMMAND_BUSY",
                                function, log);
     common_info.erreg.add_code(ROBO_state::ERROR_SHUTTER_UNKNOWN_COMMAND,
                                "ROBO_state::ERROR_SHUTTER_UNKNOWN_COMMAND",
                                function, log);
     
   }
    
   /**************** ROBO_state::registry_codes ****************/


  /** \class Shutter_state
   \brief Class to track state of Shutter daemon connection.
   \details This class monitors the state of a connection to the SHUTTERD daemon. */
  class Shutter_state {

  private:

    /**************** ROBO_state::Shutter_state::swap ****************/
     /**
     This is used to swap between two Shutter state class objects.  This is used
     when constructing class objects with assignment or copy construction.
     \param [first] The first object to swap (swap into this)
     \param [second] The second object to swap (swap from this)
     */
    friend void shut_swap(ROBO_state::Shutter_state & first,
                          ROBO_state::Shutter_state & second)
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
    /**************** ROBO_state::Shutter_state::swap ****************/

  public:

    /** \var boost::mutex state_mutex
     \details Mutex to lock thread variables */
    boost::mutex state_mutex;

    /** \var ROBO_time update_time
     \details Update time for daemon operations */
    ROBO_time update_time;

    /** \var time_t status_time
     \details Time in the status loop */
    time_t status_time;

    /** \var int error_code
     \details Error code returned from the server */
    int error_code;

    /** \var bool initialized
     \details Flag if the daemon connection has been initialized */
    bool initialized;

    /** \var bool updated
     \details Flag if the status has been updated */
    bool updated;

    /** \var bool connection_open
     \details Flag if the daemon connection is open to resources */
    bool connection_open;

    /** \var int current_state
     \details Current state value of the system */
    int current_state;

    /** \var int current_state
     \details Current state value of the system */
    std::string shutter_status_string;

    /** \var int current_state
     \details Current state of the system encoded in an integer vector */ 
//    std::vector<int> shutter_system_states;

    int remote_close;
    bool ready;
    bool close_switch[2];
    bool open_switch[2];
    int mode_switch;
    bool keylock_enabled;
    bool emergency_stop;
    bool reset_pressed;
    bool timeout;
    int microcontroller;
    
    int shutter_position;
    bool shutter_ready;
    
    int load_state(std::string status_message);

    void initialize_class();

    /**************** ROBO_state::Shutter_state::Shutter_state ****************/
    /**
     This is the constructor for the SHUTTERD state class.
     */
    Shutter_state(){}

    /**************** ROBO_state::Shutter_state::~Shutter_state ****************/
    /**
     This is the deconstructor for the SHUTTERD state class.
     */
    ~Shutter_state(){}

    /**************** ROBO_state::Shutter_state::Shutter_state ****************/
    /**
     This is the copy constructor for the SHUTTERD state class.
    Shutter_state(ROBO_state::Shutter_state & in_state)
    {
      shut_swap(*this, in_state);
    }
     */

    /**************** ROBO_state::Shutter_state::Shutter_state ****************/
    /**
     This is the operator= constructor for the SHUTTERD state class.
    Shutter_state operator=(ROBO_state::Shutter_state & in_state)
    {
    	shut_swap(*this, in_state);

      return *this;
    }
     */
    /**************** ROBO_state::Shutter_state::Shutter_state ****************/
   };

}

# endif

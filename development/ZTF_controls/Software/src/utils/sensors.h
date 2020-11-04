/**
 \file sensors.h
 \brief Header file for sensor calibration and other functions
 \details Header file for sensor calibration and other functions

 Copyright (c) 2009-2011 California Institute of Technology.
 \author Dr. Reed L. Riddle  riddle@caltech.edu
 */

// Use a preprocessor statement to set a variable that checks if the header has
// already loaded...this avoids loading a header file more than once.
# ifndef ROBO_SENSORS_H
# define ROBO_SENSORS_H

// System include files
# include <string>


// Local include files
# include "basic.h"
# include "common.h"
# include "file_ops.h"
# include "robo_time.h"
# include "registry.h"
# include "calculate.h"


/** \namespace ROBO_sensor
 Namespace for the ROBO_sensor functions */
namespace ROBO_sensor {
  
  /// Defines the types of calibration functions
  enum {
    CALIBRATION_NONE,         // No calibration applied
    CALIBRATION_LINEAR        // Linear calibration (A*x+B)
  };
  
  enum Sensor_type {
    SENSOR_UNKNOWN,
    SENSOR_CONTROL_TEMPERATURE,
    SENSOR_TEMPERATURE,
    SENSOR_HUMIDITY,
    SENSOR_VACUUM_PRESSURE,
    SENSOR_PRESSURE,
    SENSOR_VOLTAGE,
    SENSOR_FLOW,
    SENSOR_DEWPOINT
  };
  
//  /// Types of sensors to calibrate
//  typedef enum {
//    TEMPERATURE_SENSOR,
//    HUMIDITY_SENSOR,
//    DEWPOINT_SENSOR,
//    PRESSURE_SENSOR,
//    UNKNOWN_SENSOR
//  } Types;
  
  
  /** \class Calibration
   \brief Sensor calibration functions
   \details Used to apply calibrations and corrections to sensors. */
  class Calibration {

  public:
    
    /** \var int cal_type
     \details Type of calibration function to apply */
    int cal_type;
    
    /** \var std::string name
     \details Name for the sensor */
    std::string name;
    
    /** \var Sensor::Types sensor_type
     \details Type of sensor being calibrated */
    ROBO_sensor::Sensor_type sensor_type;
    
    /** \var std::vector<float> coeff
     \details Calibrationc coefficients */
    std::vector<float> coeff;
    
    
    /// Class constructor
    Calibration();//{}
    
    /// Class deconstructor
    ~Calibration(){}

    float do_cal(float value);
    
    int load_cal(std::string & input);

  };

  
  
  const int NUM_PARAMS_NOT_INITIALIZED = 5;
  const int NUM_REQUIRED_PARAMETERS = 76;
  
  enum {
    OPEN_CONNECTION = CLASS_SENSORS,
    READ_DATA,
    WRITE_DATA,
    PROCESS_INFO,
    TESTING,
    SHUTDOWN,
    EMERGENCY_SHUTDOWN,
    CHECK_ERROR,
    RELOAD_CONFIGURATION,
    POWER_ON_SENSOR,
    POWER_OFF_SENSOR,
    DISABLE_WINDOW_HEATER_CONTROL,
    ENABLE_WINDOW_HEATER_CONTROL,
    DISCONNECT_CHILLER,
    CONNECT_CHILLER,
    SET_CHILLER_TEMPERATURE,
    DISCONNECT_PRESSURE_GAUGE,
    CONNECT_PRESSURE_GAUGE,
    DISABLE_CONTINUOUS_PRESSURE_MONITORING,
    ENABLE_CONTINUOUS_PRESSURE_MONITORING,
    CHANGE_CHILLER_SETPOINT,
    
    CLOSE_CONNECTION,
    
    FIRST = OPEN_CONNECTION,
    LAST  = CLOSE_CONNECTION
  };
  
  enum {
    ERROR_OPEN_CONNECTION = CLASS_SENSORS,
    ERROR_CLOSE_CONNECTION,
    ERROR_CONFIGURATION_FILE,
    ERROR_INITIALIZED,
    ERROR_INITIALIZE_FAILED,
    ERROR_NOT_INITIALIZED,
    ERROR_DAEMON_CONNECTION,
    ERROR_CONTROL_COMMAND_ERROR,
    ERROR_ERROR_CONTROL_ERROR,
    ERROR_CONTROL_STATUS_ERROR,
    ERROR_SOCKET_REQUEST_ERROR,
    ERROR_SOCKET_WRITE_ERROR,
    ERROR_SOCKET_SELECT_ERROR,
    ERROR_SOCKET_READ_ERROR,
    ERROR_DEVICE_TIMEOUT,
    ERROR_ACK_NOT_RECEIVED,
    ERROR_WRITE_DATA_ERROR,
    ERROR_TIMEOUT,
    ERROR_BAD_CONTROLLER_CONNECTION,
    ERROR_CRC_FAILURE,
    ERROR_NEED_AC_POWER_CYCLE,
    ERROR_SENSOR_NOT_CONNECTED,
    ERROR_SENSOR_NOT_POWERED,
    ERROR_BAD_INPUT_DATA,
    ERROR_BAD_SENSOR_DATA,
    ERROR_CANNOT_READ_DATA,
    ERROR_WINDOW_HEATER_SETTING,
    MONITORD_ERROR_DAEMON_CONNECTION,
    
    // Enter errors for individual sensor elements
    ERROR_STATE_CR3000,
    ERROR_STATE_CR1000,
    ERROR_STATE_LAKESHORE_1,
    ERROR_STATE_LAKESHORE_2,
    ERROR_STATE_PRESSURE,
    ERROR_STATE_WINDOW_HEATER,
    ERROR_STATE_CHILLER,
    ERROR_STATE_ERROR,
    
    ERROR_UNKNOWN,
    
    ERROR_FIRST = ERROR_OPEN_CONNECTION,
    ERROR_LAST  = ERROR_UNKNOWN
  };
  
  void registry_codes(ROBO_logfile & log);
  
  class State {
  private:
    
  public:
    
    /** \var ROBO_logfile log
     \details Log file class container */
    ROBO_logfile log;
    
    /** \var ROBO_file fits_header_file
     \details FITS image header file for the status system to use when creating
     a FITS file. */
    ROBO_file fits_header_file;
    
    /** \var boost::mutex state_mutex
     \details Mutex to lock thread variables */
    boost::mutex state_mutex;
    
    /** \var bool updated
     \details Flag if the status has been updated */
    bool updated;
    
    /** \var ROBO_time update_time
     \details The time stamp for the last status update */
    ROBO_time update_time;
    
    /** \var time_t status_time
     \details The UNIX time for the last status update */
    time_t status_time;
    
    /** \var int error_flag
     \details Flag if there are any status errors */
    int error_code;
    
    /** \var bool initialized
     \details Flag for the initialized state of the server */
    bool initialized;
    
    bool connection_open;

    int current_state;

//    /** \var std::vector<int> error_codes
//     \details All of the error codes returned by the server */
//    std::vector<int> error_codes;
   
    
    /***** Sensor Data Section *****/
    // Use this section to define the data structure for the sensors connected
    // to the system.  This section will be unique for every instrument!
    
    float cold_plate_temp[2];
    float back_plate_temp;
    float vib_temp[2];
    float cold_plate_heat;
    float vib_heat;
    float hub_temp[2];
    float post_temp[4];
    float getter_temp[2];
    float cryo_temp[2];
    float cryo_heat[2];
    float cryo_pressure[4];
    float vacuum_pressure;
    float vac_gauge_power;
    float ccd_temp[16];
    float window_heater_power;
    float window_heater_request;
    float chiller_temp;
    float chiller_setting;
    float chiller_flow;
    float cabinet_temp[5];
    float outhouse_temp;
    float tube_humidity;
    float tube_temp[7];
    float dome_humidity;
    float dome_temp[4];
    float dry_air_flow;
    float dry_air_alarm;

    float dome_dew_point;
    float tube_dew_point;
    
    
    time_t pressure_update_time;
    time_t chiller_update_time;
    time_t CR1000_update_time;
    time_t CR3000_update_time;
    time_t window_heater_update_time;
    time_t lakeshore_1_update_time;
    time_t lakeshore_2_update_time;

    int error_CR3000;
    int error_CR1000;
    int error_lakeshore_1;
    int error_lakeshore_2;
    int error_pressure;
    int error_window_heater;
    int error_chiller;
    
    
    
//    std::vector<float> control_temperature;  //Lakeshore
//    std::vector<float> temperatures;  //Campbell temperatures + other
//    std::vector<float> pressure_state;  //Pfeiffer
//    std::vector<float> power;    //Various
//    std::vector<float> humidity;  //Campbell
//    std::vector<float> dewpoint;  //Campbell
//    std::vector<float> pressures;  //Campbell glycol flow
//    //pressures + other
//    std::vector<float> chiller_data;  //Optitemp chiller
//    std::vector<float> window_heater_power;  // power value written to window heater
//    unsigned int window_heater_power_size;
    
    
    
    
    
    
    
    
    
    State();
    
    
    State(std::string logname);
 
    
    
    
    
    
    
    
    //    Sensors(const State & in_state);
    
    /**************** ROBO_sensor::State::swap ****************/
    /**
     This is used to swap between two sensor state class objects.  This is used when
     constructing class objects with assignment or copy construction.
     \param [first] The first object to swap (swap into this)
     \param [second] The second object to swap (swap from this)
     */
    friend void swap(ROBO_sensor::State & first, ROBO_sensor::State & second)
    {
      // Enable ADL (not necessary in our case, but good practice)
      using std::swap;
      
      // By swapping the members of two classes, the two classes are effectively
      // swapped.
      // std::swap(first.Sensor_type, second.Sensor_type);
      //      swap(first.update_time, second.update_time);
      swap(first.status_time, second.status_time);
      //      swap(first.error_code, second.error_code);
      //      swap(first.initialized, second.initialized);
      //      swap(first.connection_open, second.connection_open);
      //      swap(first.current_state, second.current_state);
      //      swap(first.window_heater_power, second.window_heater_power);
      //      swap(first.window_heater_power_size, second.window_heater_power_size);
      //      
      //      std::swap(first.control_temperature, second.control_temperature);
      //      std::swap(first.temperatures, second.temperatures);
      //      std::swap(first.pressure_state, second.pressure_state);
      //      std::swap(first.power, second.power);
      //      std::swap(first.humidity, second.humidity);
      //      std::swap(first.dewpoint, second.dewpoint);
      //      std::swap(first.pressures, second.pressures);
      //      std::swap(first.chiller_data, second.chiller_data);
    }   
    /**************** ROBO_sensor::State::swap ****************/

    
    /**************** ROBO_sensor::State ****************/
    /**
     This is the copy constructor for the Sensors class.
     */
    State(State & in_state)
    {
      swap(*this, in_state);
    }
    /**************** ROBO_sensor::State ****************/
    
    
    /**************** ROBO_sensor::State ****************/
    /**
     This is the copy constructor for the Power_state class.
     */
    State & operator=(ROBO_sensor::State in_state)
    {
      swap(*this, in_state);
      
      return *this;
    }
    /**************** ROBO_sensor::State ****************/
    
//    //    Sensors operator= (const Sensors & in_state);
//        /************* ROBO_sensor::Sensors *************/
//        /**
//         
//         */
//        Sensors operator= (const Sensors & in_state)
//        {
//          this->initialize_class();
//    
//          this->copy_state(in_state);
//          
//          return *this;
//        }
//        /************* ROBO_state::Sensors::Sensors *************/
    
    void initialize_class();
    
    int load_state(std::string status_message);
    
    void load_pressure(std::vector<float> & data, time_t & now, 
                     bool bad_data = false);
    
    void load_chiller(std::vector<float> & data, time_t & now, 
                       bool bad_data = false);
    
    void load_window_heater(std::vector<float> & data, time_t & now, 
                       bool bad_data = false);
    
    void load_CR1000(std::vector<float> & data, time_t & now, 
                    bool bad_data = false);

    void load_CR3000(std::vector<float> & data, time_t & now, 
                     bool bad_data = false);
    
    void load_lakeshore_1(std::vector<float> & data, time_t & now, 
                          bool bad_data = false);
    
    void load_lakeshore_2(std::vector<float> & data, time_t & now, 
                          bool bad_data = false);
    
    std::string print_telemetry_data();
    
    int print_fits_header();

    void set_error_code(int system_error, int code);

    void copy_state(ROBO_sensor::State & in_state);
    
  };
  

  
}

#endif


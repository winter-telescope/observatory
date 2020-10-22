/**
 \file chiller.cpp
 \brief Interface functions for the Optitemp Chiller controls. 
 \details This software controls a Optitemp chiller control system
 \The chiller is controlled remotely by two Love PLC controllers, one for the
 \temperature of the circulating fluid and one for the flow rate.  Both
 \controllers are on the same RS485 hardware link and both use the Modbus/RTU
 \protocol for serial communicaitons.

 Copyright (c) 2014-2017 California Institute of Technology.
 \author Dr. Reed L. Riddle  riddle@caltech.edu & John Cromer  dwc@caltech.edu
 \note
 
 */

# include "chiller.h"


/** \namespace Optitemp
 Namespace for the Optitemp chiller functions */
namespace Optitemp {
  
  /*********** Optitemp::Chiller_control::Chiller_control ***********/
  /**
   This function constructs the Optitemp Chiller_control class.
   */
  Chiller_control::Chiller_control()
  {
    // Set the log file name to the class log name
    this->log.filename = common_info.log_dir + "chiller.log";
    
    // Initialize the class
    this->initialize_class();
  };
  /*********** Optitemp::Chiller_control::Chiller_control ***********/
  
  
  /*********** Optitemp::Chiller_control::Chiller_control ***********/
  /**
   This function constructs the OptiTemp Chiller_control class, using 
   an input string to set the name of the log file.
   */
  Chiller_control::Chiller_control(std::string logname): chiller(logname)
  {
    // Set up the log file
    this->log.filename = common_info.log_dir + logname + ".log";
    
    // Initialize the class
    this->initialize_class();
  };
  /*********** Optitemp::Chiller_control::Chiller_control ***********/
  
  
  /*********** Optitemp::Chiller_control::Chiller_control ***********/
  /**
   This function constructs the Chiller_control class, using 
   an input log class to set up the log file system.
   */
  Chiller_control::Chiller_control(ROBO_logfile log_in): chiller(log_in)
  {
    // Set up the log file
    this->log = log_in;
    
    this->initialize_class();
  }
  /*********** Optitemp::Chiller_control::Chiller_control ***********/
  
  
  /********** Optitemp::Chiller_control::~Chiller_control ***********/
  /**
   This function deconstructs the Chiller_control class.
   */
  Chiller_control::~Chiller_control()
  {
    
  }
  /********** Optitemp::Chiller_control::~Chiller_control ***********/
  
  
  /********** Optitemp::Chiller_control::initialize_class ***********/
  /**
  Initializes the Chiller_control class container, called in the 
  constructors for the class.
  \note None.
  */
  void Chiller_control::initialize_class()
  {
    // Set up the function string and message stream
    std::string function("Optitemp::Chiller_control::initialize_class");
    std::stringstream message;
    
    // Load the command and error codes into the error registry
    ROBO_sensor::registry_codes(this->log);
    
    // Set the initialized flag to false
    this->initialized = false;
    
    // Read the config file
    if (this->chiller.get_config() != NO_ERROR){
      this->log.write(function, LOG_ERROR, "failed to read configuration file!");
    }
  }
  /*********** Optitemp::Chiller_control::initialize_class **********/


  /**************** Optitemp::Chiller_control::open ****************/
  /**
   Opens the communication with the  interface.
   \return NO_ERROR if the connection is opened successfully, ERROR if the 
   connection fails
   */
  int Chiller_control::open()
  {
    // Set the function information for logging
    std::string function("Optitemp::Chiller_control::open");
    std::stringstream message;
    
    // The initialized variable flags when the system has opened and set up
    // properly, If the Chiller is already initialized then just return, there
    // is no need to do all of this again.
    if (this->initialized == true){
      this->log.write(function, LOG_WARNING, "system already initialized");
    	return(NO_ERROR);
    }
    
    this->log.write(function, LOG_NO_ERROR, "opening the connection");
    
    // Connect to the unit
    int error = 0;
    error = this->chiller.controllerconnect();

    // If there is a failure log it and return an error
    if (error != NO_ERROR){
      this->log.write(function, LOG_ERROR, "connection to chiller failed!");
      return(ROBO_sensor::ERROR_OPEN_CONNECTION);
    }
    
    // Set the initialized flag if it worked
    this->initialized = true;
    this->log.write(function, LOG_NO_ERROR, "opened connection successfully");
    return(NO_ERROR);
  }
	/**************** Optitemp::Chiller_control::open ****************/
  
  
  /**************** Optitemp::Chiller_control::close ****************/
  /**
   Closes the communication with the Chiller system.
   \return NO_ERROR if the connection is closed successfully, ERROR if closing 
   the connection fails
   */
  int Chiller_control::close()
  {
    // Set the logging functions
    std::string function("Optitemp::Chiller_control::close");
    std::stringstream message;

    // Log that we're closing the connection
    this->log.write(function, LOG_NO_ERROR, "closing the connection");
    
    // Only try to close if the system initialized, otherwise just log an
    // error
    if (this->initialized == false){
      message << this->chiller.name << " system already shut down";
      this->log.write(function, LOG_NO_ERROR, message.str());
      return(NO_ERROR);
    }
    
    // Shut down the camera
    int error;
    error = this->chiller.disconnect();

    // Return an error if it doesn't work
    if (error != NO_ERROR){
      this->log.write(function, LOG_ERROR, "failed to close connection!");
      return (ROBO_sensor::ERROR_CLOSE_CONNECTION);
    }
    
    // Set the initialized flag
    this->initialized = false;
    
    // Log that we're closing the connection
    this->log.write(function, LOG_NO_ERROR, "connection closed successfully");
    
    // Return that all is good
    return (NO_ERROR);
  }
  /**************** Optitemp::Chiller_control::close ****************/
  

  /******** Optitemp::Chiller_control::change_temperature_setpoint ********/
  /**
   Calls interface routine to change the circulating fluid temperature set
   \point.  Return NO_ERROR if the command is sent successfully, ERROR if it
   \fails. 
   */
  int Chiller_control::change_temperature_setpoint( std::string & params)
  {
    // Set the logging functions
    std::string function("Optitemp::Chiller_control::change_temperature_setpoint");
    std::stringstream message;
    int error;

    //get the parameters for the call
    std::vector<std::string> tokens;
    Tokenize(params, tokens, "\t ");
    if (tokens.size() != 1){
      message << "wrong input to chiller temperature set point, "
              << "parameters: " << params;
      this->log.write(function, LOG_ERROR, message.str());
      return ERROR;
    } 

    // Log 
    message<<" Changing chiller temperature set point, " << tokens[0];
    this->log.write(function, LOG_NO_ERROR, message.str());
    message.str("");
    
    // Call to change setpoint. 
    error = chiller.change_temperature_setpoint(tokens[0]); 

    // If there is a failure log it and return an error
    if (error != NO_ERROR){
      message << this->chiller.name << " change temperature set point failed!";
      this->log.write(function, LOG_ERROR, message.str());
      return(ROBO_sensor::ERROR_WRITE_DATA_ERROR);
    }
    
    // Return success
    message << this->chiller.name << " temperature set point changed to " 
            << tokens[0] << " successfully";
    this->log.write(function, LOG_NO_ERROR, message.str());
    return(NO_ERROR);
  }
  /*********** Optitemp::Chiller_control::temperature_setpoint *************/

  
  /**************** Optitemp::Chiller_control::get_data ****************/
  /**
   Calls interface routine get chiller data.
   \return NO_ERROR if the command is sent successfully, ERROR if it fails.
   */
  int Chiller_control::get_data(std::vector<float> & data) 
  {
    // Set the logging functions
    std::string function("Optitemp::Chiller_control::get_data");
    std::stringstream message;
    std::stringstream ss;
    int error;

    // Log
    this->log.write(function, LOG_NO_ERROR, " Getting chiller data.");

    // Function call here. 
    error = get_status(data);

# if DATA_TESTING
    std::cout << "get_status return = " << error << std::endl; 
# endif

    if (error != NO_ERROR){
      this->log.write(function, LOG_ERROR, "failed to get chiller data.");
    }
    
    return(error);
  }
  /**************** Optitemp::Chiller_control::get_data ***************/
  

  /**************** Optitemp::Chiller_control::control ****************/
	/**
   This function controls the operation of the Chiller controller.  All of
   the commands should go through this routine except when necessary.
	 \param [command] The command for the camera to do
   \param [params] A string of parameters for the command
   \param [output] A string of parameters for the command
	 \return NO_ERROR if the command is executed successfully, an error code if 
   there are any problems.
   */
  int Chiller_control::control(int command, std::string params,
                               std::string & output)
  {
    // Function name string
    std::string function("Optitemp::Chiller_control::control");
    std::stringstream message("");  // A stream for messages to be logged
    int retval = ERROR;             // Return value from commands
    std::stringstream outstr("");   // Temp string for output from commands
    bool outset = false;						// Flag that output has been written

    /// The next section handles various states of operation, and makes sure
    // that the camera is not allowed to run a command that it isn't in a state
    // to run properly.  This avoids crashes and memory errors, so make sure any
    // changes to the code include making sure that commands only run when
    // it is appropriate and safe to do so.
    
    // Don't run commands if the connection hasn't been opened
    if (this->initialized == false){
      switch (command) {
        case ROBO_sensor::CLOSE_CONNECTION:
        case ROBO_sensor::WRITE_DATA:
        case ROBO_sensor::READ_DATA:
          message << "system not initialized, cannot run command "
                  << common_info.comreg.get_code(command);
          this->log.write(function, LOG_ERROR, message.str());
          outstr << ROBO_sensor::ERROR_NOT_INITIALIZED;
          output = outstr.str();
          return (ROBO_sensor::ERROR_NOT_INITIALIZED);
          break;
        default:
          ;
      }
    }
    
    // Don't try to open the Chiller controller if it is already open
    else if (this->initialized == true){
      switch (command) {
        case ROBO_sensor::OPEN_CONNECTION:
          message << "system already initialized, cannot run command "
                  << common_info.comreg.get_code(command);
          this->log.write(function, LOG_WARNING, message.str());
          outstr << NO_ERROR;
          output = outstr.str();
          return (NO_ERROR);
          break;
        default:
          ;
      }
    }
    
    // Check the configuration file to see if it was updated
    if (this->chiller.config.modified() == true){
      if (this->chiller.get_config() != NO_ERROR){
        this->log.write(function, LOG_ERROR, "failed to read configuration file!");
        return(ERROR);
      }
    }
    
    // Now, go through the possible commands and run them.
    switch (command){
        
        // Open the connection up for operations
      case ROBO_sensor::OPEN_CONNECTION:
        retval = this->open();
        break;

        // Close the connection to terminate operations
      case ROBO_sensor::CLOSE_CONNECTION:
        retval = this->close();
        break;

        // Set the temperature
      case ROBO_sensor::SET_CHILLER_TEMPERATURE:
        retval = this->change_temperature_setpoint(params);
        break;

        // Get chiller status data
      case ROBO_sensor::READ_DATA:
      {
        std::vector<float> data;
        
        retval = this->get_data(data);
        outstr << retval << " temperature=" << data[0] 
                << " set_point=" << data[1]
                << " flow=" << data[2];
        std::cout << "Chiller_control.control:  "<< outstr.str() << std::endl;
        outset = true;
        break;
      }
        // Catch any other commands, nothing else should do anything
      default:
        message << this->chiller.name 
                << " unknown command! Entered command code: " << command;
        this->log.write(function, LOG_ERROR, message.str());
        retval = ERROR_UNKNOWN;
        
    }
    
    // Return the flag from the command
    if (outset == false){
    	outstr << retval;
    }
    output = outstr.str();
    return(retval);
  }
  /**************** Optitemp::Chiller_control::control ****************/
  
  
  /*************** Optitemp::Chiller_control::get_status **************/
  /** Reads the status of the Chiller control system.
   \note None.
   */
  int Chiller_control::get_status(std::vector<float> & data)
  {
    // Function name string
    std::string function("Optitemp::Chiller_control::get_status");
    std::stringstream message;
    int error = ERROR;
    
    error = this->chiller.get_state(data);
    if (error != NO_ERROR){
      message << "error reading chiller data, error code: " 
              << common_info.erreg.get_code(error);
      this->log.write(function, LOG_ERROR, message.str());
    }
 
    // Return the error code from the pressure read
    return(error);
  }
  /*************** Optitemp::Chiller_control::get_status **************/
  
}

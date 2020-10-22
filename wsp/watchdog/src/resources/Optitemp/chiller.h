/**
 \file chiller.h
 \brief Interface functions for Opti Temp Chiller.
 \details This software controls Opti Temp Chiller.
 
 Copyright (c) 2014-2017 California Institute of Technology.
 \author Dr. Reed L. Riddle  riddle@caltech.edu
 \note
 
 */

# ifndef CHILLER_H
# define CHILLER_H

# include <iostream>

# include "common.h"
# include "robo_time.h"
# include "file_ops.h"
# include "state.h"
# include "chiller_interface.h"


/** \namespace Optitemp
 Namespace for the Opti Temp functions */
namespace Optitemp {
  
  
  /** \class Chiller_control
   \brief Class for control of the Opti Temp Chiller controller.
   \details   Control software for the Opti Temp Chiller controller, does
   all of the driver control functions for the system, communicates with the 
   interface software to set up parameters, and everything else necessary to run
   the system. */
  class Chiller_control {
  private:
    
    /** \var bool initialized
     \details Flags if the software has initialized. */
    bool initialized;
    
    /** \var ROBO_logfile log
     \details Log file class container */
    ROBO_logfile log;
    
    void initialize_class();
    
    // Open the connection
    int open();
    
    // Close connection.
    int close();

    // Get temperature, setpoint and flow 
    int get_data(std::vector<float> & data);    

  public:
    
    /** \var Optitemp::Interface chiller
     \details  */
    Optitemp::Chiller_interface chiller;
    
    // Constructors
    Chiller_control();
    Chiller_control(std::string logname_in);
    Chiller_control(ROBO_logfile log_in);
    
    // Destructor
    ~Chiller_control();
    
    int control(int command, std::string params,
                std::string & output);
    
    int get_status(std::vector<float> & data);

    // Change fluid temperature  
    int change_temperature_setpoint(std::string & params);

  };
  
}

# endif

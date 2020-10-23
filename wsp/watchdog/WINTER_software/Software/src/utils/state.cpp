 /**
 \file state.cpp
\brief State classes for Robo_AO robotic system.
 \details This file defines the classes for the states of the various
 ROBO subsystems.  States monitor what is happening in each of the subsystems
 during operations.
 
 Copyright (c) 2009-2013 California Institute of Technology.
 \author Dr. Reed L. Riddle  riddle@caltech.edu
 \note
 */

// Local include files
# include "state.h"


/** \namespace QUEUE
 Namespace for the queue control functions. */
namespace ROBO_state {
  
  
  /**************** ROBO_state::Daemon_state::Daemon_state ****************/
  /**

   */
  Daemon_state::Daemon_state()
  {
    this->daemon_shutdown = false;
    this->command = NO_COMMAND;
    this->timeout = 0;
    this->waiting = false;
    
    this->initialize_command_error();
    this->initialize_error();
  }
  /**************** ROBO_state::Daemon_state::Daemon_state ****************/

  
  /*********** ROBO_state::Daemon_state::initialize_command_error ***********/
  /**
   
   */
  void Daemon_state::initialize_command_error()
  {
    this->command_error = NO_ERROR;
    this->old_command_error = NO_ERROR;
    this->command_error_found = false;
    this->command_error_time = 0;
    this->command_attempts = 0;
  }
  /*********** ROBO_state::Daemon_state::initialize_command_error ***********/

  
  /*************** ROBO_state::Daemon_state::initialize_error ***************/
  /**
   
   */
  void Daemon_state::initialize_error()
  {
    this->error = NO_ERROR;
    this->error_found = false;
    this->old_error = NO_ERROR;
    this->error_time = 0;
    this->error_attempts = 0;
  }
  /*************** ROBO_state::Daemon_state::initialize_error ***************/

 
  
  /************* ROBO_state::LGS_daemon_state::LGS_daemon_state *************/
  /**
   
   */
  LGS_daemon_state::LGS_daemon_state()
  {
    this->autowindow_closed = true;
    this->window_time = 0;
    this->error_code = NO_ERROR;
    this->laser_temperature = 0;
    this->chiller_temperature = 0;
    this->laser_current = 0;
    this->window_closed = true;
    this->laser_time = 0;
    this->shutter_closed = false;
    this->interlock_closed = false;
    this->laser_on = false;
    this->laser_power = 0;
  }
  /************* ROBO_state::LGS_daemon_state::LGS_daemon_state *************/


  /************* ROBO_state::LGS_daemon_state::load_state *************/
  /**
   
   */
  int LGS_daemon_state::load_state(std::string status_message)
  {
    // Break the message into tokens
    std::vector<std::string> tokens;  // Temporary tokens
    int err = Tokenize(status_message, tokens, "|");
    //      std::cout << "    LGS state: " << status_message << " " << tokens.size() << std::endl;
    //      std::cout << tokens[0] << " : " << tokens[1] << " : " << tokens[2] << std::endl;
    if (err != 3){
      return(ERROR);
    }
    
    std::vector<std::string> tokens2;  // Temporary tokens
    err = Tokenize(tokens[0], tokens2, " \t");
    //      std::cout << "  "  << tokens2.size();
    // Return an error if there are not the rught number of tokens
    if (err != 13){
      return(ERROR);
    }
    
    std::vector<std::string> tokens3;  // Temporary tokens
    err = Tokenize(tokens[2], tokens3, " \t\r\n");
    //      std::cout << "   " << tokens3.size() << std::endl;
    // Return an error if there are not the rught number of tokens
    if (err != 4){
      return(ERROR);
    }
    
    this->laser_time = atoi(tokens2[1].c_str());
    if (tokens2[2].compare("ON") == 0){
      this->laser_on = true;
    }
    else {
      this->laser_on = false;
    }
    if (tokens2[3].compare("OPEN") == 0){
      this->interlock_closed = false;
    }
    else {
      this->interlock_closed = true;
    }
    if (tokens2[4].compare("OPEN") == 0){
      this->shutter_closed = false;
    }
    else {
      this->shutter_closed = true;
    }
    this->laser_power = atof(tokens2[5].c_str());
    this->laser_temperature = atof(tokens2[6].c_str());
    this->laser_current = atof(tokens2[7].c_str());
    this->chiller_temperature = atof(tokens2[10].c_str());
    
    int temp_autowindow = atoi(tokens3[2].c_str());
    if (temp_autowindow == NO_ERROR){
      this->autowindow_closed = false;
    }
    else {
      this->autowindow_closed = true;
    }
    this->window_time = atoi(tokens3[3].c_str());
    this->error_code = atoi(tokens3[0].c_str());
    
    //      std::cout << "    LGS state: " << status_message << " " << tokens.size() << std::endl;
    //      std::cout << "    LGS state: " << tokens[16] << " " << tokens[16].compare("OPEN") << std::endl;
    //      std::cout << "    LGS state: " << tokens[tokens.size()-3] << " " << tokens[tokens.size()-3].compare("OPEN")
    //          << std::endl;
    if (tokens3[1].compare("OPEN") == 0){
      this->window_closed = false;
    }
    else {
      this->window_closed = true;
    }
    
    return(NO_ERROR);
  }
  /************* ROBO_state::LGS_daemon_state::load_state *************/

  
  
  /************* ROBO_state::AO_daemon_state::AO_daemon_state *************/
  /**
   
   */
  AO_daemon_state::AO_daemon_state()
  {
    this->focus_limits[0] = 0.02;
    this->focus_limits[1] = 0.05;
    this->intensity_limits[0] = 50;
    this->intensity_limits[1] = 100;
    this->intensity_limits[2] = 200;
    this->focus_update = false;
    this->status_time = 0;
    this->last_status_time = 0;
    this->num_obs_seconds = 0;
  }
  /************* ROBO_state::AO_daemon_state::AO_daemon_state *************/

  
  /************* ROBO_state::AO_daemon_state::load_state *************/
  /**
   
   */
  int AO_daemon_state::load_state(std::string status_message)
  {
    // Break the message into tokens
    std::vector<std::string> tokens;  // Temporary tokens
    int err = Tokenize(status_message, tokens, " \t\r\n\0");
    //        std::cout << "    AO state: " << status_message << " " << tokens.size() << std::endl;
    if (err != 22){
      return(ERROR);
    }
    
    //        AO client mesasge: STATUS 1374989907       100.999114 119841   1199.24 1199 2 1263
    //          -9999.000000 0  -9999.00 -9999 0 0 9831 33550 20640 -67.7085 -201.054 0.255194 124.085 -0.00609377
    
    this->last_status_time = this->status_time;
    this->status_time = atoi(tokens[1].c_str());
    //        std::cout << tokens[1] << " " << this->status_time << std::endl;
    
    this->wfs_run_time = atof(tokens[2].c_str());
    //        std::cout << tokens[2] << " " << this->wfs_run_time << std::endl;
    this->num_wfs_frames = atof(tokens[3].c_str());
    this->wfs_current_frame_rate = atof(tokens[4].c_str());
    this->wfs_loop_count = atof(tokens[5].c_str());
    this->wfs_frame_skips = atof(tokens[6].c_str());
    this->wfs_ndropped_frames = atof(tokens[7].c_str());
    
    this->tt_run_time = atof(tokens[8].c_str());
    this->num_tt_frames = atof(tokens[9].c_str());
    this->tt_current_frame_rate = atof(tokens[10].c_str());
    this->tt_loop_count = atof(tokens[11].c_str());
    this->tt_frame_skips = atof(tokens[12].c_str());
    this->tt_ndropped_frames = atof(tokens[13].c_str());
    
    this->min = atof(tokens[14].c_str());
    this->max = atof(tokens[15].c_str());
    this->median = atof(tokens[16].c_str());
    this->focus = atof(tokens[17].c_str());
    this->leaky_average = atof(tokens[18].c_str());
    this->r0_est = atof(tokens[19].c_str());
    this->average_intensity = atof(tokens[20].c_str());
    //        std::cout << tokens[20] << " " << this->average_intensity << std::endl;
    this->secondary_focus = atof(tokens[21].c_str());
    //        std::cout << tokens[21] << " " << this->secondary_focus << std::endl;
    //        std::cout << "----" << std::endl;
    
    return(NO_ERROR);
  }
  /************* ROBO_state::AO_daemon_state::load_state *************/

  
  
  /************* ROBO_state::Tip_Tilt::Tip_Tilt *************/
  /**
   
   */
  Tip_Tilt::Tip_Tilt()
  {
    this->low_light_value = 0.0;
    this->centroid[0] = 0.0;
    this->centroid[1] = 0.0;
    this->fwhm = 0;
    this->platescale = 0;
    this->max_flux = 0;
    this->rotation = 0;
    this->error = NO_ERROR;
    this->updated = false;
    this->current_time = get_current_time_double();
    this->image_good = false;
  }
  /************* ROBO_state::Tip_Tilt::Tip_Tilt *************/

  
  /************* ROBO_state::Tip_Tilt::load_state *************/
  /**
   
   */
  int Tip_Tilt::load_state(std::string status_message)
  {
    // Break the message into tokens
    std::vector<std::string> tokens;  // Temporary tokens
    int err = Tokenize(status_message, tokens, " \t\r\n\0");
    //        std::cout << "    state: " << status_message << " " << tokens.size() << std::endl;
    if (err != 7){
      boost::lock_guard<boost::mutex> lock(this->state_mutex);
      this->updated = false;
      this->image_good = false;
      this->error = ERROR;
      return(ERROR);
    }
    
    boost::lock_guard<boost::mutex> lock(this->state_mutex);
    this->current_time = atof(tokens[1].c_str());
    this->error = atoi(tokens[2].c_str());
    this->centroid[0] = atof(tokens[3].c_str());
    this->centroid[1] = atof(tokens[4].c_str());
    this->image_good = atoi(tokens[5].c_str());
    this->rotation = atof(tokens[6].c_str());
    
    this->updated = true;
    
    return(NO_ERROR);
  }
  /************* ROBO_state::Tip_Tilt::load_state *************/

  
  /************* ROBO_state::Tip_Tilt::server_message *************/
  /**
   
   */
  std::string Tip_Tilt::server_message()
  {
    std::stringstream message;
    
    message << TCPIP::TIP_TILT_MESSAGE << " " << std::setprecision(16) << this->current_time << " "
    << this->error << " " << std::setprecision(4) << this->centroid[0]
    << " " << this->centroid[1] << " " << this->image_good << " "
    << this->rotation;
    
    return(message.str());
  }
  /************* ROBO_state::Tip_Tilt::server_message *************/

  
  
  
  /**************** ROBO_state::Motion::Motion ****************/
  /**
   This function constructs the Motion state class
   */
  Motion::Motion()
  {
    // Initialize the class
    this->initialize_class();
  };
  /**************** ROBO_state::Motion::Motion ****************/
  
  
  /**************** ROBO_state::Motion::~Motion ****************/
  /**
   This is the destructor for the Motion state class.
   */
  Motion::~Motion()
  {
  };
  /**************** ROBO_state::Motion::~Motion ****************/
  
  
//  /**************** FITS_file::swap ****************/
//  /**
//   This is used to swap between two Motion state class objects.  This is used when
//   constructing class objects with assignment or copy construction.
//   \param [first] The first object to swap (swap into this)
//   \param [second] The second object to swap (swap from this)
//   */
//  void Motion::swap(ROBO_state::Motion & first, ROBO_state::Motion & second)
//  {
//    // By swapping the members of two classes, the two classes are effectively
//    // swapped.
//    std::swap(first.update_time, second.update_time);
//    std::swap(first.status_time, second.status_time);
//    std::swap(first.error_code, second.error_code);
//    std::swap(first.initialized, second.initialized);
//    std::swap(first.connection_open, second.connection_open);
//    std::swap(first.current_state, second.current_state);
//  }
//  /**************** FITS_file::swap ****************/
  
  
  /**************** ROBO_state::Motion::Motion ****************/
  /**
   This is the copy constructor for the Motion state class.
   */
  Motion::Motion(ROBO_state::Motion & in_motion)
  {
  	motion_swap(*this, in_motion);
//    this->swap(*this, in_motion);
  };
  /**************** Motion::Motion ****************/
  
  
//  /**************** ROBO_state::Motion::Motion ****************/
//  /**
//   This is the operator= constructor for the Motion state class.
//   */
//  Motion::Motion operator=(ROBO_state::Motion & in_motion)
//  {
////    swap(*this, in_motion);
//    this->swap(*this, in_motion);
//    
//    return *this;
//  }
//  /**************** ROBO_state::Motion::Motion ****************/
  
  
  /************ ROBO_state::Motion::initialize_class ************/
  /**
   Initializes the motion state class variables to default values.
   */
  void Motion::initialize_class()
  {
    this->status_time = 0;
    this->error_code = NO_ERROR;
    this->initialized = false;
    this->connection_open = false;
    this->current_state = NO_ERROR;
    this->moving = false;
    this->current_focus = 0;
    this->updated = false;
  }
  /************ ROBO_state::Motion::initialize_class ************/
  
  /************* ROBO_state::Motion::load_state *************/
  /**
   Loads the status string into the state class variables
   \param[status_message] A formatted string that contains the status
   */
  int Motion::load_state(std::string status_message)
  {
    std::stringstream message;
    // Break the message into tokens
    std::vector<std::string> tokens;  // Temporary tokens
    int err = Tokenize(status_message, tokens, " ");
    if (err < ROBO_state::NUM_MOTION_PARAMS_NOT_INITIALIZED){
      return(ERROR);
    }
//    std::cout << "load_state Tokenize return = " << err << " " <<  ROBO_state::NUM_MOTION_PARAMS_NOT_INITIALIZED 
//    		<< " " << ROBO_state::NUM_REQUIRED_MOTION_PARAMETERS << std::endl;

    //Unix time
    this->status_time = atoi(tokens[1].c_str());

    //Date and clock-time
    std::string temp = tokens[2] + " " + tokens[3];
    this->update_time.set_time(temp, ROBO_time::TIMEFMT_Y_M_D_H_M_S);

    this->initialized = atoi(tokens[4].c_str());

    // If the system is not initialized, then there are only
    // NUM_MOTION_PARAMS_NOT_INITIALIZED parameters

    if (err == ROBO_state::NUM_MOTION_PARAMS_NOT_INITIALIZED){
      this->error_code = NO_ERROR;
    }

    else if (err >= ROBO_state::NUM_REQUIRED_MOTION_PARAMETERS)
    {
      this->error_code = atoi(tokens[5].c_str());
      int num_controller_error_states = atoi(tokens[6].c_str());
      int num_inst_positions = atoi(tokens[7].c_str());
      int num_axes_positions = atoi(tokens[8].c_str());
      int num_on_target_status_values = atoi(tokens[9].c_str());
      int num_pivot_point_position_values = atoi(tokens[10].c_str());

//      std::cout << num_controller_error_states << "|" << num_inst_positions 
//      		 << "|" << num_axes_positions << "|" << num_on_target_status_values << "|"
//		<< num_pivot_point_position_values << "|" << ROBO_state::NUM_REQUIRED_MOTION_PARAMETERS + num_controller_error_states
//	  + num_inst_positions
//                + num_axes_positions
//                + num_on_target_status_values
//	  + num_pivot_point_position_values << std::endl;

      if (err != (ROBO_state::NUM_REQUIRED_MOTION_PARAMETERS
		  + num_controller_error_states
		  + num_inst_positions
                  + num_axes_positions
                  + num_on_target_status_values
		  + num_pivot_point_position_values ) ) {
std::cout << "err != to num req. params + value count!" << std::endl;
std::cout << "Total tokenized parameters = " << err << std::endl;
std::cout << "num_controller_error_states = " << num_controller_error_states << std::endl;
std::cout << "num_inst_positions = " << num_inst_positions << std::endl;
std::cout << "num_axes_positions = " << num_axes_positions << std::endl;
std::cout << "num_on_target_status_values = " << num_on_target_status_values << std::endl;
std::cout << "num_pivot_point_position_values = " << num_pivot_point_position_values << std::endl;
        return(ERROR);
      }

      int i;
      int j = ROBO_state::NUM_REQUIRED_MOTION_PARAMETERS;
      std::vector<int> temp_int;
      std::vector<float> temp_float;
//      this->controller_error_state.clear();
      for (i = 0; i < num_controller_error_states; i++){
      	temp_int.push_back(atof(tokens[j].c_str()));
 //       this->controller_error_state.push_back(atof(tokens[j].c_str()));
        j++;
      }
      this->controller_error_state = temp_int;
      
      i = 0;
//      this->inst_positions.clear();
      for (i = 0; i < num_inst_positions; i++){
      	temp_float.push_back(atof(tokens[j].c_str()));
//        this->inst_positions.push_back(atof(tokens[j].c_str()));
//        if (i == 2){
//        	this->current_focus = this->inst_positions[i];
//        }
        j++;
      }
      this->inst_positions = temp_float;
    	this->current_focus = this->inst_positions[2];

      i = 0;
      temp_float.clear();
//      this->axes_positions.clear();
      for (i = 0; i < num_axes_positions; i++){
      	temp_float.push_back(atof(tokens[j].c_str()));
//        this->axes_positions.push_back(atof(tokens[j].c_str()));
        j++;
      }
      this->axes_positions = temp_float;

      i = 0;
      temp_int.clear();
//      this->axes_on_target_status_values.clear();
      for (i = 0; i < num_on_target_status_values; i++){
      	temp_int.push_back(atof(tokens[j].c_str()));
//       this->axes_on_target_status_values.push_back(atof(tokens[j].c_str()));
        j++;
      }
      this->axes_on_target_status_values = temp_int;

      i = 0;
      temp_float.clear();
//      this->pivot_point_position.clear();
      for (i = 0; i < num_pivot_point_position_values; i++){
      	temp_float.push_back(atof(tokens[j].c_str()));
//        this->pivot_point_position.push_back(atof(tokens[j].c_str()));
        j++;
      }
      this->pivot_point_position = temp_float;

    }

    // Return an error if there are not the right number of tokens
    else {
std::cout << "err <  to num req. params!" << std::endl;
      return(ERROR);
    }
//    std::cout << "current focus: " << this->current_focus << std::flush;
//    std::cout << this->inst_positions[2] << std::endl;

    boost::lock_guard<boost::mutex> lock(this->state_mutex);
    this->updated = true;
    return(NO_ERROR);
  }
  /************* ROBO_state::Motion::load_state *************/

   /************ ROBO_state::Motion::copy_state ************/
  /**
   Copies the Motion state class variables into a new class variable.
   \param[in_state] A Motion state class container
   \note This is used for the copy and operator= constructors
   */
  void Motion::copy_state(const Motion & in_state)
  {
    this->update_time = in_state.update_time;
  }
  /************ ROBO_state::Motion::copy_state ************/ 

  /************ ROBO_state::motion_registry_codes ************/
  void motion_registry_codes(ROBO_logfile & log)
  {
    
    std::string function("ROBO_state::motion_registry_codes");

    if (common_info.comreg.check_registry(ROBO_registry::MOTION_REGISTRY) == true){
        return;
    }

    common_info.comreg.add_registry(ROBO_registry::MOTION_REGISTRY);
    
    common_info.comreg.add_code(ROBO_state::MOTION_OPEN_CONNECTION,
                                "ROBO_state::MOTION_OPEN_CONNECTION",
                                function, common_info.log);

    common_info.comreg.add_code(ROBO_state::MOTION_READ_DATA,
                                "ROBO_state::MOTION_READ_DATA",
                                function, common_info.log);

    common_info.comreg.add_code(ROBO_state::MOTION_PROCESS_INFO,
                                "ROBO_state::MOTION_PROCESS_INFO",
                                function, common_info.log);

    common_info.comreg.add_code(ROBO_state::MOTION_TESTING,
                                "ROBO_state::MOTION_TESTING",
                                function, common_info.log);

    common_info.comreg.add_code(ROBO_state::MOTION_SHUTDOWN,
                                "ROBO_state::MOTION_SHUTDOWN",
                                function, common_info.log);

    common_info.comreg.add_code(ROBO_state::MOTION_EMERGENCY_SHUTDOWN,
                                "ROBO_state::MOTION_EMERGENCY_SHUTDOWN",
                                function, common_info.log);

    common_info.comreg.add_code(ROBO_state::MOTION_CHECK_ERROR,
                                "ROBO_state::MOTION_CHECK_ERROR",
                                function, common_info.log);

    common_info.comreg.add_code(ROBO_state::MOTION_RELOAD_CONFIGURATION,
                                "ROBO_state::MOTION_RELOAD_CONFIGURATION",
                                function, common_info.log);

    common_info.comreg.add_code(ROBO_state::MOTION_AXIS_MOVE_ABS,
                                "ROBO_state::MOTION_AXIS_MOVE_ABS",
                                function, common_info.log);

    common_info.comreg.add_code(ROBO_state::MOTION_AXIS_MOVE_REL,
                                "ROBO_state::MOTION_AXIS_MOVE_REL",
                                function, common_info.log);

    common_info.comreg.add_code(ROBO_state::MOTION_AXIS_GET_INFO,
                                "ROBO_state::MOTION_AXIS_GET_INFO",
                                function, common_info.log);

    common_info.comreg.add_code(ROBO_state::MOTION_AXIS_HOME_AXIS,
                                "ROBO_state::MOTION_AXIS_HOME_AXIS",
                                function, common_info.log);

    common_info.comreg.add_code(ROBO_state::MOTION_AXIS_HOME_ALL,
                                "ROBO_state::MOTION_AXIS_HOME_ALL",
                                function, common_info.log);

    common_info.comreg.add_code(ROBO_state::MOTION_SEND_COMMAND,
                                "ROBO_state::SEND_COMMAND",
                                function, common_info.log);

    common_info.comreg.add_code(ROBO_state::MOTION_SET_PIVOT,
                                "ROBO_state::MOTION_SET_PIVOT",
                                function, common_info.log);

    common_info.comreg.add_code(ROBO_state::MOTION_EMERGENCY_STOP,
                                "ROBO_state::MOTION_EMERGENCY_STOP",
                                function, common_info.log);

    common_info.comreg.add_code(ROBO_state::MOTION_CLOSE_CONNECTION,
                                "ROBO_state::MOTION_CLOSE_CONNECTION",
                                function, common_info.log);




    common_info.erreg.add_code(ROBO_state::ERROR_MOTION_OPEN_CONNECTION,
                               "ROBO_state::ERROR_MOTION_OPEN_CONNECTION",
                               function, common_info.log);

    common_info.erreg.add_code(ROBO_state::ERROR_MOTION_INITIALIZED,
                               "ROBO_state::ERROR_MOTION_INITIALIZED",
                               function, common_info.log);

    common_info.erreg.add_code(ROBO_state::ERROR_MOTION_INITIALIZE_FAILED,
                               "ROBO_state::ERROR_MOTION_INITIALIZE_FAILED",
                               function, common_info.log);

    common_info.erreg.add_code(ROBO_state::ERROR_MOTION_DAEMON_CONNECTION,
                               "ROBO_state::ERROR_MOTION_DAEMON_CONNECTION",
                               function, common_info.log);

    common_info.erreg.add_code(ROBO_state::ERROR_MOTION_CONTROL_COMMAND_ERROR,
                               "ROBO_state::ERROR_MOTION_CONTROL_COMMAND_ERROR",
                               function, common_info.log);

    common_info.erreg.add_code(ROBO_state::ERROR_MOTION_ERROR_CONTROL_ERROR,
                               "ROBO_state::ERROR_MOTION_ERROR_CONTROL_ERROR",
                               function, common_info.log);

    common_info.erreg.add_code(ROBO_state::ERROR_MOTION_CONTROL_STATUS_ERROR,
                               "ROBO_state::ERROR_MOTION_CONTROL_STATUS_ERROR",
                               function, common_info.log);

    common_info.erreg.add_code(ROBO_state::ERROR_MOTION_SOCKET_WRITE_ERROR,
                               "ROBO_state::ERROR_MOTION_SOCKET_WRITE_ERROR",
                               function, common_info.log);

    common_info.erreg.add_code(ROBO_state::ERROR_MOTION_SOCKET_SELECT_ERROR,
                               "ROBO_state::ERROR_MOTION_SOCKET_SELECT_ERROR",
                               function, common_info.log);

    common_info.erreg.add_code(ROBO_state::ERROR_MOTION_SOCKET_READ_ERROR,
                               "ROBO_state::ERROR_MOTION_SOCKET_READ_ERROR",
                               function, common_info.log);

    common_info.erreg.add_code(ROBO_state::ERROR_MOTION_DEVICE_TIMEOUT,
                               "ROBO_state::ERROR_MOTION_DEVICE_TIMEOUT",
                               function, common_info.log);

    common_info.erreg.add_code(ROBO_state::ERROR_MOTION_AXIS_MOVE_ABS,
                                "ROBO_state::ERROR_MOTION_AXIS_MOVE_ABS",
                                function, common_info.log);

    common_info.erreg.add_code(ROBO_state::ERROR_MOTION_AXIS_HOME_AXIS,
                                "ROBO_state::ERROR_MOTION_AXIS_HOME_AXIS",
                                function, common_info.log);

    common_info.erreg.add_code(ROBO_state::ERROR_MOTION_AXIS_HOME_ALL,
                                "ROBO_state::ERROR_MOTION_AXIS_HOME_ALL",
                                function, common_info.log);

    common_info.erreg.add_code(ROBO_state::ERROR_MOTION_SEND_COMMAND,
                                "ROBO_state::ERROR_MOTION_SEND_COMMAND",
                                function, common_info.log);

    common_info.erreg.add_code(ROBO_state::ERROR_MOTION_SET_PIVOT,
                                "ROBO_state::ERROR_MOTION_SET_PIVOT",
                                function, common_info.log);

    common_info.erreg.add_code(ROBO_state::ERROR_MOTION_AXIS_MOVE_REL,
                                "ROBO_state::ERROR_MOTION_AXIS_MOVE_REL",
                                function, common_info.log);

    common_info.erreg.add_code(ROBO_state::ERROR_MOTION_UNKNOWN,
                               "ROBO_state::ERROR_MOTION_UNKNOWN",
                               function, common_info.log);

    common_info.erreg.add_code(ROBO_state::ERROR_MOTION_INVALID_AXIS_IDENTIFIER,
                                "ROBO_state::ERROR_MOTION_INVALID_AXIS_IDENTIFIER",
                                function, common_info.log);

    common_info.erreg.add_code(ROBO_state::ERROR_MOTION_INVALID_PIVOT_POINT_ID,
                                "ROBO_state::ERROR_MOTION_INVALID_PIVOT_POINT_ID",
                                function, common_info.log);

  }

  /************ ROBO_state::illuminator_registry_codes ************/
  void illuminator_registry_codes(ROBO_logfile & log)
  {

    std::string function("ROBO_state::illuminator_registry_codes");

    if (common_info.comreg.check_registry(ROBO_registry::ILLUMINATOR_REGISTRY) == true){
        return;
    }

    common_info.comreg.add_registry(ROBO_registry::ILLUMINATOR_REGISTRY);

    common_info.comreg.add_code(ROBO_state::ILLUMINATOR_OPEN_CONNECTION,
                                "ROBO_state::ILLUMINATOR_OPEN_CONNECTION",
                                function, common_info.log);

    common_info.comreg.add_code(ROBO_state::ILLUMINATOR_READ_DATA,
                                "ROBO_state::ILLUMINATOR_READ_DATA",
                                function, common_info.log);

    common_info.comreg.add_code(ROBO_state::ILLUMINATOR_WRITE_DATA,
                                "ROBO_state::ILLUMINATOR_WRITE_DATA",
                                function, common_info.log);

    common_info.comreg.add_code(ROBO_state::ILLUMINATOR_PROCESS_INFO,
                                "ROBO_state::ILLUMINATOR_PROCESS_INFO",
                                function, common_info.log);

    common_info.comreg.add_code(ROBO_state::ILLUMINATOR_TESTING,
                                "ROBO_state::ILLUMINATOR_TESTING",
                                function, common_info.log);

    common_info.comreg.add_code(ROBO_state::ILLUMINATOR_SHUTDOWN,
                                "ROBO_state::ILLUMINATOR_SHUTDOWN",
                                function, common_info.log);

    common_info.comreg.add_code(ROBO_state::ILLUMINATOR_EMERGENCY_SHUTDOWN,
                                "ROBO_state::ILLUMINATOR_EMERGENCY_SHUTDOWN",
                                function, common_info.log);

    common_info.comreg.add_code(ROBO_state::ILLUMINATOR_CHECK_ERROR,
                                "ROBO_state::ILLUMINATOR_CHECK_ERROR",
                                function, common_info.log);

    common_info.comreg.add_code(ROBO_state::ILLUMINATOR_RELOAD_CONFIGURATION,
                                "ROBO_state::ILLUMINATOR_RELOAD_CONFIGURATION",
                                function, common_info.log);

    common_info.comreg.add_code(ROBO_state::ILLUMINATOR_RESET,
                                "ROBO_state::ILLUMINATOR_RESET",
                                function, common_info.log);

    common_info.comreg.add_code(ROBO_state::ILLUMINATOR_INIT,
                                "ROBO_state::ILLUMINATOR_INIT",
                                function, common_info.log);

    common_info.comreg.add_code(ROBO_state::ILLUMINATOR_TRIGGER,
                                "ROBO_state::ILLUMINATOR_TRIGGER",
                                function, common_info.log);

    common_info.comreg.add_code(ROBO_state::ILLUMINATOR_START_SEQUENCE,
                                "ROBO_state::ILLUMINATOR_START_SEQUENCE",
                                function, common_info.log);

    common_info.comreg.add_code(ROBO_state::ILLUMINATOR_SET_FILTER,
                                "ROBO_state::ILLUMINATOR_SET_FILTER",
                                function, common_info.log);

    common_info.comreg.add_code(ROBO_state::ILLUMINATOR_SET_SEQUENCE,
                                "ROBO_state::ILLUMINATOR_SET_SEQUENCE",
                                function, common_info.log);

    common_info.comreg.add_code(ROBO_state::ILLUMINATOR_CLOSE_CONNECTION,
                                "ROBO_state::ILLUMINATOR_CLOSE_CONNECTION",
                                function, common_info.log);



    common_info.erreg.add_code(ROBO_state::ERROR_ILLUMINATOR_OPEN_CONNECTION,
                                "ROBO_state::ERROR_ILLUMINATOR_OPEN_CONNECTION",
                                function, common_info.log);

    common_info.erreg.add_code(ROBO_state::ERROR_ILLUMINATOR_CLOSE_CONNECTION,
                                "ROBO_state::ERROR_ILLUMINATOR_CLOSE_CONNECTION",
                                function, common_info.log);

    common_info.erreg.add_code(ROBO_state::ERROR_ILLUMINATOR_INITIALIZED,
                                "ROBO_state::ERROR_ILLUMINATOR_INITIALIZED",
                                function, common_info.log);

    common_info.erreg.add_code(ROBO_state::ERROR_ILLUMINATOR_INITIALIZE_FAILED,
                                "ROBO_state::ERROR_ILLUMINATOR_INITIALIZE_FAILED",
                                function, common_info.log);

    common_info.erreg.add_code(ROBO_state::ERROR_ILLUMINATOR_NOT_INITIALIZED,
                                "ROBO_state::ERROR_ILLUMINATOR_NOT_INITIALIZED",
                                function, common_info.log);

    common_info.erreg.add_code(ROBO_state::ERROR_ILLUMINATOR_DAEMON_CONNECTION,
                                "ROBO_state::ERROR_ILLUMINATOR_DAEMON_CONNECTION",
                                function, common_info.log);

    common_info.erreg.add_code(ROBO_state::ERROR_ILLUMINATOR_CONTROL_COMMAND_ERROR,
                                "ROBO_state::ERROR_ILLUMINATOR_CONTROL_COMMAND_ERROR",
                                function, common_info.log);

    common_info.erreg.add_code(ROBO_state::ERROR_ILLUMINATOR_CONTROL_ERROR,
                                "ROBO_state::ERROR_ILLUMINATOR_CONTROL_ERROR",
                                function, common_info.log);

    common_info.erreg.add_code(ROBO_state::ERROR_ILLUMINATOR_CONTROL_STATUS_ERROR,
                                "ROBO_state::ERROR_ILLUMINATOR_CONTROL_STATUS_ERROR",
                                function, common_info.log);

    common_info.erreg.add_code(ROBO_state::ERROR_ILLUMINATOR_ERROR_CONTROL_ERROR,
                                "ROBO_state::ERROR_ILLUMINATOR_ERROR_CONTROL_ERROR",
                                function, common_info.log);

    common_info.erreg.add_code(ROBO_state::ERROR_ILLUMINATOR_SOCKET_REQUEST_ERROR,
                                "ROBO_state::ERROR_ILLUMINATOR_SOCKET_REQUEST_ERROR",
                                function, common_info.log);

    common_info.erreg.add_code(ROBO_state::ERROR_ILLUMINATOR_SOCKET_WRITE_ERROR,
                                "ROBO_state::ERROR_ILLUMINATOR_SOCKET_WRITE_ERROR",
                                function, common_info.log);

    common_info.erreg.add_code(ROBO_state::ERROR_ILLUMINATOR_SOCKET_SELECT_ERROR,
                                "ROBO_state::ERROR_ILLUMINATOR_SOCKET_SELECT_ERROR",
                                function, common_info.log);

    common_info.erreg.add_code(ROBO_state::ERROR_ILLUMINATOR_SOCKET_READ_ERROR,
                                "ROBO_state::ERROR_ILLUMINATOR_SOCKET_READ_ERROR",
                                function, common_info.log);

    common_info.erreg.add_code(ROBO_state::ERROR_ILLUMINATOR_DEVICE_TIMEOUT,
                                "ROBO_state::ERROR_ILLUMINATOR_DEVICE_TIMEOUT",
                                function, common_info.log);

    common_info.erreg.add_code(ROBO_state::ERROR_ILLUMINATOR_WRITE_DATA_ERROR,
                                "ROBO_state::ERROR_ILLUMINATOR_WRITE_DATA_ERROR",
                                function, common_info.log);

    common_info.erreg.add_code(ROBO_state::ERROR_ILLUMINATOR_SET_ADDRESS_FAILURE,
                                "ROBO_state::ERROR_ILLUMINATOR_SET_ADDRESS_FAILURE",
                                function, common_info.log);

    common_info.erreg.add_code(ROBO_state::ERROR_ILLUMINATOR_CRC_FAILURE,
                                "ROBO_state::ERROR_ILLUMINATOR_CRC_FAILURE",
                                function, common_info.log);

    common_info.erreg.add_code(ROBO_state::ERROR_ILLUMINATOR_RESET_FAILURE,
                                "ROBO_state::ERROR_ILLUMINATOR_RESET_FAILURE",
                                function, common_info.log);

    common_info.erreg.add_code(ROBO_state::ERROR_ILLUMINATOR_INIT_FAILURE,
                                "ROBO_state::ERROR_ILLUMINATOR_INIT_FAILURE",
                                function, common_info.log);

    common_info.erreg.add_code(ROBO_state::ERROR_ILLUMINATOR_TRIGGER_FAILURE,
                                "ROBO_state::ERROR_ILLUMINATOR_TRIGGER_FAILURE",
                                function, common_info.log);

    common_info.erreg.add_code(ROBO_state::ERROR_ILLUMINATOR_SET_FILTER_FAILURE,
                                "ROBO_state::ERROR_ILLUMINATOR_SET_FILTER_FAILURE",
                                function, common_info.log);

    common_info.erreg.add_code(ROBO_state::ERROR_ILLUMINATOR_FILTER_TOKENIZER_ERROR,
                                "ROBO_state::ERROR_ILLUMINATOR_FILTER_TOKENIZER_ERROR",
                                function, common_info.log);

    common_info.erreg.add_code(ROBO_state::ERROR_ILLUMINATOR_NO_SEQ_NUMBER_FOUND,
                                "ROBO_state::ERROR_ILLUMINATOR_NO_SEQ_NUMBER_FOUND",
                                function, common_info.log);

    common_info.erreg.add_code(ROBO_state::ERROR_ILLUMINATOR_SEQUENCE_TOKENIZER_ERROR,
                                "ROBO_state::ERROR_ILLUMINATOR_SEQUENCE_TOKENIZER_ERROR",
                                function, common_info.log);

    common_info.erreg.add_code(ROBO_state::ERROR_ILLUMINATOR_NO_LED_SEQUENCE_FOUND,
                                "ROBO_state::ERROR_ILLUMINATOR_NO_LED_SEQUENCE_FOUND",
                                function, common_info.log);

    common_info.erreg.add_code(ROBO_state::ERROR_ILLUMINATOR_UNKNOWN_CONTROLLER_ERROR,
                                "ROBO_state::ERROR_ILLUMINATOR_UNKNOWN_CONTROLLER_ERROR",
                                function, common_info.log);

    common_info.erreg.add_code(ROBO_state::ERROR_ILLUMINATOR_CALIB_SEND_FAILURE,
                                "ROBO_state::ERROR_ILLUMINATOR_CALIB_SEND_FAILURE",
                                function, common_info.log);

    common_info.erreg.add_code(ROBO_state::ERROR_ILLUMINATOR_UNKNOWN_COMMAND,
                                "ROBO_state::ERROR_ILLUMINATOR_UNKNOWN_COMMAND",
                                function, common_info.log);
  }

  /************ ROBO_state::illuminator_registry_codes ************/

  /**************** ROBO_state::Illmuminator::initialize_class ****************/
  void Illuminator::initialize_class()
  {
    this->status_time = 0;
    this->error_code = NO_ERROR;
    this->initialized = false;
    this->connection_open = false;
    this->current_state = NO_ERROR;
    this->updated = false;
  }
  /************ ROBO_state::Illmuminator::initialize_class ************/

 /************* ROBO_state::Illuminator::load_state *************/
  /**
   Loads the status string into the state class variables
   \param[status_message] A formatted string that contains the status
   */
  int Illuminator::load_state(std::string status_message)
  {
    std::stringstream message;
    // Break the message into tokens
    std::vector<std::string> tokens;  // Temporary tokens

    // Break up the message
    int err = Tokenize(status_message, tokens, " ");
    if (err < ROBO_state::NUM_ILLUMINATOR_PARAMS_NOT_INITIALIZED){
      return(ERROR);
    }

    //Unix time
    this->status_time = atoi(tokens[1].c_str());

    //Date and clock-time
    std::string temp = tokens[2] + " " + tokens[3];
    this->update_time.set_time(temp, ROBO_time::TIMEFMT_Y_M_D_H_M_S);

    this->initialized = atoi(tokens[4].c_str());

    // If the system is not initialized, then there are only
    // NUM_ILLUMINATOR_PARAMS_NOT_INITIALIZED parameters

    if (err == ROBO_state::NUM_ILLUMINATOR_PARAMS_NOT_INITIALIZED){
      this->error_code = NO_ERROR;
    }
    else if (err >= ROBO_state::NUM_REQUIRED_ILLUMINATOR_PARAMETERS)
    {
      this->error_code = atoi(tokens[5].c_str());
      int num_controller_errors = atoi(tokens[6].c_str());
      int num_illuminator_data_values = atoi(tokens[7].c_str());

      if (err != (ROBO_state::NUM_REQUIRED_ILLUMINATOR_PARAMETERS
                  + num_controller_errors
                  + num_illuminator_data_values ) )
      {
std::cout << "err != to num req. params + value count!" << std::endl;
std::cout << "Total tokenized parameters = " << err << std::endl;
std::cout << "num_controller_errors = " << num_controller_errors << std::endl;
std::cout << "num_illuminator data values = " << num_illuminator_data_values << std::endl;
        return(ERROR);
      }

      int i;
      int j = ROBO_state::NUM_REQUIRED_ILLUMINATOR_PARAMETERS;
      std::vector<int> temp_int;

      for (i = 0; i < num_controller_errors; i++){
        temp_int.push_back(atof(tokens[j].c_str()));
        j++;
      }
      this->controller_errors = temp_int;

      temp_int.clear();
      for (i = 0; i < num_illuminator_data_values; i++){
        temp_int.push_back(atof(tokens[j].c_str()));
        j++;
      }
      this->illuminator_data = temp_int;
    }

    else {
      return ERROR;
    }

    boost::lock_guard<boost::mutex> lock(this->state_mutex);
    this->updated = true;
    return NO_ERROR;
  }

  /**************** ROBO_state::Shutter_state::initialize_class ****************/
  void Shutter_state::initialize_class()
  {
    this->status_time = 0;
    this->error_code = NO_ERROR;
    this->initialized = false;
    this->connection_open = false;
    this->current_state = NO_ERROR;
    
    this->remote_close = BAD_VALUE;
    this->ready = false;
    this->close_switch[0] = false;
    this->close_switch[1] = false;
    this->open_switch[0] = false;
    this->open_switch[1] = false;
    this->mode_switch = BAD_VALUE;
    this->keylock_enabled = false;
    this->emergency_stop = false;
    this->reset_pressed = false;
    this->timeout = false;
    this->microcontroller = BAD_VALUE;
    this->updated = false;

    this->shutter_position = ROBO_state::SHUTTER_UNKNOWN;
    this->shutter_ready = false;
  }
  /************ ROBO_state::Shutter_state::initialize_class ************/

 /************* ROBO_state::Shutter_state::load_state *************/
  /**
   Loads the status string into the state class variables
   \param[status_message] A formatted string that contains the status
   */
  int Shutter_state::load_state(std::string status_message)
  {
//    int num_shutter_system_states=0;
    std::stringstream message;
    // Break the message into tokens
    std::vector<std::string> tokens;  // Temporary tokens

    // Break up the message
    int err = Tokenize(status_message, tokens, " ");
    if (err < ROBO_state::NUM_SHUTTER_PARAMS_NOT_INITIALIZED){
      return(ERROR);
    }

    //Unix time
    this->status_time = atoi(tokens[1].c_str());

    //Date and clock-time
    std::string temp = tokens[2] + " " + tokens[3];
    this->update_time.set_time(temp, ROBO_time::TIMEFMT_Y_M_D_H_M_S);

    this->initialized = atoi(tokens[4].c_str());

    // If the system is not initialized, then there are only
    // NUM_SHUTTER_PARAMS_NOT_INITIALIZED parameters

    if (err == ROBO_state::NUM_SHUTTER_PARAMS_NOT_INITIALIZED){
      this->error_code = NO_ERROR;
      this->remote_close = BAD_VALUE;
      this->ready = false;
      this->close_switch[0] = false;
      this->close_switch[1] = false;
      this->open_switch[0] = false;
      this->open_switch[1] = false;
      this->mode_switch = BAD_VALUE;
      this->keylock_enabled = false;
      this->emergency_stop = false;
      this->reset_pressed = false;
      this->timeout = false;
      this->microcontroller = BAD_VALUE;
      this->shutter_position = ROBO_state::SHUTTER_UNKNOWN;
      this->shutter_ready = false;
    }
    else if (err == ROBO_state::NUM_REQUIRED_SHUTTER_PARAMETERS)
    {
      this->error_code = atoi(tokens[5].c_str());
      this->shutter_ready = get_bool_value(tokens[6]);
      this->shutter_position = atoi(tokens[7].c_str());
     this->remote_close = atoi(tokens[8].c_str());
      this->ready = get_bool_value(tokens[9]);
      this->close_switch[0] = get_bool_value(tokens[10]);
      this->close_switch[1] = get_bool_value(tokens[11]);
      this->open_switch[0] = get_bool_value(tokens[12]);
      this->open_switch[1] = get_bool_value(tokens[13]);
      this->mode_switch = atoi(tokens[14].c_str());
      this->keylock_enabled = get_bool_value(tokens[15]);
      this->emergency_stop = get_bool_value(tokens[16]);
      this->reset_pressed = get_bool_value(tokens[17]);
      this->timeout = get_bool_value(tokens[18]);
      this->microcontroller = atoi(tokens[19].c_str());

      
      
//      int num_shutter_system_states = atoi(tokens[6].c_str());
//       if (err != (ROBO_state::NUM_REQUIRED_SHUTTER_PARAMETERS
//                  + num_shutter_system_states ) )
//      {
//std::cout << "err != to num req. params + value count!" << std::endl;
//std::cout << "Total tokenized parameters = " << err << std::endl;
//std::cout << "num_shutter_system_states = " << num_shutter_system_states << std::endl;
//        return(ERROR);
//      }
//
//      int i;
//      int j = ROBO_state::NUM_REQUIRED_SHUTTER_PARAMETERS;
//      std::vector<int> temp_int;
//
//      for (i = 0; i < num_shutter_system_states; i++){
//        temp_int.push_back(atof(tokens[j].c_str()));
//        j++;
//      }
//      this->shutter_system_states = temp_int;
    }

    else {
      return ERROR;
    }

    boost::lock_guard<boost::mutex> lock(this->state_mutex);
    this->updated = true;
    return NO_ERROR;
  }
 /************* ROBO_state::Shutter_state::load_state *************/
}


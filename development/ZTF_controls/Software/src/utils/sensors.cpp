/**
 \file sensors.cpp
 \brief Sensor classes for ROBO robotic system.
 \details This file handles the sensors for the various instruments in the
 robotic system.  
 
 Copyright (c) 2009-2021 California Institute of Technology.
 \author Dr. Reed L. Riddle  riddle@caltech.edu
 \note
 */

// Local include files
# include "sensors.h"


/** \namespace ROBO_sensor
 Namespace for the ROBO_sensor functions. */
namespace ROBO_sensor {
  
  
  /**************** ROBO_sensor::Calibration::Calibration ****************/
  /**
   This function constructs the Calibration class.
   */
  Calibration::Calibration()
  {
    
    this->cal_type = ROBO_sensor::CALIBRATION_NONE;
    this->sensor_type = ROBO_sensor::SENSOR_UNKNOWN;
    
  }
  /**************** ROBO_sensor::Calibration::Calibration ****************/

  
  /**************** ROBO_sensor::Calibration::do_cal ****************/
  /**
   Computes the calibration based on the coefficients and type of calibration
   that is being applied
   */
  float Calibration::do_cal(float value)
  {
    float output;   // Output value
    
    // Switch on the type
    switch(this->cal_type){
        
        // Linear calibration function: A*x+B
      case ROBO_sensor::CALIBRATION_LINEAR:
        output = value * this->coeff[1] + coeff[0];
        break;
        
        // If no calibration is applied then return the value
      case ROBO_sensor::CALIBRATION_NONE:
      default:
        output = value;
    }
    
    return(output);
  }
  /**************** ROBO_sensor::Calibration::do_cal ****************/
  
  
  /**************** ROBO_sensor::Calibration::load_cal ****************/
  /**
   Load the calibration string into the class.  The string is input in a 
   configuration file and needs to follow the format:
   \code
   CALIBRATION="Name Sensor_type Cal_type Coefficients"
   \endcode
   The name is whatever is useful to the user.  
   Sensor types are:
   \code
   TEMP - Temperature sensor
   HUMI - Humidity sensor
   DEWP - Dewpoint sensor
   PRES - In-line pressure sensor
   \endcode
   Calibration types are:
   \code
   NON - No calibration applied
   LIN - Linear calibration function (i.e. A*x + B)
   \endcode
   The coefficients depend on the calibration type, all must be present for 
   the calibration function to work appropriately
   \param [input] The input string of information
   */
  int Calibration::load_cal(std::string & input)
  {
    // Use the tokenizer to break up the message
    std::vector<std::string> tokens;  // Temporary tokens
    Tokenize(input, tokens, " \t");
    
    // There have to be a minimum of three elements
    if (tokens.size() < 3){
      return(ERROR);
    }
    
    // Set the name
    this->name = tokens[0];
    
    // Set the sensor type
    if (tokens[1].compare(0, 4, "CTEMP") == 0){
      this->sensor_type = ROBO_sensor::SENSOR_CONTROL_TEMPERATURE;
    }
    else if (tokens[1].compare(0, 4, "TEMP") == 0){
      this->sensor_type = ROBO_sensor::SENSOR_TEMPERATURE;
    }
    else if (tokens[1].compare(0, 4, "HUMI") == 0){
      this->sensor_type = ROBO_sensor::SENSOR_HUMIDITY;
    }
    else if (tokens[1].compare(0, 4, "VACP") == 0){
      this->sensor_type = ROBO_sensor::SENSOR_VACUUM_PRESSURE;
    }
    else if (tokens[1].compare(0, 4, "PRES") == 0){
      this->sensor_type = ROBO_sensor::SENSOR_PRESSURE;
    }
    else if (tokens[1].compare(0, 4, "VOLT") == 0){
      this->sensor_type = ROBO_sensor::SENSOR_VOLTAGE;
    }
    else if (tokens[1].compare(0, 4, "FLOW") == 0){
      this->sensor_type = ROBO_sensor::SENSOR_FLOW;
    }
    else if (tokens[1].compare(0, 4, "DEWP") == 0){
      this->sensor_type = ROBO_sensor::SENSOR_DEWPOINT;
    }
    else {
      this->sensor_type = ROBO_sensor::SENSOR_UNKNOWN;
    }
    
    // Set the calibration function type
    if (tokens[2].compare(0, 3, "LIN") == 0){
      this->cal_type = ROBO_sensor::CALIBRATION_LINEAR;
    }
    else if (tokens[2].compare(0, 3, "NON") == 0){
      this->cal_type = ROBO_sensor::CALIBRATION_NONE;
    }
    
    // Set the calibration coefficients
    this->coeff.clear();
    switch(this->cal_type){
        // Set parameters for linear calibration
      case ROBO_sensor::CALIBRATION_LINEAR:
        // There have to be a minimum of two coefficients for this
        if (tokens.size() < 5){
          return(ERROR);
        }
        this->coeff.push_back(atof(tokens[3].c_str()));
        this->coeff.push_back(atof(tokens[4].c_str()));
        break;
      default:
        ;
    }
    
    return(NO_ERROR);
  }
  /**************** ROBO_sensor::Calibration::load_cal ****************/












  /************* ROBO_sensor::State::State *************/
  /**
   
   */
  State::State()
  {
    // Set the log file name to the class log name
    this->log.filename = common_info.log_dir + "sensor_state.log";
    
    this->initialize_class();
  }
  /************* ROBO_sensor::State::State *************/
  
  
  /************* ROBO_sensor::State::State *************/
  /**
   
   */
  State::State(std::string logname)
  {
    // Set up the log file
    this->log.filename = common_info.log_dir + logname + ".log";
    
    this->initialize_class();
  }
  /************* ROBO_sensor::State::State *************/
  
  
  //  /************* ROBO_sensor::State::State *************/
  //  /**
  //   
  //   */
  //  State::State(const State & in_state)
  //  {
  //    this->initialize_class();
  //    
  //    this->copy_state(in_state);
  //  }
  //  /************* ROBO_sensor::State::State *************/
  
  
  //  /************* ROBO_sensor::State::State *************/
  //  /**
  //   
  //   */
  //  State::State operator= (const State & in_state)
  //  {
  //    this->initialize_class();
  //
  //    this->copy_state(in_state);
  //    
  //    return *this;
  //  }
  //  /************* ROBO_sensor::State::State *************/
  
  
  /************ ROBO_sensor::State::initialize_class ************/
  /**
   Initializes the sensor state class variables to default values.
   */
  void State::initialize_class()
  {
    this->status_time = 0;
    this->error_code = NO_ERROR;
    this->initialized = false;
    this->connection_open = false;
    this->current_state = NO_ERROR;
    // this->window_heater_power = 0;
//    this->window_heater_power_size = 0;
    this->updated = false;
    
    this->error_pressure = NO_ERROR;
    this->error_chiller = NO_ERROR;
    this->error_CR1000 = NO_ERROR;
    this->error_CR3000 = NO_ERROR;
    
    this->pressure_update_time = 0;
    this->chiller_update_time = 0;
    this->CR1000_update_time = 0;
    this->CR3000_update_time = 0;

    this->outhouse_temp = BAD_VALUE;
    this->cryo_pressure[0] = BAD_VALUE;
    this->cryo_pressure[1] = BAD_VALUE;
    this->cryo_pressure[2] = BAD_VALUE;
    this->cryo_pressure[3] = BAD_VALUE;
    this->dry_air_alarm = BAD_VALUE;
    this->dome_temp[0] = BAD_VALUE;
    this->dome_temp[1] = BAD_VALUE;
    this->dome_temp[2] = BAD_VALUE;
    this->dry_air_flow = BAD_VALUE;
    this->dome_temp[3] = BAD_VALUE;
    this->dome_humidity = BAD_VALUE;
    
    this->dome_dew_point = BAD_VALUE;
    
    this->cabinet_temp[0] = BAD_VALUE;
    this->hub_temp[0] = BAD_VALUE;
    this->post_temp[0] = BAD_VALUE;
    this->post_temp[1] = BAD_VALUE;
    this->hub_temp[1] = BAD_VALUE;
    this->post_temp[2] = BAD_VALUE;
    this->post_temp[3] = BAD_VALUE;
    this->getter_temp[0] = BAD_VALUE;
    this->getter_temp[1] = BAD_VALUE;
    this->tube_temp[0] = BAD_VALUE;
    this->tube_humidity = BAD_VALUE;
    this->ccd_temp[0] = BAD_VALUE;
    this->ccd_temp[1] = BAD_VALUE;
    this->ccd_temp[2] = BAD_VALUE;
    this->ccd_temp[3] = BAD_VALUE;
    this->ccd_temp[4] = BAD_VALUE;
    this->ccd_temp[5] = BAD_VALUE;
    this->ccd_temp[6] = BAD_VALUE;
    this->ccd_temp[7] = BAD_VALUE;
    this->ccd_temp[8] = BAD_VALUE;
    this->ccd_temp[9] = BAD_VALUE;
    this->ccd_temp[10] = BAD_VALUE;
    this->ccd_temp[11] = BAD_VALUE;
    this->ccd_temp[12] = BAD_VALUE;
    this->ccd_temp[13] = BAD_VALUE;
    this->ccd_temp[14] = BAD_VALUE;
    this->ccd_temp[15] = BAD_VALUE;
    this->tube_temp[1] = BAD_VALUE;
    this->tube_temp[2] = BAD_VALUE;
    this->tube_temp[3] = BAD_VALUE;
    this->tube_temp[4] = BAD_VALUE;
    this->tube_temp[5] = BAD_VALUE;
    this->tube_temp[6] = BAD_VALUE;
    this->cabinet_temp[1] = BAD_VALUE;
    this->cabinet_temp[2] = BAD_VALUE;
    this->cabinet_temp[3] = BAD_VALUE;
    this->cabinet_temp[4] = BAD_VALUE;
    
    this->tube_dew_point = BAD_VALUE;
    
    this->vacuum_pressure = BAD_VALUE;
    this->vac_gauge_power = BAD_VALUE;

    this->window_heater_request = BAD_VALUE;
    this->window_heater_power = BAD_VALUE;
    
    this->chiller_temp = BAD_VALUE;
    this->chiller_setting = BAD_VALUE;
    this->chiller_flow = BAD_VALUE;

    this->cold_plate_temp[0] = BAD_VALUE;
    this->cold_plate_temp[1] = BAD_VALUE;
    this->back_plate_temp = BAD_VALUE;
    this->vib_temp[0] = BAD_VALUE;
    this->vib_temp[1] = BAD_VALUE;
    this->cold_plate_heat = BAD_VALUE;
    this->vib_heat = BAD_VALUE;

    this->cryo_temp[0] = BAD_VALUE;
    this->cryo_temp[1] = BAD_VALUE;
    this->cryo_heat[0] = BAD_VALUE;
    this->cryo_heat[1] = BAD_VALUE;

    std::stringstream file;
    file << common_info.status_dir << "/" << "sensor_data.header";
    this->fits_header_file.filename = file.str();

  }
  /************ ROBO_sensor::State::initialize_class ************/
  
  
  /************* ROBO_sensor::State::load_state *************/
  /**
   Loads the status string into the state class variables
   \param[status_message] A formatted string that contains the dome status
   */
  int State::load_state(std::string status_message)
  {
    std::string function("ROBO_sensor::State::load_state");
    std::stringstream message;
    
    // Break the message into tokens
    std::vector<std::string> tokens;  // Temporary tokens
    int err = Tokenize(status_message, tokens, " ");
    if (err < ROBO_sensor::NUM_PARAMS_NOT_INITIALIZED){
      message << "bad message format!  Number of message parameters (" << err 
              << ") is less than minimum required (" 
              << ROBO_sensor::NUM_PARAMS_NOT_INITIALIZED << ")!";  
       this->log.write(function, LOG_ERROR, message.str());
      return(ERROR);
    }
    
    this->status_time = atoi(tokens[1].c_str());
    
    std::string temp = tokens[2] + " " + tokens[3];
    this->update_time.set_time(temp, ROBO_time::TIMEFMT_Y_M_D_H_M_S);
    
    this->initialized = atoi(tokens[4].c_str());
    
    // If the system is not initialized, then there are only
    // NUM_SENSOR_PARAMS_NOT_INITIALIZED parameters
    if (err == ROBO_sensor::NUM_PARAMS_NOT_INITIALIZED){
      this->error_code = NO_ERROR;
    }

    
    else if (err == ROBO_sensor::NUM_REQUIRED_PARAMETERS){
      // Get the error code state from the error flags, any flag non zero means
      // there is a problem
      if (tokens[5].length() == 7){
        this->error_code = NO_ERROR;
        for (int i = 0; i < 7; i++){
          std::string t = tokens[5].substr(i, 1);
          int err = atoi(t.c_str());
          if (err != 0){
            this->error_code = ERROR;
          }
        }
      }
      else {
        this->error_code = ERROR;
      }

      // Get Lakeshore 1 data
      this->cold_plate_temp[0] = atof(tokens[6].c_str());
      this->cold_plate_temp[1] = atof(tokens[7].c_str());
      this->back_plate_temp = atof(tokens[8].c_str());
      this->vib_temp[0] = atof(tokens[9].c_str());
      this->vib_temp[1] = atof(tokens[10].c_str());
      this->cold_plate_heat = atof(tokens[11].c_str());
      this->vib_heat = atof(tokens[12].c_str());

      // Get Lakeshore 2 data
      this->cryo_temp[0] = atof(tokens[13].c_str());
      this->cryo_temp[1] = atof(tokens[14].c_str());
      this->cryo_heat[0] = atof(tokens[15].c_str());
      this->cryo_heat[1] = atof(tokens[16].c_str());
      
      // Get CR3000 data
      this->cabinet_temp[0] = atof(tokens[17].c_str());
      this->hub_temp[0] = atof(tokens[18].c_str());
      this->post_temp[0] = atof(tokens[19].c_str());
      this->post_temp[1] = atof(tokens[20].c_str());
      this->hub_temp[1] = atof(tokens[21].c_str());
      this->post_temp[2] = atof(tokens[22].c_str());
      this->post_temp[3] = atof(tokens[23].c_str());
      this->getter_temp[0] = atof(tokens[24].c_str());
      this->getter_temp[1] = atof(tokens[25].c_str());
      this->tube_temp[0] = atof(tokens[26].c_str());
      this->tube_humidity = atof(tokens[27].c_str());
      this->ccd_temp[0] = atof(tokens[28].c_str());
      this->ccd_temp[1] = atof(tokens[29].c_str());
      this->ccd_temp[2] = atof(tokens[30].c_str());
      this->ccd_temp[3] = atof(tokens[31].c_str());
      this->ccd_temp[4] = atof(tokens[32].c_str());
      this->ccd_temp[5] = atof(tokens[33].c_str());
      this->ccd_temp[6] = atof(tokens[34].c_str());
      this->ccd_temp[7] = atof(tokens[35].c_str());
      this->ccd_temp[8] = atof(tokens[36].c_str());
      this->ccd_temp[9] = atof(tokens[37].c_str());
      this->ccd_temp[10] = atof(tokens[38].c_str());
      this->ccd_temp[11] = atof(tokens[39].c_str());
      this->ccd_temp[12] = atof(tokens[40].c_str());
      this->ccd_temp[13] = atof(tokens[41].c_str());
      this->ccd_temp[14] = atof(tokens[42].c_str());
      this->ccd_temp[15] = atof(tokens[43].c_str());
      this->tube_temp[1] = atof(tokens[44].c_str());
      this->tube_temp[2] = atof(tokens[45].c_str());
      this->tube_temp[3] = atof(tokens[46].c_str());
      this->tube_temp[4] = atof(tokens[47].c_str());
      this->tube_temp[5] = atof(tokens[48].c_str());
      this->tube_temp[6] = atof(tokens[49].c_str());
      this->cabinet_temp[1] = atof(tokens[50].c_str());
      this->cabinet_temp[2] = atof(tokens[51].c_str());
      this->cabinet_temp[3] = atof(tokens[52].c_str());
      this->cabinet_temp[4] = atof(tokens[53].c_str());

      // Get pressure data
      this->vacuum_pressure = atof(tokens[54].c_str());
      this->vac_gauge_power = atof(tokens[55].c_str());
      
      // Get CR1000 data
      this->outhouse_temp = atof(tokens[56].c_str());
      this->cryo_pressure[0] = atof(tokens[57].c_str());
      this->cryo_pressure[1] = atof(tokens[58].c_str());
      this->cryo_pressure[2] = atof(tokens[59].c_str());
      this->cryo_pressure[3] = atof(tokens[60].c_str());
      this->dry_air_alarm = atof(tokens[61].c_str());
      this->dome_temp[0] = atof(tokens[62].c_str());
      this->dome_temp[1] = atof(tokens[63].c_str());
      this->dome_temp[2] = atof(tokens[64].c_str());
      this->dry_air_flow = atof(tokens[65].c_str());
      this->dome_temp[3] = atof(tokens[66].c_str());
      this->dome_humidity = atof(tokens[67].c_str());

      // Get window heater data
      this->window_heater_request = atof(tokens[68].c_str());
      this->window_heater_power = atof(tokens[69].c_str());

      // Get chiller data
      this->chiller_temp = atof(tokens[70].c_str());
      this->chiller_setting = atof(tokens[71].c_str());
      this->chiller_flow = atof(tokens[72].c_str());

      // Get calculated data
      this->tube_dew_point = atof(tokens[73].c_str());
      this->dome_dew_point = atof(tokens[74].c_str());
      
      // Get the error codes
      std::vector<std::string> tok2;  // Temporary tokens
      err = Tokenize(tokens[75], tok2, ",");
      if (err == 7){
        this->error_CR3000 = atoi(tok2[0].c_str());
        this->error_CR1000 = atoi(tok2[1].c_str());
        this->error_lakeshore_1 = atoi(tok2[2].c_str());
        this->error_lakeshore_2 = atoi(tok2[3].c_str());
        this->error_pressure = atoi(tok2[4].c_str());
        this->error_window_heater = atoi(tok2[5].c_str());
        this->error_chiller = atoi(tok2[6].c_str());
        
        // See if there are any errors
        if (this->error_CR3000 != NO_ERROR){
//          this->error_code = this->error_CR3000;
          this->error_code = ROBO_sensor::ERROR_STATE_CR3000;
        }
        else if (this->error_CR1000 != NO_ERROR){
//          this->error_code = this->error_CR1000;
          this->error_code = ROBO_sensor::ERROR_STATE_CR1000;
        }
        else if (this->error_lakeshore_1 != NO_ERROR){
//          this->error_code = this->error_lakeshore_1;
          this->error_code = ROBO_sensor::ERROR_STATE_LAKESHORE_1;
        }
        else if (this->error_lakeshore_2 != NO_ERROR){
//          this->error_code = this->error_lakeshore_2;
          this->error_code = ROBO_sensor::ERROR_STATE_LAKESHORE_2;
        }
        else if (this->error_pressure != NO_ERROR){
//          this->error_code = this->error_pressure;
          this->error_code = ROBO_sensor::ERROR_STATE_PRESSURE;
        }
        else if (this->error_window_heater != NO_ERROR){
//          this->error_code = this->error_window_heater;
          this->error_code = ROBO_sensor::ERROR_STATE_WINDOW_HEATER;
        }
        else if (this->error_chiller != NO_ERROR){
//          this->error_code = this->error_chiller;
          this->error_code = ROBO_sensor::ERROR_STATE_CHILLER;
        }
        else {
          this->error_code = NO_ERROR;
        }
      }
      else {
        this->error_code = ROBO_sensor::ERROR_STATE_ERROR;
        message << "wrong number of error codes! Expected 7, received " << err
                << ", code message sent: " << tokens[75];
        this->log.write(function, LOG_ERROR, message.str());
      }

    }
     
    // Return an error if there are not the right number of tokens
    else {
      message << "wrong number of parameters! Initialized: " 
              << this->initialized << ", expected parameters: ";
      if (this->initialized == true){
        message << ROBO_sensor::NUM_REQUIRED_PARAMETERS;
      }
      else {
        message << ROBO_sensor::NUM_PARAMS_NOT_INITIALIZED;
      }
      message << ", input parameters: " << err << ".  Input message: " 
              << std::endl << status_message;
      this->log.write(function, LOG_ERROR, message.str());

      return(ERROR);
    }
    
    boost::lock_guard<boost::mutex> lock(this->state_mutex);
    this->updated = true;
    return(NO_ERROR);
  }
  /************* ROBO_sensor::State::load_state *************/
  
  
  /************* ROBO_sensor::State::load_pressure *************/
  /**
   Loads the status from the Pfeiffer pressure gaunge into the state class 
   variables
   \param[data] Vector of sensor data
   \param[now] The UNIX time of the update
   \param[bad_data] Flag if the data are bad
   */
  void State::load_pressure(std::vector<float> & data, time_t & now, 
                            bool bad_data)
  {
    std::string function("ROBO_sensor::State::load_pressure");
    
    // If the bad data flag is sent, or if there aren't enough elements in the
    // data, set all the data to the bad value
    if (bad_data == true || data.size() < 2){
      boost::lock_guard<boost::mutex> lock(this->state_mutex);
      this->vacuum_pressure = BAD_VALUE;
      this->vac_gauge_power = BAD_VALUE;
      
      if (data.size() < 2){
        this->log.write(function, LOG_ERROR, "missing pressure parameters!");
        this->error_pressure = ROBO_sensor::ERROR_BAD_SENSOR_DATA;
      }
      return;
    } 
    
    this->error_pressure = NO_ERROR;
    this->pressure_update_time = now;
    this->vacuum_pressure = data[0];
    this->vac_gauge_power = data[1];
  }
  /************* ROBO_sensor::State::load_pressure *************/


  /************* ROBO_sensor::State::load_chiller *************/
  /**
   Loads the status from the Optitemp chiller into the state class variables
   \param[data] Vector of sensor data
   \param[now] The UNIX time of the update
   \param[bad_data] Flag if the data are bad
   */
  void State::load_chiller(std::vector<float> & data, time_t & now, 
                                 bool bad_data)
  {
    std::string function("ROBO_sensor::State::load_chiller");
    
    // If the bad data flag is sent, or if there aren't enough elements in the
    // data, set all the data to the bad value
    if (bad_data == true || data.size() < 3){
      boost::lock_guard<boost::mutex> lock(this->state_mutex);
      this->chiller_temp = BAD_VALUE;
      this->chiller_setting = BAD_VALUE;
      this->chiller_flow = BAD_VALUE;
      
      if (data.size() < 3){
        this->log.write(function, LOG_ERROR, "missing chiller parameters!");
        this->error_chiller = ROBO_sensor::ERROR_BAD_SENSOR_DATA;
     }
      return;
    } 
    
    this->error_chiller = NO_ERROR;
    this->chiller_update_time = now;
    this->chiller_temp = data[0];
    this->chiller_setting = data[1];
    this->chiller_flow = data[2];
  }
  /************* ROBO_sensor::State::load_chiller *************/
  
  
  /************* ROBO_sensor::State::load_window_heater *************/
  /**
   Loads the status from the window heater into the state class variables
   \param[data] Vector of sensor data
   \param[now] The UNIX time of the update
   \param[bad_data] Flag if the data are bad
   */
  void State::load_window_heater(std::vector<float> & data, time_t & now, 
                            bool bad_data)
  {
    std::string function("ROBO_sensor::State::load_window_heater");
    
    // If the bad data flag is sent, or if there aren't enough elements in the
    // data, set all the data to the bad value
    if (bad_data == true || data.size() < 2){
      boost::lock_guard<boost::mutex> lock(this->state_mutex);
      this->window_heater_request = BAD_VALUE;
      this->window_heater_power = BAD_VALUE;
      
      if (data.size() < 2){
        this->log.write(function, LOG_ERROR, "missing pressure parameters!");
        this->error_window_heater = ROBO_sensor::ERROR_BAD_SENSOR_DATA;
      }
      return;
    } 
    
    this->error_window_heater = NO_ERROR;
    this->window_heater_update_time = now;
    this->window_heater_request = data[0];
    this->window_heater_power = data[1];
  }
  /************* ROBO_sensor::State::load_window_heater *************/
  
  
  /************* ROBO_sensor::State::load_lakeshore_1 *************/
  /**
   Loads the status from the window heater into the state class variables
   \param[data] Vector of sensor data
   \param[now] The UNIX time of the update
   \param[bad_data] Flag if the data are bad
   */
  void State::load_lakeshore_1(std::vector<float> & data, time_t & now, 
                                 bool bad_data)
  {
    std::string function("ROBO_sensor::State::load_lakeshore_1");
    
    // If the bad data flag is sent, or if there aren't enough elements in the
    // data, set all the data to the bad value
    if (bad_data == true || data.size() < 10){
      boost::lock_guard<boost::mutex> lock(this->state_mutex);
      this->cold_plate_temp[0] = BAD_VALUE;
      this->cold_plate_temp[1] = BAD_VALUE;
      this->back_plate_temp = BAD_VALUE;
      this->vib_temp[0] = BAD_VALUE;
      this->vib_temp[1] = BAD_VALUE;
      this->cold_plate_heat = BAD_VALUE;
      this->vib_heat = BAD_VALUE;
      
      if (data.size() < 10){
        this->log.write(function, LOG_ERROR, "missing sensor parameters!");
        this->error_lakeshore_1 = ROBO_sensor::ERROR_BAD_SENSOR_DATA;
      }
      return;
    } 
    
    this->error_lakeshore_1 = NO_ERROR;
    this->lakeshore_1_update_time = now;

    this->cold_plate_temp[0] = data[0];
    this->cold_plate_temp[1] = data[1];
    this->back_plate_temp = data[2];
    this->vib_temp[0] = data[3];
    this->vib_temp[1] = data[4];
    this->cold_plate_heat = data[8];
    this->vib_heat = data[9];
  }
  /************* ROBO_sensor::State::load_lakeshore_1 *************/
  
  
  /************* ROBO_sensor::State::load_lakeshore_2 *************/
  /**
   Loads the status from the window heater into the state class variables
   \param[data] Vector of sensor data
   \param[now] The UNIX time of the update
   \param[bad_data] Flag if the data are bad
   */
  void State::load_lakeshore_2(std::vector<float> & data, time_t & now, 
                               bool bad_data)
  {
    std::string function("ROBO_sensor::State::load_lakeshore_2");
    
    // If the bad data flag is sent, or if there aren't enough elements in the
    // data, set all the data to the bad value
    if (bad_data == true || data.size() < 10){
      boost::lock_guard<boost::mutex> lock(this->state_mutex);
      this->cryo_temp[0] = BAD_VALUE;
      this->cryo_temp[1] = BAD_VALUE;
      this->cryo_heat[0] = BAD_VALUE;
      this->cryo_heat[1] = BAD_VALUE;
      
      if (data.size() < 10){
        this->log.write(function, LOG_ERROR, "missing sensor parameters!");
        this->error_lakeshore_1 = ROBO_sensor::ERROR_BAD_SENSOR_DATA;
      }
      return;
    } 
    
    this->error_lakeshore_1 = NO_ERROR;
    this->lakeshore_2_update_time = now;
    
    this->cryo_temp[0] = data[0];
    this->cryo_temp[1] = data[1];
    this->cryo_heat[0] = data[8];
    this->cryo_heat[1] = data[9];
  }
  /************* ROBO_sensor::State::load_lakeshore_2 *************/
  
  
  /************* ROBO_sensor::State::load_CR1000 *************/
  /**
   Loads the status from the CR1000 into the state class variables
   \param[data] Vector of sensor data
   \param[now] The UNIX time of the update
   \param[bad_data] Flag if the data are bad
   */
  void State::load_CR1000(std::vector<float> & data, time_t & now, 
                          bool bad_data)
  {
    std::string function("ROBO_sensor::State::load_CR1000");

    // If the bad data flag is sent, or if there aren't enough elements in the
    // data, set all the data to the bad value
    if (bad_data == true || data.size() < 14){
      boost::lock_guard<boost::mutex> lock(this->state_mutex);
      this->outhouse_temp = BAD_VALUE;
      this->cryo_pressure[0] = BAD_VALUE;
      this->cryo_pressure[1] = BAD_VALUE;
      this->cryo_pressure[2] = BAD_VALUE;
      this->cryo_pressure[3] = BAD_VALUE;
      this->dry_air_alarm = BAD_VALUE;
      this->dome_temp[0] = BAD_VALUE;
      this->dome_temp[1] = BAD_VALUE;
      this->dome_temp[2] = BAD_VALUE;
      this->dry_air_flow = BAD_VALUE;
      this->dome_temp[3] = BAD_VALUE;
      this->dome_humidity = BAD_VALUE;

      this->dome_dew_point = BAD_VALUE;
      
      if (data.size() < 14){
        this->log.write(function, LOG_ERROR, "missing sensor parameters!");
        this->error_CR1000 = ROBO_sensor::ERROR_BAD_SENSOR_DATA;
      }
      return;
    }
    
    // Load the sensor data into the appropriate variables
    boost::lock_guard<boost::mutex> lock(this->state_mutex);
    this->error_CR1000 = NO_ERROR;
    this->CR1000_update_time = now;
//    this->outhouse_temp = data[0];
    this->cryo_pressure[0] = data[1];
    this->cryo_pressure[1] = data[2];
    this->cryo_pressure[2] = data[3];
    this->cryo_pressure[3] = data[4];
    this->outhouse_temp = data[5];
    this->dry_air_alarm = data[6];
    this->dome_temp[0] = data[8];
    this->dome_temp[1] = data[9];
    this->dome_temp[2] = data[10];
    this->dry_air_flow = data[11];
    this->dome_temp[3] = data[12];
    this->dome_humidity = data[13];

    // Calculate the dome dew point
    float b = 17.62;
    float g = 243.12; //degrees C
    float temp = calculate_median(this->dome_temp, 4) - 273.15;
    float humidity = this->dome_humidity / 100.0;
    this->dome_dew_point = g * (std::log(humidity) + b * temp / (g + temp)) / 
                          (b - (std::log(humidity) + b * temp / (g + temp)));
    
  }
  /************* ROBO_sensor::State::load_CR1000 *************/
  
  
  /************* ROBO_sensor::State::load_CR3000 *************/
  /**
   Loads the status from the CR1000 into the state class variables
   \param[data] Vector of sensor data
   \param[now] The UNIX time of the update
   \param[bad_data] Flag if the data are bad
   */
  void State::load_CR3000(std::vector<float> & data, time_t & now, 
                          bool bad_data)
  {
    std::string function("ROBO_sensor::State::load_CR3000");
    
    // If the bad data flag is sent, or if there aren't enough elements in the
    // data, set all the data to the bad value
    if (bad_data == true || data.size() < 45){
      boost::lock_guard<boost::mutex> lock(this->state_mutex);
      this->cabinet_temp[0] = BAD_VALUE;
      this->hub_temp[0] = BAD_VALUE;
      this->post_temp[0] = BAD_VALUE;
      this->post_temp[1] = BAD_VALUE;
      this->hub_temp[1] = BAD_VALUE;
      this->post_temp[2] = BAD_VALUE;
      this->post_temp[3] = BAD_VALUE;
      this->getter_temp[0] = BAD_VALUE;
      this->getter_temp[1] = BAD_VALUE;
      this->tube_temp[0] = BAD_VALUE;
      this->tube_humidity = BAD_VALUE;
      this->ccd_temp[0] = BAD_VALUE;
      this->ccd_temp[1] = BAD_VALUE;
      this->ccd_temp[2] = BAD_VALUE;
      this->ccd_temp[3] = BAD_VALUE;
      this->ccd_temp[4] = BAD_VALUE;
      this->ccd_temp[5] = BAD_VALUE;
      this->ccd_temp[6] = BAD_VALUE;
      this->ccd_temp[7] = BAD_VALUE;
      this->ccd_temp[8] = BAD_VALUE;
      this->ccd_temp[9] = BAD_VALUE;
      this->ccd_temp[10] = BAD_VALUE;
      this->ccd_temp[11] = BAD_VALUE;
      this->ccd_temp[12] = BAD_VALUE;
      this->ccd_temp[13] = BAD_VALUE;
      this->ccd_temp[14] = BAD_VALUE;
      this->ccd_temp[15] = BAD_VALUE;
      this->tube_temp[1] = BAD_VALUE;
      this->tube_temp[2] = BAD_VALUE;
      this->tube_temp[3] = BAD_VALUE;
      this->tube_temp[4] = BAD_VALUE;
      this->tube_temp[5] = BAD_VALUE;
      this->tube_temp[6] = BAD_VALUE;
      this->cabinet_temp[1] = BAD_VALUE;
      this->cabinet_temp[2] = BAD_VALUE;
      this->cabinet_temp[3] = BAD_VALUE;
      this->cabinet_temp[4] = BAD_VALUE;
      
      this->tube_dew_point = BAD_VALUE;
      
      if (data.size() < 45){
        this->log.write(function, LOG_ERROR, "missing sensor parameters!");
        this->error_CR3000 = ROBO_sensor::ERROR_BAD_SENSOR_DATA;
      }
      return;
    }
    
    // Load the sensor data into the appropriate variables
    boost::lock_guard<boost::mutex> lock(this->state_mutex);
    this->error_CR3000 = NO_ERROR;

    this->CR3000_update_time = now;
    this->cabinet_temp[0] = data[0];
    this->hub_temp[0] = data[1];
    this->post_temp[0] = data[2];
    this->post_temp[1] = data[3];
    this->hub_temp[1] = data[4];
    this->post_temp[2] = data[5];
    this->post_temp[3] = data[6];
    this->getter_temp[0] = data[7];
    this->getter_temp[1] = data[8];
    this->tube_temp[0] = data[9];
    this->tube_humidity = data[10];
    this->ccd_temp[0] = data[14];
    this->ccd_temp[1] = data[15];
    this->ccd_temp[2] = data[16];
    this->ccd_temp[3] = data[17];
    this->ccd_temp[4] = data[18];
    this->ccd_temp[5] = data[19];
    this->ccd_temp[6] = data[20];
    this->ccd_temp[7] = data[21];
    this->ccd_temp[8] = data[22];
    this->ccd_temp[9] = data[23];
    this->ccd_temp[10] = data[24];
    this->ccd_temp[11] = data[25];
    this->ccd_temp[12] = data[26];
    this->ccd_temp[13] = data[27];
    this->ccd_temp[14] = data[28];
    this->ccd_temp[15] = data[29];
    this->tube_temp[1] = data[30];
    this->tube_temp[2] = data[31];
    this->tube_temp[3] = data[32];
    this->tube_temp[4] = data[33];
    this->tube_temp[5] = data[34];
    this->tube_temp[6] = data[35];
    this->cabinet_temp[1] = data[36];
    this->cabinet_temp[2] = data[42];
    this->cabinet_temp[3] = data[43];
    this->cabinet_temp[4] = data[44];

    // Calculate the dome dew point
    float b = 17.62;
    float g = 243.12; //degrees C
    float temp = this->tube_temp[0] - 273.15;
    float humidity = this->tube_humidity / 100.0;
    this->tube_dew_point = g * (std::log(humidity) + b * temp / (g + temp)) / 
    (b - (std::log(humidity) + b * temp / (g + temp)));
  }
  /************* ROBO_sensor::State::load_CR3000 *************/
  
  
  /************* ROBO_sensor::State::print_telemetry_data *************/
  /**
   Print out the data in the required order for telemetry output.
   */
  std::string State::print_telemetry_data()
  {
    std::stringstream output;
    
    // Output the error flags in one group
    if (this->error_CR3000 == NO_ERROR){
      output << "0";
    }
    else {
      output << "1";
    }
    // Output the error flags in one group
    if (this->error_CR1000 == NO_ERROR){
      output << "0";
    }
    else {
      output << "1";
    }
    // Output the error flags in one group
    if (this->error_lakeshore_1 == NO_ERROR){
      output << "0";
    }
    else {
      output << "1";
    }
    // Output the error flags in one group
    if (this->error_lakeshore_2 == NO_ERROR){
      output << "0";
    }
    else {
      output << "1";
    }
    // Output the error flags in one group
    if (this->error_pressure == NO_ERROR){
      output << "0";
    }
    else {
      output << "1";
    }
    // Output the error flags in one group
    if (this->error_window_heater == NO_ERROR){
      output << "0";
    }
    else {
      output << "1";
    }
    // Output the error flags in one group
    if (this->error_chiller == NO_ERROR){
      output << "0";
    }
    else {
      output << "1";
    }
    
    // Output all of the sensor data
    output << std::setprecision(2) << std::fixed << " "
    // Lakeshore 1
      << this->cold_plate_temp[0] << " "
      << this->cold_plate_temp[1] << " "
      << this->back_plate_temp << " "
      << this->vib_temp[0] << " "
      << this->vib_temp[1] << " "
      << this->cold_plate_heat << " "
      << this->vib_heat << " "
    // Lakeshore 2
      << this->cryo_temp[0] << " "
      << this->cryo_temp[1] << " "
      << this->cryo_heat[0] << " "
      << this->cryo_heat[1] << " "
    // Campbell CR3000
      << this->cabinet_temp[0] << " "
      << this->hub_temp[0] << " "
      << this->post_temp[0] << " "
      << this->post_temp[1] << " "
      << this->hub_temp[1] << " "
      << this->post_temp[2] << " "
      << this->post_temp[3] << " "
      << this->getter_temp[0] << " "
      << this->getter_temp[1] << " "
      << this->tube_temp[0] << " "
      << this->tube_humidity << " "
      << this->ccd_temp[0] << " "
      << this->ccd_temp[1] << " "
      << this->ccd_temp[2] << " "
      << this->ccd_temp[3] << " "
      << this->ccd_temp[4] << " "
      << this->ccd_temp[5] << " "
      << this->ccd_temp[6] << " "
      << this->ccd_temp[7] << " "
      << this->ccd_temp[8] << " "
      << this->ccd_temp[9] << " "
      << this->ccd_temp[10] << " "
      << this->ccd_temp[11] << " "
      << this->ccd_temp[12] << " "
      << this->ccd_temp[13] << " "
      << this->ccd_temp[14] << " "
      << this->ccd_temp[15] << " "
      << this->tube_temp[1] << " "
      << this->tube_temp[2] << " "
      << this->tube_temp[3] << " "
      << this->tube_temp[4] << " "
      << this->tube_temp[5] << " "
      << this->tube_temp[6] << " "
      << this->cabinet_temp[1] << " "
      << this->cabinet_temp[2] << " "
      << this->cabinet_temp[3] << " "
      << this->cabinet_temp[4] << " "
    // Pfeiifer pressure gauge
      << std::setprecision(7) << " "<< this->vacuum_pressure << " "
      << std::setprecision(2) << this->vac_gauge_power << " "
    // Campbell CR1000
      << this->outhouse_temp << " "
      << this->cryo_pressure[0] << " "
      << this->cryo_pressure[1] << " "
      << this->cryo_pressure[2] << " "
      << this->cryo_pressure[3] << " "
      << this->dry_air_alarm << " "
      << this->dome_temp[0] << " "
      << this->dome_temp[1] << " "
      << this->dome_temp[2] << " "
      << this->dry_air_flow << " "
      << this->dome_temp[3] << " "
      << this->dome_humidity << " "
    // Window heater
      << this->window_heater_request << " "
      << this->window_heater_power << " "
    // Optitemp chiller
      << this->chiller_temp << " "
      << this->chiller_setting << " "
      << this->chiller_flow << " "
    // Calculated telemetry
      << this->tube_dew_point << " "
      << this->dome_dew_point << " "

    ;

    // Send the error codes
    output << this->error_CR3000 << "," << this->error_CR1000 << "," 
           << this->error_lakeshore_1 << "," << this->error_lakeshore_2 << "," 
           << this->error_pressure << "," << this->error_window_heater << "," 
           << this->error_chiller;
    
    output << std::endl;
    
    return(output.str());
  }
  /************* ROBO_sensor::State::print_telemetry_data *************/

  
  /************* ROBO_sensor::State::print_fits_header *************/
  int State::print_fits_header()
  {
    // Return an error if the file can't be opened
    if (this->fits_header_file.open_file(OPEN_FILE_REWRITE) != NO_ERROR){
      return(ERROR);
    }
    
    // Write everything into the header filestream.  Make sure to end each line
    // with an endline.  Make sure to follow the formatting:
    //
    // TYPE|KEY|VALUE|COMMENT
    //
    // Type is the kind of value, STRING, REAL or INT.  The key is an 8 character
    // keycode unique to the header parameter.  The value is, duh, the value to
    // put in the header; it has to be of type TYPE.  The comment is something
    // that explains what the value is.  The entire line has to be less than 80
    // characters, so don't be wordy with comments.
    this->fits_header_file.filestream
    // This is the number of parameters in the header file, it has to match
    // or else the FITS system will throw an error
      << "19" << std::endl
    
      << "REAL|HEADTEMP|" << this->cold_plate_temp[0] 
        << "|Cryo cooler cold head temp (K)" << std::endl
      << "REAL|DEWPRESS|" << this->vacuum_pressure 
        << "|Dewar pressure (milli-torr)" << std::endl
      << "REAL|DETHEAT|" << this->cold_plate_heat
        << "|Detector focal plane heater power (%)" << std::endl;
    
    for (int i = 0; i < 16; i++){
      std::stringstream bob;
      bob << std::setw(2) << std::setfill('0') << i + 1;
      this->fits_header_file.filestream << "REAL|CCDTMP" << bob.str()
        << "|" << this->ccd_temp[i] << "|CCD temperature " <<  bob.str() 
        << " (K)" << std::endl;
    }

    
//    if (this->temp_control_state.control_temperature.size() > 0){
//      this->fits_header_file.filestream << "REAL|HEADTEMP|" << this->temp_control_state.control_temperature[0]
//      << "|Cryo cooler cold head temp (K)" << std::endl;
//    }
//    else {
//      this->fits_header_file.filestream << "REAL|HEADTEMP|" << BAD_VALUE
//      << "|Cryo cooler cold head temp (K)" << std::endl;
//    }
//    if(this->pressure_measurement_state.pressure_state.size() > 0){
//      this->fits_header_file.filestream
//      << "REAL|DEWPRESS|" << this->pressure_measurement_state.pressure_state[0]
//      << "|Dewar pressure (milli-torr)" << std::endl;
//    }
//    else {
//      this->fits_header_file.filestream
//      << "REAL|DEWPRESS|" << BAD_VALUE
//      << "|Dewar pressure (milli-torr)" << std::endl;
//    }
//    //    << "REAL|DEWPRESS|" << this->pressure_measurement_state.pressure_state[0]
//    //      << "|Dewar pressure (milli-torr)" << std::endl
//    if (this->temp_control_state.control_temperature.size() > 8){
//      this->fits_header_file.filestream
//      << "REAL|DETHEAT|" << this->temp_control_state.control_temperature[8]
//      << "|Detector focal plane heater power (%)" << std::endl;
//    }
//    else {
//      this->fits_header_file.filestream
//      << "REAL|DETHEAT|" << BAD_VALUE
//      << "|Detector focal plane heater power (%)" << std::endl;
//    }
//    
//    for (int i = 14; i < 30; i++){
//      std::stringstream bob;
//      bob << std::setw(2) << std::setfill('0') << i - 13;
//      this->fits_header_file.filestream << "REAL|CCDTMP" << bob.str()
//      << "|" << logger_state.temperatures[i] << "|CCD temperature "
//      <<  bob.str() << " (K)" << std::endl;
//    }
    
    // Close the file and return the NO_ERROR code
    this->fits_header_file.close_file();
    return(NO_ERROR);
  }
  /************* ROBO_sensor::State::print_fits_header *************/
  

  /************* ROBO_sensor::State::set_error_code *************/
  /**
   Sets the error code for one of the hardware sensor systems
   \param[system_error] The system the error code is being set for
   \param[code] The code to set
   */
  void State::set_error_code(int system_error, int code)
  {
    
    if (system_error == ROBO_sensor::ERROR_STATE_CR3000){
      boost::lock_guard<boost::mutex> lock(this->state_mutex);
      this->error_CR3000 = code;
    }
    else if (system_error == ROBO_sensor::ERROR_STATE_CR1000){
      boost::lock_guard<boost::mutex> lock(this->state_mutex);
      this->error_CR1000 = code;
    }
    else if (system_error == ROBO_sensor::ERROR_STATE_LAKESHORE_1){
      boost::lock_guard<boost::mutex> lock(this->state_mutex);
      this->error_lakeshore_1 = code;
    }
    else if (system_error == ROBO_sensor::ERROR_STATE_LAKESHORE_2){
      boost::lock_guard<boost::mutex> lock(this->state_mutex);
      this->error_lakeshore_2 = code;
    }
    else if (system_error == ROBO_sensor::ERROR_STATE_PRESSURE){
      boost::lock_guard<boost::mutex> lock(this->state_mutex);
      this->error_pressure = code;
    }
    else if (system_error == ROBO_sensor::ERROR_STATE_WINDOW_HEATER){
      boost::lock_guard<boost::mutex> lock(this->state_mutex);
      this->error_window_heater = code;
    }
    else if (system_error == ROBO_sensor::ERROR_STATE_CHILLER){
      boost::lock_guard<boost::mutex> lock(this->state_mutex);
      this->error_chiller = code;
    }

  }
  /************* ROBO_sensor::State::set_error_code *************/

  
  
  
  /************ ROBO_sensor::State::copy_state ************/
  /**
   Copies the State state class variables into a new class variable.
   \param[in_state] A State state class container
   \note This is used for the copy and operator= constructors
   */
  void State::copy_state(State & in_state)
  {
    this->update_time = in_state.update_time;
    
    this->status_time = in_state.status_time;
    this->error_code = in_state.error_code;
    this->initialized = in_state.initialized;
    this->connection_open = in_state.connection_open;
    this->current_state = in_state.current_state;
    // this->window_heater_power = in_state.window_heater_power;
    // this->window_heater_power_size = in_state.window_heater_power_size;
    
//    this->window_heater_power.swap(in_state.window_heater_power);
//    this->control_temperature.swap(in_state.control_temperature);
//    this->temperatures.swap(in_state.temperatures);
//    this->pressure_state.swap(in_state.pressure_state);
//    this->power.swap(in_state.power);
//    this->humidity.swap(in_state.humidity);
//    this->dewpoint.swap(in_state.dewpoint);
//    this->pressures.swap(in_state.pressures);
//    this->chiller_data.swap(in_state.chiller_data);
  }
  /************ ROBO_sensor::State::copy_state ************/
  
  
  /************ ROBO_sensor::State::sensor_registry_codes ************/
  void registry_codes(ROBO_logfile & log)
  {
    
    std::string function("ROBO_sensor::sensor_registry_codes");
    
    if (common_info.comreg.check_registry(ROBO_registry::SENSOR_REGISTRY) == true){
      return;
    }
    
    common_info.comreg.add_registry(ROBO_registry::SENSOR_REGISTRY);
    
    common_info.comreg.add_code(ROBO_sensor::OPEN_CONNECTION,
                                "ROBO_sensor::OPEN_CONNECTION",
                                function, common_info.log);
    common_info.comreg.add_code(ROBO_sensor::READ_DATA,
                                "ROBO_sensor::READ_DATA",
                                function, common_info.log);
    common_info.comreg.add_code(ROBO_sensor::WRITE_DATA,
                                "ROBO_sensor::WRITE_DATA",
                                function, common_info.log);
    common_info.comreg.add_code(ROBO_sensor::PROCESS_INFO,
                                "ROBO_sensor::PROCESS_INFO",
                                function, common_info.log);
    common_info.comreg.add_code(ROBO_sensor::TESTING,
                                "ROBO_sensor::TESTING",
                                function, common_info.log);
    common_info.comreg.add_code(ROBO_sensor::SHUTDOWN,
                                "ROBO_sensor::SHUTDOWN",
                                function, common_info.log);
    common_info.comreg.add_code(ROBO_sensor::EMERGENCY_SHUTDOWN,
                                "ROBO_sensor::EMERGENCY_SHUTDOWN",
                                function, common_info.log);
    common_info.comreg.add_code(ROBO_sensor::CHECK_ERROR,
                                "ROBO_sensor::CHECK_ERROR",
                                function, common_info.log);
    common_info.comreg.add_code(ROBO_sensor::POWER_ON_SENSOR,
                                "ROBO_sensor::POWER_ON_SENSOR",
                                function, common_info.log);
    common_info.comreg.add_code(ROBO_sensor::POWER_OFF_SENSOR,
                                "ROBO_sensor::POWER_OFF_SENSOR",
                                function, common_info.log);
    common_info.comreg.add_code(ROBO_sensor::RELOAD_CONFIGURATION,
                                "ROBO_sensor::RELOAD_CONFIGURATION",
                                function, common_info.log);
    
    common_info.comreg.add_code(ROBO_sensor::DISABLE_WINDOW_HEATER_CONTROL,
                                "ROBO_sensor::DISABLE_WINDOW_HEATER_CONTROL",
                                function, common_info.log);
    
    common_info.comreg.add_code(ROBO_sensor::ENABLE_WINDOW_HEATER_CONTROL,
                                "ROBO_sensor::ENABLE_WINDOW_HEATER_CONTROL",
                                function, common_info.log);
    
    common_info.comreg.add_code(ROBO_sensor::DISCONNECT_CHILLER,
                                "ROBO_sensor::DISCONNECT_CHILLER",
                                function, common_info.log);
    
    common_info.comreg.add_code(ROBO_sensor::CONNECT_CHILLER,
                                "ROBO_sensor::CONNECT_CHILLER",
                                function, common_info.log);
    
    common_info.comreg.add_code(ROBO_sensor::DISCONNECT_PRESSURE_GAUGE,
                                "ROBO_sensor::DISCONNECT_PRESSURE_GAUGE",
                                function, common_info.log);
    
    common_info.comreg.add_code(ROBO_sensor::CONNECT_PRESSURE_GAUGE,
                                "ROBO_sensor::CONNECT_PRESSURE_GAUGE",
                                function, common_info.log);
    
    common_info.comreg.add_code(
                          ROBO_sensor::DISABLE_CONTINUOUS_PRESSURE_MONITORING,
                          "ROBO_sensor::DISABLE_CONTINUOUS_PRESSURE_MONITORING",
                          function, common_info.log);
    
    common_info.comreg.add_code(
                          ROBO_sensor::ENABLE_CONTINUOUS_PRESSURE_MONITORING,
                          "ROBO_sensor::ENABLE_CONTINUOUS_PRESSURE_MONITORING",
                          function, common_info.log);
    
    common_info.comreg.add_code(ROBO_sensor::CHANGE_CHILLER_SETPOINT,
                                "ROBO_sensor::CHANGE_CHILLER_SETPOINT",
                                function, common_info.log);
    
    common_info.comreg.add_code(ROBO_sensor::CLOSE_CONNECTION,
                                "ROBO_sensor::CLOSE_CONNECTION",
                                function, common_info.log);
    
    // Error codes
    common_info.erreg.add_code(ROBO_sensor::ERROR_OPEN_CONNECTION,
                               "ROBO_sensor::ERROR_OPEN_CONNECTION",
                               function, common_info.log);
    
    common_info.erreg.add_code(ROBO_sensor::ERROR_CLOSE_CONNECTION,
                               "ROBO_sensor::ERROR_CLOSE_CONNECTION",
                               function, common_info.log);
    
    common_info.erreg.add_code(ROBO_sensor::ERROR_CONFIGURATION_FILE,
                               "ROBO_sensor::ERROR_CONFIGURATION_FILE",
                               function, common_info.log);
    
    common_info.erreg.add_code(ROBO_sensor::ERROR_INITIALIZED,
                               "ROBO_sensor::ERROR_INITIALIZED",
                               function, common_info.log);
    
    common_info.erreg.add_code(ROBO_sensor::ERROR_INITIALIZE_FAILED,
                               "ROBO_sensor::ERROR_INITIALIZE_FAILED",
                               function, common_info.log);
    
    common_info.erreg.add_code(ROBO_sensor::ERROR_NOT_INITIALIZED,
                               "ROBO_sensor::ERROR_NOT_INITIALIZED",
                               function, common_info.log);
    
    common_info.erreg.add_code(ROBO_sensor::ERROR_DAEMON_CONNECTION,
                               "ROBO_sensor::ERROR_DAEMON_CONNECTION",
                               function, common_info.log);
    
    common_info.erreg.add_code(ROBO_sensor::ERROR_CONTROL_COMMAND_ERROR,
                               "ROBO_sensor::ERROR_CONTROL_COMMAND_ERROR",
                               function, common_info.log);
    common_info.erreg.add_code(ROBO_sensor::ERROR_ERROR_CONTROL_ERROR,
                               "ROBO_sensor::ERROR_ERROR_CONTROL_ERROR",
                               function, common_info.log);
    
    common_info.erreg.add_code(ROBO_sensor::ERROR_CONTROL_STATUS_ERROR,
                               "ROBO_sensor::ERROR_CONTROL_STATUS_ERROR",
                               function, common_info.log);
    
    common_info.erreg.add_code(ROBO_sensor::ERROR_SOCKET_REQUEST_ERROR,
                               "ROBO_sensor::ERROR_SOCKET_REQUEST_ERROR",
                               function, common_info.log);
    
    common_info.erreg.add_code(ROBO_sensor::ERROR_SOCKET_WRITE_ERROR,
                               "ROBO_sensor::ERROR_SOCKET_WRITE_ERROR",
                               function, common_info.log);
    
    common_info.erreg.add_code(ROBO_sensor::ERROR_SOCKET_SELECT_ERROR,
                               "ROBO_sensor::ERROR_SOCKET_SELECT_ERROR",
                               function, common_info.log);
    
    common_info.erreg.add_code(ROBO_sensor::ERROR_SOCKET_READ_ERROR,
                               "ROBO_sensor::ERROR_SOCKET_READ_ERROR",
                               function, common_info.log);
    
    common_info.erreg.add_code(ROBO_sensor::ERROR_DEVICE_TIMEOUT,
                               "ROBO_sensor::ERROR_DEVICE_TIMEOUT",
                               function, common_info.log);
    
    common_info.erreg.add_code(ROBO_sensor::ERROR_ACK_NOT_RECEIVED,
                               "ROBO_sensor::ERROR_ACK_NOT_RECEIVED",
                               function, common_info.log);
    
    common_info.erreg.add_code(ROBO_sensor::ERROR_WRITE_DATA_ERROR,
                               "ROBO_sensor::ERROR_WRITE_DATA_ERROR",
                               function, common_info.log);
    
    common_info.erreg.add_code(ROBO_sensor::ERROR_TIMEOUT,
                               "ROBO_sensor::ERROR_TIMEOUT",
                               function, common_info.log);
    
    common_info.erreg.add_code(ROBO_sensor::ERROR_BAD_CONTROLLER_CONNECTION,
                               "ROBO_sensor::ERROR_BAD_CONTROLLER_CONNECTION",
                               function, common_info.log);
    
    common_info.erreg.add_code(ROBO_sensor::ERROR_CRC_FAILURE,
                               "ROBO_sensor::ERROR_CRC_FAILURE",
                               function, common_info.log);
    
    common_info.erreg.add_code(ROBO_sensor::ERROR_NEED_AC_POWER_CYCLE,
                               "ROBO_sensor::ERROR_NEED_AC_POWER_CYCLE",
                               function, common_info.log);
    
    common_info.erreg.add_code(ROBO_sensor::ERROR_SENSOR_NOT_CONNECTED,
                               "ROBO_sensor::ERROR_SENSOR_NOT_CONNECTED",
                               function, common_info.log);
    common_info.erreg.add_code(ROBO_sensor::ERROR_SENSOR_NOT_POWERED,
                               "ROBO_sensor::ERROR_SENSOR_NOT_POWERED",
                               function, common_info.log);
    common_info.erreg.add_code(ROBO_sensor::ERROR_BAD_INPUT_DATA,
                               "ROBO_sensor::ERROR_BAD_INPUT_DATA",
                               function, common_info.log);
    common_info.erreg.add_code(ROBO_sensor::ERROR_BAD_SENSOR_DATA,
                               "ROBO_sensor::ERROR_BAD_SENSOR_DATA",
                               function, common_info.log);
    common_info.erreg.add_code(ROBO_sensor::ERROR_CANNOT_READ_DATA,
                               "ROBO_sensor::ERROR_CANNOT_READ_DATA",
                               function, common_info.log);
    common_info.erreg.add_code(ROBO_sensor::ERROR_WINDOW_HEATER_SETTING,
                               "ROBO_sensor::ERROR_WINDOW_HEATER_SETTING",
                               function, common_info.log);
    common_info.erreg.add_code(ROBO_sensor::MONITORD_ERROR_DAEMON_CONNECTION,
                               "ROBO_sensor::MONITORD_ERROR_DAEMON_CONNECTION",
                               function, common_info.log);
    common_info.erreg.add_code(ROBO_sensor::ERROR_STATE_CR3000,
                               "ROBO_sensor::ERROR_STATE_CR3000",
                               function, common_info.log);
    common_info.erreg.add_code(ROBO_sensor::ERROR_STATE_CR1000,
                               "ROBO_sensor::ERROR_STATE_CR1000",
                               function, common_info.log);
    common_info.erreg.add_code(ROBO_sensor::ERROR_STATE_LAKESHORE_1,
                               "ROBO_sensor::ERROR_STATE_LAKESHORE_1",
                               function, common_info.log);
    common_info.erreg.add_code(ROBO_sensor::ERROR_STATE_LAKESHORE_2,
                               "ROBO_sensor::ERROR_STATE_LAKESHORE_2",
                               function, common_info.log);
    common_info.erreg.add_code(ROBO_sensor::ERROR_STATE_PRESSURE,
                               "ROBO_sensor::ERROR_STATE_PRESSURE",
                               function, common_info.log);
    common_info.erreg.add_code(ROBO_sensor::ERROR_STATE_WINDOW_HEATER,
                               "ROBO_sensor::ERROR_STATE_WINDOW_HEATER",
                               function, common_info.log);
    common_info.erreg.add_code(ROBO_sensor::ERROR_STATE_CHILLER,
                               "ROBO_sensor::ERROR_STATE_CHILLER",
                               function, common_info.log);
    common_info.erreg.add_code(ROBO_sensor::ERROR_STATE_ERROR,
                               "ROBO_sensor::ERROR_STATE_ERROR",
                               function, common_info.log);
    
    common_info.erreg.add_code(ROBO_sensor::ERROR_UNKNOWN,
                               "ROBO_sensor::ERROR_UNKNOWN",
                               function, common_info.log);
    
  }
  /************ ROBO_sensor::State::sensor_registry_codes ************/
  
  
  
















}

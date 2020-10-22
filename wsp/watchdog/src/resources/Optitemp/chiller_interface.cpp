/**
 \file chiller_interface.cpp
 \brief Interface functions for Opti Temp Chiller device.
 \details Functions that interface with Opti Temp Chiller devices to 
  get information out of them and control their operation.

 Copyright (c) 2009-2015 California Institute of Technology.
 \author John Cromer  cro@astro.caltech.edu
 \author Dr. Reed L. Riddle  riddle@caltech.edu
 */

// Local include files
# include "chiller_interface.h"


//char BUF[64];

/** \namespace Optitemp
 Namespace for the Opti Temp functions */
namespace Optitemp
{

  
  /********* Optitemp::Chiller_interface::Chiller_interface *********/
  /**
   This function constructs the Optitemp Interface class.
   */
  Chiller_interface::Chiller_interface()
  {
    // Set the log file name to the class log name
    this->log.filename = common_info.log_dir + "chiller.log";
    
    // Initialize the class
    this->initialize_class();
  };
  /********* Optitemp::Chiller_interface::Chiller_interface *********/

  
  /********* Optitemp::Chiller_interface::Chiller_interface *********/
  /**
   This function constructs the Opti Temp Interface class, using an 
   input string to set the name of the log file.
   */
  Chiller_interface::Chiller_interface(std::string logname)
  {
    // Set up the log file
    this->log.filename = common_info.log_dir + logname + ".log";
    
    // Initialize the class
    this->initialize_class();
  };
  /********* Optitemp::Chiller_interface::Chiller_interface *********/

  
  /********* Optitemp::Chiller_interface::Chiller_interface *********/
  /**
   This function constructs the Opti Temp Interface class, using an 
   input log class to set up the log file system.
   */
  Chiller_interface::Chiller_interface(ROBO_logfile log_in)
  {
    // Set up the log file
    this->log = log_in;

    this->initialize_class();
  }
  /********* Optitemp::Chiller_interface::Chiller_interface *********/

  
  /******** Optitemp::Chiller_interface::~Chiller_interface *********/
  /**
   This function deconstructs the Opti Temp Interface class.
   */
  Chiller_interface::~Chiller_interface()
  {

  }
  /******** Optitemp::Chiller_interface::~Chiller_interface *********/

  
  /********* Optitemp::Chiller_interface::initialize_class **********/
  /**
   This function initializes the Opti Temp Chiller interface class.
   */
  void Chiller_interface::initialize_class()
  {
    // Set the function information for logging
    std::string function("Optitemp::Chiller_interface::initialize_class");
    std::stringstream message;

    this->log.write(function, LOG_NO_ERROR, "initializing the Chiller interface class");

    // Initialize the variables
    this->connection_open = false;
    
    // Set the configuration file name
    this->config.filename = common_info.config_dir + "optitemp.cfg";

    // Get the configuration file information
    if (this->get_config() != NO_ERROR){
      this->log.write(function, LOG_ERROR, "failed to read configuration file!");
      return;
    }
    
    this->log.write(function, LOG_NO_ERROR,
                    "Chiller interface class initialization complete");
  }
  /********* Optitemp::Chiller_interface::initialize_class **********/
  
  
  /************ Optitemp::Chiller_interface::get_config *************/
  /**
   Reads the configuration file into the config class variable.  This requires
   setting the file name variable (config.filename) to the configuration file
   BEFORE calling this routine.  The configuration file must be set up with
   variable=value pairs in the same format as a Bash script:
   \code
   # Configuration file directory
   CONFIG_DIR="/home/bob/Config/"
   \endcode
   \return NO_ERROR if the configuration file is read properly, ERROR if not
   \note The configuration filename is set in initialize_class, if it changes
   for some reason that change must be applied before get_config() is called.
   */
  int Chiller_interface::get_config()
  {
    std::string function("Optitemp::Chiller_interface::get_config");
    std::stringstream message;
    
    message << "reading config file " << this->config.filename;
    log.write(function, false, message.str());
    message.str("");
    
    int error_code = NO_ERROR;
    
    if (this->config.filename.empty() == true){
      this->log.write(function, LOG_ERROR, "config file does not exist!");
      return(ERROR);
    }
    
    // After reading, toss any errors back from the file reading system.
    //    error_code = this->config.read_config(this->config);
    error_code = this->config.read_config(this->config);
    if (error_code != NO_ERROR){
      message << "file error thrown, error code: "
      << common_info.erreg.get_code(error_code);
      this->log.write(function, LOG_ERROR, message.str());
      message.str("");
      return(ERROR);
    }
    
    // Set the parameter values, do some error checking along the way
    int i = 0;            // Loop index variable
    for (i=0; i<this->config.n_elements; i++){
      
      if (config.vars[i].compare("NAME") == 0){
        this->name = config.params[i];
      }
      
      else if (config.vars[i].compare("IP_ADDRESS") == 0){
        this->info.hostname = config.params[i];
      }
      
      else if (config.vars[i].compare("NETWORK_PORT") == 0){
        this->info.port = (ROBO_port) atoi(config.params[i].c_str());
      }
      
      
      // Found an unknown variable name, so flag it and return.
      else {
        message << "unknown variable found: " << this->config.vars[i];
        this->log.write(function, LOG_ERROR, message.str());
        message.str("");
        return(ERROR);
      }
    }
    
    // Log a message that the configuration was found successfully.
    this->log.write_log_config(this->config.vars, this->config.params,
                               this->config.filename);
    /*
     * The above function never returns.
     */
    message << "successfully read config file " << this->config.filename;
    this->log.write(function, LOG_NO_ERROR, message.str());
    message.str("");
    
    return(NO_ERROR);
  }
  /************ Optitemp::Chiller_interface::get_config *************/

  
  /********* Optitemp::Chiller_interface::controllerconnect *********/
  /**
  Establish a connection to the Optitemp chiller
  \return NO_ERROR if the connection opens successfully, ERROR or the 
    connection error code if it fails
   */
  int Chiller_interface::controllerconnect (void)
  {
    std::stringstream message;
    std::string function("Optitemp::Chiller_interface::controllerconnect");
    struct sockaddr_in	insock;
    int			flags;
    int error=NO_ERROR;
    
    /* Already open? */
    if (this->connection_open == true){
      this->log.write(function, LOG_NO_ERROR, 
                      "Chiller connection already open");
      return(NO_ERROR);
    }
    
    /* Log what we're doing. */
    this->log.write(function, LOG_NO_ERROR,
                    "opening a connection to the Chiller controller");
    
    // Make sure the config file data are up to date
    if (this->config.modified() == true){
      if (this->get_config() != NO_ERROR){
        this->log.write(function, LOG_ERROR, "unable to get configuration!");
        return(ROBO_sensor::ERROR_CONFIGURATION_FILE);
      }
    }
    
    /* open a socket file descriptor */
    if ((this->sockfd = socket (AF_INET, SOCK_STREAM, IPPROTO_TCP)) < 0){
      this->log.write(function, LOG_ERROR, 
                      "allocating connection socket failed!");
      return (ERROR);
    }
    
    /* make address reuseable */
    flags = 1;
    if (setsockopt (this->sockfd, SOL_SOCKET, SO_REUSEADDR, (char*)&flags, sizeof(flags)) == ERROR){
      this->log.write(function, LOG_ERROR, 
                      "setting options on connection socket failed!");
      return (ERROR);
    }
    
    /* try to make a connection */
    insock.sin_family = AF_INET;
    insock.sin_port = htons (this->info.port);
    insock.sin_addr.s_addr = inet_addr (this->info.hostname.c_str());
    error = connect( this->sockfd, (struct sockaddr *)&insock, sizeof(insock));
    if (error < 0){
      message << " socket connect() failed.  " << strerror(errno);
      this->log.write(function, LOG_ERROR, message.str());
      message.str("");
    }
    else {
      error = NO_ERROR;
      message << "socket connection to " << this->info.hostname << ":" 
              << this->info.port << " established on fd" << this->sockfd;
      this->log.write(function, LOG_NO_ERROR, message.str());
      message.str("");
    }
    
    // On success, write the value to the log
    if (error == NO_ERROR){
      this->connection_open = true;
      this->log.write(function, LOG_NO_ERROR, "Chiller connection established");
    }
    // Throw an error for any other errors
    else { 
      /* Need to put something about state here */
      this->log.write(function, LOG_ERROR, "Chiller connection error!");
    }
    
    /* return any error */ 
    return(error);
  }
  /********* Optitemp::Chiller_interface::controllerconnect *********/
  
  
  /************* Optitemp::Chiller_interface::disconnect ************/
  /** Terminates the Chiller interface connection.
   \return NO_ERROR if the connection closes successfully, socket error code if
   it fails
   */
  int Chiller_interface::disconnect()
  {
    // Set the function information for logging
    std::string function("Optitemp::Chiller_interface::disconnect");
    std::stringstream message;
    int error = ERROR;
    int ret = 0; // function return value

    if (this->connection_open == false){
      this->log.write(function, LOG_NO_ERROR, "connection already shut down");
      return(NO_ERROR);
    }
    
    // Log a message that the camera connection is shutting down
    this->log.write(function, LOG_NO_ERROR, "shutting down Chiller connection");
    
    if ((ret = shutdown(this->sockfd,SHUT_RDWR)) < 0){
      message << " shutdown() failed.  System error msg = " << strerror(errno);
      this->log.write(function, LOG_ERROR, message.str());
      message.str("");
    }
    else {
      if ((ret = close(this->sockfd)) < 0){
        message << " close() failed.  System error msg = " << strerror(errno);
        this->log.write(function, LOG_ERROR, message.str());
        message.str("");
      }
      else {
        error = NO_ERROR;
      }
    }
    
    
//    // Close network connection
//    try {
//      if (this->sock.is_open() == true){
//        sock.close();
//      }
//      this->io_service.stop();
//      this->io_service.reset();
//    }
//    // Toss an error message on a failure to connect
//    catch (...){
//      message << "closing " << this->name << " connection failed!";
//      this->log.write(function, LOG_ERROR, message.str());
//      return(ERROR);
//    }
//    error = NO_ERROR;
    
    // On success, write the value to the log and return
    if (error == NO_ERROR){
      this->connection_open = false;
      this->log.write(function, LOG_NO_ERROR, "Chiller connection terminated");
    }
    // Throw an error for any other errors
    else {
      message << "Error disconnecting Chiller! Chiller error code: " << error;
      this->log.write(function, LOG_ERROR, message.str());
      return(ERROR);
    }
    return(NO_ERROR);
  }
  /************* Optitemp::Chiller_interface::disconnect ************/
  
  
  /************* Optitemp::Chiller_interface::modGet ************/
  /** 
   Gets multiple bytes from Modbus host at one time.
   \param [ct] Number of bytes to read.
   */
  int Chiller_interface::modGet(int fd, unsigned char *buf, int ct)
  {
    std::string function("Optitemp::Chiller_interface::modGet");
    std::stringstream message;

    int i = 0;
    fd_set readfds;
    struct timeval timeo;
    int status = 0;
    
    FD_ZERO( &readfds );
    FD_SET( fd, &readfds );
    
    timeo.tv_sec=1;
    timeo.tv_usec=0;
    
    status = select(FD_SETSIZE, &readfds, NULL, NULL, &timeo);
    if (status < 0){
      message << "Select failed.  System error msg: " << strerror(errno);
      this->log.write(function, LOG_ERROR, message.str());
      message.str("");
//      printf("Select failed.  System error msg = %s",strerror(errno));
    }
//    else {
//      status = 0;
//    }
    
    if (FD_ISSET( fd, &readfds)){
      for (i = 0; i < ct; i++){
        if (read(fd, buf + i, 1) != 1)
          break;
      }
    }
    else {
      this->log.write(function, LOG_ERROR, "Serial port timeout!");
//      printf("Serial port timeout!\n");
//      status = ERROR;
    }
    return (i);
    
  }
  /************* Optitemp::Chiller_interface::modGet ************/
  
  
  /************* Optitemp::Chiller_interface::modCRC ************/
  /***
   Generate a ModbusRTU cyclic redundancy check value.
   
   */
  unsigned short modCrc (unsigned char *pData, int ct)
  {
    unsigned short  v, work;
    int             eor, i, j;
    
    work = 0xffff;
    for (i = 0; i < ct; i++) {
      work ^= (unsigned short) *(pData+i);
      for (j = 0; j < 8; j++) {
        eor = work & 0x01;
        work >>= 1;
        if (eor)
          work ^= 0xa001;
      }
    }
    v = work << 8;
    v |= work >> 8;
    return (v);
  }
  /************* Optitemp::Chiller_interface::modCRC ************/
  
  
  /************* Optitemp::Chiller_interface::modWrite ************/
  /**
   Send ct words from the location pointed to by pData to the Modbus host,
   starting at register Reg.
   ct is now a WORD count rather than byte count.
   */
  int Chiller_interface::modWrite (int fd, unsigned char modaddr, 
                                   unsigned short Reg, unsigned char *pData, 
                                   int ct)
  {
    std::string function("Optitemp::Chiller_interface::modWrite");
    std::stringstream message;

    int i;
    unsigned char	buf[64], dummy;
    union {
      unsigned short a;
      unsigned char b[2];
    } work;
    struct timespec	Timer;
    char BUF[64];
    
    /* Test for open port */  //Not effective for broken connection
    if (fd <= 0){
      return (ROBO_sensor::ERROR_CLOSE_CONNECTION);
    }
    
    /* Build and send command block */
    buf[0] = modaddr;
    buf[1] = WRITE_REG_CMD;
    work.a = Reg;
    buf[2] = work.b[1];
    buf[3] = work.b[0];
    work.a = (unsigned short)ct;
    buf[4] = work.b[1];
    buf[5] = work.b[0];
    i = ct*2;
    buf[6] = (unsigned char)i;
    bcopy ((char*)pData, (char*)buf+7, i);
    i += 7;
    work.a = modCrc (buf, i);
    buf[i] = work.b[1];
    buf[i+1] = work.b[0];
    Timer.tv_sec = 0;
    Timer.tv_nsec = 10000000;
    nanosleep (&Timer, 0);  /* assure modbus host enough time */
    
    write (fd, (char*)buf, i+2);
    
    /* Get acknowledgement, or timeout */
    if (modGet (fd, buf, 2) != 2){
      return (ROBO_sensor::ERROR_DEVICE_TIMEOUT);
    }
    
    // Fault state
    if (buf[1] & 0x80){	  /* Bit 7 set = fault */
      if (modGet (fd, buf+2, 3) != 3){
        return (ROBO_sensor::ERROR_DEVICE_TIMEOUT);
      }
      work.a = modCrc (buf, 3);
      dummy = work.b[1];	//byte swap.
      work.b[1] = work.b[0];
      work.b[0] = dummy;
      if (bcmp ((char*)&work, (char*)buf + 3, 2)){
        bcopy ((char*)buf, (char*)BUF, 5);
        return (ROBO_sensor::ERROR_CRC_FAILURE);
      }
      this->log.write(function, LOG_ERROR, "chiller fault state!");
      return ((int)(*(buf+2)));
    }
    
    // Normal state
    else {
      if (modGet (fd, buf + 2, 6) != 6){
        return (ROBO_sensor::ERROR_DEVICE_TIMEOUT);
      }
      work.a = modCrc (buf, 6);
      dummy = work.b[1];	//byte swap.
      work.b[1] = work.b[0];
      work.b[0] = dummy;
      if (bcmp ((char*)&work, (char*)buf+6, 2)){
        bcopy ((char*)buf, (char*)BUF, 8);
        return (ROBO_sensor::ERROR_CRC_FAILURE);
      }
      else {
        return (NO_ERROR);
      }
    }
  }
  /************* Optitemp::Chiller_interface::modWrite ************/
  
  
  /************* Optitemp::Chiller_interface::modRead ************/
  /**
   Reads ct words from the Modbus host starting at register Reg, put the data
   into the location pointed to by pData.
   ct is now a WORD count instead of a byte count.
   Modified for little-endian operation, work.b values reversed.
   */
  int Chiller_interface::modRead (int fd, unsigned char modaddr, unsigned short Reg,
                                  unsigned char *pData, int ct)
  {
    std::string function("Optitemp::Chiller_interface::modRead");
    std::stringstream message;

    int i;
    unsigned char	buf[64], crc[2], dummy;
    union {
      unsigned short	a;
      unsigned char	b[2];
    } work;
    struct timespec	Timer;
    
    /* Test for open port */  //Not effective for broken connection
    if (fd <= 0){
      return (ROBO_sensor::ERROR_CLOSE_CONNECTION);
    }
    
    /* Build (with byte swapping) and send command block */
    buf[0] = modaddr;
    buf[1] = READ_REG_CMD;
    work.a = Reg;
    buf[2] = work.b[1];
    buf[3] = work.b[0];
    work.a = (unsigned short)ct;
    buf[4] = work.b[1];
    buf[5] = work.b[0];
    work.a = modCrc (buf, 6);
    buf[6] = work.b[1];
    buf[7] = work.b[0];
    Timer.tv_sec = 0;
    Timer.tv_nsec = 10000000;
    nanosleep (&Timer, 0);		/* assure modbus host enough time */
    
    write(fd, buf, 8);
    /* Get data back, or timeout */
    if (modGet (fd, buf, 2) != 2){
      return (ROBO_sensor::ERROR_DEVICE_TIMEOUT);
    }
    
    // Fault state
    if (buf[1] & 0x80){ 			/* Bit 7 set = fault */
      if (modGet (fd, buf + 2, 3) != 3){
        return (ROBO_sensor::ERROR_DEVICE_TIMEOUT);
      }
      work.a = modCrc (buf, 3);
      dummy = work.b[1];	//byte swap.
      work.b[1] = work.b[0];
      work.b[0] = dummy;
      
      if (bcmp ((char*)&work, (char*)buf + 3, 2)){
        return (ROBO_sensor::ERROR_CRC_FAILURE);
      }
      this->log.write(function, LOG_ERROR, "chiller fault state!");
      return ((int)(*(buf+2)));
    }

    // Normal state
    else {
      if (modGet (fd, buf + 2, 1) == 0){
        return (ROBO_sensor::ERROR_DEVICE_TIMEOUT);
      }
      i = (int)buf[2];
      if (modGet (fd, buf + 3, i) != i){
        return (ROBO_sensor::ERROR_DEVICE_TIMEOUT);
      }
      if (modGet (fd, crc, 2) != 2){
        return (ROBO_sensor::ERROR_DEVICE_TIMEOUT);
      }
      work.a = modCrc (buf, i + 3);
      dummy = work.b[1];	//byte swap.
      work.b[1] = work.b[0];
      work.b[0] = dummy;
      if (bcmp ((char*)&work, (char*)crc, 2)){
        return (ROBO_sensor::ERROR_CRC_FAILURE);
      }
      else{
        bcopy ((char*)buf + 3, (char*)pData, i);
        return (NO_ERROR);
      }
    }
  }
  /************* Optitemp::Chiller_interface::modRead ************/
  
  
  /************* Optitemp::Chiller_interface::get_state ************/
  /** Reads the status of the Chiller interface system.
   \note None.
   */
  int Chiller_interface::get_state(std::vector<float> & data)
  {
    std::stringstream reply, message;
    std::string function("Opti Temp::Chiller_interface::get_state");

    // Make sure the config file data are up to date
    if (this->config.modified() == true){
      if (this->get_config() != NO_ERROR){
        this->log.write(function, LOG_ERROR, "unable to get configuration!");
        return(ROBO_sensor::ERROR_CONFIGURATION_FILE);
      }
    }
    
    // Return if the connection is not open
    if (this->connection_open == false){
      this->log.write(function, LOG_ERROR, "chiller connection is not open!");
      return(ROBO_sensor::ERROR_NOT_INITIALIZED);
    }
    







    

    data.clear();
    
    int error = NO_ERROR;
    int ct = 1;
    unsigned char modaddr = 0x0001;
    unsigned short reg = 0x1000;
    float value_to_send = 0.0;
    unsigned char pData[8];
    union 
    {
      unsigned short a;
      unsigned char b[2];
    } value;

    for (int j = 0; j < 3; j++)
    {
      switch (j)
      {
        case 0:
          modaddr=1;
          reg=0x1000;	// Fluid temperature
          break;
        case 1:
          modaddr=1;
          reg=0x1001;	// Fluid temperature set point
          break;
        case 2:
          modaddr=2;
          reg=0x1000;	// Fluid flow rate in GPM
          break;
      }
      
      error =  modRead (sockfd, modaddr, reg, pData, ct);
      if (error != NO_ERROR){
        message << "error returned from reading value " << j << ":" << error;
        this->log.write(function, LOG_ERROR, message.str());
        message.str("");
        data.push_back(BAD_VALUE);
        error = ROBO_sensor::ERROR_BAD_SENSOR_DATA;
        break;
      }
      else {
        //measured temperature.
        if (modaddr==1 && reg==0x1000) {
          value.b[1]= pData[0];  //swap
          value.b[0]= pData[1];
          // Convert to Kelvin
          value_to_send = (float) value.a / 10.0 + 273.15;
# if DATA_TESTING
          std::cout << "Fluid temperature = " << (float) value.a / 10. << " C" 
                    << std::endl;
# endif
        }
        //temperature set point
        if (modaddr==1 && reg==0x1001){
          value.b[1]= pData[0];  //swap
          value.b[0]= pData[1];
          // Convert to Kelvin
          value_to_send = (float) value.a / 10.0 + 273.15;
# if DATA_TESTING
          std::cout << "Temperature set point = " << (float) value.a / 10. << " C"
                    << std::endl;
# endif
        }
        //measured flow.
        if (modaddr==2 && reg==0x1000){
          value.b[1]= pData[0];  //swap
          value.b[0]= pData[1];
          value_to_send = (float) value.a / 10.0;
# if DATA_TESTING
          std::cout << "Fluid flow = " << value_to_send << " GPM" << std::endl;
# endif
        }
      }
      data.push_back(value_to_send);
    }
    
    // If we made it this far, there should be no error. 
    return error;
  }
  /************* Optitemp::Chiller_interface::get_state ************/
  
  
  /***** Optitemp::Chiller_interface::change_temperature_setpoint ******/
  /**
   * Sends the command to set the chiller temperature setpint in degrees-C 
   */
  int Chiller_interface::change_temperature_setpoint(std::string set_point)
  {
    int error=0;
    std::stringstream com;
    std::stringstream message;
    std::string ss;
    std::string function("Optitemp::Chiller_interface::change_temperature_setpoint");
    
    unsigned char modaddr=0x0001;
    unsigned short reg=0x1001;
    int ct=1;
    unsigned char pData[8];
    union
    {
      unsigned short a;
      unsigned char b[2];
    } value;
    float sp;
    
    // Get the data to write and format for the Modbus packet.
    // Note that the data in the  registers are in 1/10ths of the unit of measure
    // Thus we multiply by 10 to get the value to write to the register.
    // After changing from Kelvin to Celsius 
    
    sp = (float)( ((atof(set_point.c_str())) )*10.0);
    
    if (sp > 300) sp = 300; // Clamp at 30 
    if (sp < 0) sp = 0; //! Check!!   HOW DO WE SET NETATIVE SET POINTS? 
    value.a = (unsigned short)sp;	 // Risk of overflow if we don't have limits on this.
    
    message<<"Writing chiller set point = " << sp << "/10 C";
    this->log.write(function, LOG_NO_ERROR, message.str());
    message.str("");
    
    // Now the packet bytes, which need to be swapped:
    pData[0]=value.b[1];
    pData[1]=value.b[0];
    
    error = modWrite(sockfd, modaddr, reg, pData, ct);
    
    if (error != NO_ERROR)
    {
      message <<"Error returned from modWrite(): " 
              << common_info.erreg.get_code(error);
      this->log.write(function, LOG_ERROR, message.str());
      message.str("");
    }
    return error;
  }
  /******** Optitemp::Chiller_interface::change_temperature_setpoint *********/
  
  
}

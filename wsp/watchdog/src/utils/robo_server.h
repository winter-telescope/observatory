/**
 \file robo_server.h
 \brief Header file for server communications.
 \details This file handles the server  side of the ROBO server-client 
 architecture.
 
 Copyright (c) 2009-2011 California Institute of Technology.
 \author Dr. Reed L. Riddle  riddle@caltech.edu
 \note
 
 <b>Version History</b>:
 \verbatim
 \endverbatim
 */

// Use a preprocessor statement to set a variable that checks if the header has
// already loaded...this avoids loading the header file more than once.
#ifndef ROBO_SERVER_H
#define ROBO_SERVER_H

# include <iostream>
# include <iomanip>
# include <vector>
# include <boost/thread.hpp>

// Local include files
# include "common.h"
# include "file_ops.h"
# include "communications.h"


/** \namespace ROBO_server
 \brief ROBO server software namespace
 \details ROBO server software namespace. */
namespace ROBO_server {
  
  /** \class Server
   \brief Base server class used for ROBO servers
   \details This class is the base class for all daemons in the ROBO software
   system.  Daemons are built by defining a new class that extends the properties
   of this class to the specifics of the daemon software.  This class is the 
   server side of the client-server architecture used by ROBO to control
   the system. */
  class Server {

  protected:
    
    /** \var ROBO_logfile log
     \details Log file class container */
    ROBO_logfile log;
    
    /** \var bool system_initialized
     \details Flag that holds system initialization state */
    bool system_initialized;
    
    /** \var boost::thread control_thread
     \details Boost thread variable for control */
    boost::thread control_thread;
    
    /** \var boost::thread command_thread
     \details Boost thread variable for command */
    boost::thread command_thread;
    
    /** \var boost::thread status_thread
     \details Boost thread variable for status */
    boost::thread status_thread;
    
    /** \var boost::thread watchdog_thread
     \details Boost thread variable for watchdog */
    boost::thread watchdog_thread;
    
    /** \var boost::thread abort_thread
     \details Boost thread variable for abort */
    boost::thread abort_thread;
    
    /** \var mutable boost::mutex command_mutex
     \details Mutex for blocking command variables */
    mutable boost::mutex command_mutex;
    
    /** \var ROBO_port port
     \details The connection port to the server */
    ROBO_port port;
    
    /** \var bool operating
     \details Flag that controls the operation of the server.  While this is 
     true, all threads continue to run, once it is changed to false all threads
     stop. */
    bool operating;
    
    /** \var bool processing_command
     \details Flag that is true when a command has been sent to the server and
     is being processed by the control() function. */
    bool processing_command;
    
    /** \var int command
     \details The flag for the current command.  These are numeric values 
     declared in enums for each type of command that can be sent through the
     server. */
    int command;
    
    /** \var int command_number
     \details Number of the current command being processed. */
    int command_number;
    
    /** \var std::vector<std::string> command_tokens
     \details Tokens that contain the parameters for each command sent to the
     server. */
    std::vector<std::string> command_tokens;
    
    /** \var std::string command_reply
     \details Reply string used to communicate server actions to clients */
    std::string command_reply;
    
    /** \var std::stringstream current_status
     \details Stream that contains the current status of the server.  This stream
     is sent to clients, that then interpret and react to the contents of the
     status string. */
    std::stringstream current_status;
    
    /** \var time_t server_time
     \details Time variable updated in control() function.  This tracks that the
     control() function thread doesn't stop operating. */
    time_t server_time;
    
    /** \var time_t status_time
     \details Time variable updated in status() function.  This tracks that the
     status() function thread doesn't stop operating.  The time is tracked to
     the level of an integer second. */
    time_t status_time;
    
    /** \var bool status_updated
     \details Flag that the status has updated. */
    bool status_updated;
    
    /** \var double status_time_micro
     \details Time variable updated in status() function.  This time variable
     tracks the time to a fraction of a second. */
    double status_time_micro;
    
    /** \var std::string server_name
     \details Name for the server.  Since some functions are common, it is 
     necessary to save the server name separately for logging purposes.  Set this
     in the initialize_class function; the format should be something like 
     "AO::Server::" to map to the common funciton names. */
    std::string server_name;

    /** \var int max_watchdog_diff
     \details The maximum time that the watchdog waits when the control() thread
     locks up before killing the server. Some servers have operations that take
     time to execute in the control() thread, this allows for that extra time. */
    int max_watchdog_diff;
    
    std::string control_thread_status;
    
    bool shutdown_flag;
    
    // These four functions are all virtual, they have to be replaced with local
    // functions in any classes that inherit from the Server class.
    
    /**************** ROBO_server::Server::initialize_class ****************/
    /**
     This initializes the class functions for the server.  It is created
     separately for each class that inherits from this class.  Each class will
     have individual variables that have to be initialized, but they should also
     start all the threads and initialize the common variables.
     */
//    virtual void initialize_class() = 0;
    /**************** ROBO_server::Server::initialize_class ****************/

    /**************** ROBO_server::Server::initialize_class ****************/
    /**
     This initializes the class functions for the server.  It is created
     separately for each class that inherits from this class.  Each class will
     have individual variables that have to be initialized, but they should also
     start all the threads and initialize the common variables.
     */
    virtual void initialize_class(std::string logname_in) = 0;
    /**************** ROBO_server::Server::initialize_class ****************/

    /**************** ROBO_server::Server::handle_command ****************/
    /**
     This handles any commands that are sent to the server.  Every server is
     different, so while these functions will all be structured and operate 
     similarly, what they handle will be completely different.  This function
     runs in a thread started by the control() function each time a command is
     sent to the server.
     */
    virtual void handle_command() = 0;
    /**************** ROBO_server::Server::handle_command ****************/

    /**************** ROBO_server::Server::control ****************/
    /**
     Main control function that runs in a separate thread.  This is the function
     that communicates with the clients.  Commands are received, and the 
     handle_command() function is started in a separate thread.  Replies are sent
     to clients as appropriate for commands.  Each second, an output status 
     message is also sent out.
     */
    virtual void control() = 0;
    /**************** ROBO_server::Server::control ****************/

    /**************** ROBO_server::Server::status ****************/
    /**
     This function is run in a separate thread.  It is used to monitor the status
     of the daemon subsystems.  Each second, the status is composed and saved in
     a class variable that is then sent to the clients by the control() function.
     The status is completely different for every subsystem, each will have its
     own function to do this.
     */
    virtual void status() = 0;
    /**************** ROBO_server::Server::status ****************/


    /**************** ROBO_server::Server::watchdog ****************/
    /**
     This function is run when the watchdog_thread is set up in the initialize_class
     function.  
     
     The watchdog continually checks the server_time variable that is
     set each second in the control() function; if the control() function stops
     looping the server won't receive communications from clients, so it is 
     effectively locked.  When that happens, this function catches that and
     exits the program; the ROBO system automatically restarts a server when
     the client connection is dropped unexpectedly.
     
     The watchdog also checks the status_time variable that is set each second
     in the status() function.  Again, if the status function stops updating the
     watchdog will exit the server.
     
     Other functions for watchdog activities can be added into this function as
     necessary for monitoring the operation of the server.  
     */
    void watchdog()
    {
      // Wait five seconds to give enough time for the other threads to start
      timeout(5);

      // Log that the watchdog thread has started
      std::string function = this->server_name + "watchdog";
      this->log.write(function, false, "starting the watchdog thread");
      
      std::stringstream message;      // Temporary message container
      bool processing_command_local;  // Local copy of command processing flag
      bool local_operating;           // Local copy of operating variable
      time_t current_time = time(NULL);   // Current time for the watchdog
      
      // These variables are copies of the class time variables for the server
      // and status threads
      time_t server_time_local;
      time_t status_time_local;
      
      // Get copies of the class variables and put them in the local versions.
      // This is protected by a mutex since the variables come from other threads
      boost::mutex::scoped_lock lock(command_mutex);
      server_time_local = this->server_time;
      status_time_local = this->status_time;
      processing_command_local = this->processing_command;
      local_operating = this->operating;
      lock.unlock();
      
      int server_lockups = 0;     // Number of times control thread doesn't respond
      int status_lockups = 0;     // Number of times status thread doesn't respond
      int shutdown = false;  // Flag to shut down the program, which happens
                                  // if the other threads don't respond
      
      // We do this as long as the class operating variable remains true
      while (local_operating == true){
        
        // Get the current time in this thread
        current_time = time(NULL);
        
//        if (current_time - server_time_local > 2 &&
//            command_in_progress_local == false){
        // Check the difference with the control thread time.  If the difference is
        // greater than 2 seconds there is a problem in the control thread, so
        // log a message and increase the lockup counter
        if (current_time - server_time_local > 2){
          message << "time difference found, control thread has apparently locked up, time: "
                  << get_current_time(SECOND_MILLI) << " time: watchdog "
                  << current_time << " server " << server_time_local
                  << " difference " << current_time - server_time_local
                  << " command in progress: "
                  << print_bool(processing_command_local, PRINT_BOOL_TRUE_FALSE)
									<< " control thread status: " << this->control_thread_status;
          log.write(function, true, message.str());
          message.str("");
        
          server_lockups++;
          // If the control thread has been locked up for three seconds, it means
          // something bad has happened.  Log it, set the shutdown flag to true.
//          if (server_lockups == this->max_watchdog_diff){
          if (server_lockups >= 5){
            message << "control thread locked for 5 seconds, shutting down";
//            message << "control thread locked for "<< this->max_watchdog_diff + 2
//                    << " seconds, shutting down";
            this->log.write(function, true, message.str());
            message.str("");
            shutdown = true;
          }
        }
        // If there isn't a time error, reset the lockup variable if it is not 0,
        // and log that things are back to normal.
        else {
          if (server_lockups > 0){
            this->log.write(function, false,
                            "control thread fixed itself, continuing operations");
            server_lockups = 0;
          }
        }
        
        // Check the difference with the status thread time.  If the difference is
        // greater than 2 seconds there is a problem in the status thread, so
        // log a message and increase the lockup counter
//        if (current_time - status_time_local > 2){
        if (current_time - status_time_local > this->max_watchdog_diff){
          message << "time difference found, status thread has apparently locked up, time: "
          << get_current_time(SECOND_MILLI) << " time: watchdog "
          << current_time << " status " << status_time_local
          << " difference " << current_time - status_time_local
          << " command in progress: "
          << print_bool(processing_command_local, PRINT_BOOL_TRUE_FALSE);
          log.write(function, true, message.str());
          message.str("");
          
          status_lockups++;
          // If the control thread has been locked up for three seconds, it means
          // something bad has happened.  Log it, set the shutdown flag to true.
//          if (status_lockups == this->max_watchdog_diff){
          if (status_lockups >= this->max_watchdog_diff + 2){
            message << "status thread locked for " << this->max_watchdog_diff + 2
                    << " seconds, shutting down";
            this->log.write(function, true, message.str());
            message.str("");
            shutdown = true;
          }
        }
        // If there isn't a time error, reset the lockup variable if it is not 0,
        // and log that things are back to normal.
        else {
          if (status_lockups > 0){
            this->log.write(function, false,
                            "status thread fixed itself, continuing operations");
            status_lockups = 0;
          }
        }
        
        // If the shutdown flag is true, then a thread has crashed and the server
        // needs to be shut down.  This logs it and tries to kill everything.
        if (shutdown == true){
          this->log.write(function, true, "exiting the server!");
          lock.lock();
          this->operating = false;
          lock.unlock();
          timeout(1);
//          this->control_thread.join();
//          this->status_thread.join();
          exit(-1);
        }
        
        // The first timeout waits until the end of the current second.  All the
        // threads have this timeout.  It then waits an extra 0.1s with the second
        // timeout, in order to make sure to get the new time measurement out of
        // the other threads.
        timeout();
        timeout(0.1);
        
        // Get copies of the class variables and put them in the local versions.
        // This is protected by a mutex since the variables come from other threads
//        lock.lock();
        server_time_local = this->server_time;
        status_time_local = this->status_time;
        processing_command_local = this->processing_command;
        local_operating = this->operating;
//        lock.unlock();
      }
      
      // Log that the function is done
      this->log.write(function, false, "stopping the watchdog thread");
      
    }
    /**************** ROBO_server::Server::watchdog ****************/

    
    /**************** ROBO_server::Server::print_params ****************/
    /**
     Creates a string that lists the tokens sent to the server in a command.  
     Use this to print out messages that include all the tokens input to the
     server.  Does not include the command.
     \param [tokens] List of tokens in command sent to server.  This is the 
     entire command string tokenized, so it includes the command as well.
     */
    std::string print_params(std::vector<std::string> tokens)
    {
      std::stringstream message;  // Temporary message buffer
      
      // Print out all the tokens.  Don't print token 0, as that is the command
      // for the server.
      for (unsigned int i = 1; i < tokens.size(); i++){
        message << tokens[i] ;
        // if there is another token then insert a space
        if ( (i+1) < tokens.size() ) message << " ";
      }
      
      // Send a string back for the calling function to deal with
      return(message.str());
    }
    /**************** ROBO_server::Server::print_params ****************/

    
    /********* ROBO_server::Server::handle_message_parameter_error *********/
    /**
     Formats command tokens into a string for log output when there is an error
     in parameters sent in a server command.  Does not print the command.
     \param [tokens] List of tokens in command sent to server.  This is the
     entire command string tokenized, so it includes the command as well.
     */
    std::string handle_message_parameter_error(std::vector<std::string> tokens)
    {
      std::stringstream message;  // Temporary message buffer
      
      // Print the command parameter tokens.  Don't print token 0, as that is the
      // command for the server.
      message << "server parameter error, parameters: "
      << this->print_params(tokens);
      
      // Send a string back for the calling function to deal with
      return(message.str());
    }
    /********* ROBO_server::Server::handle_message_parameter_error *********/
    
    
    /********* ROBO_server::Server::handle_message_parameter_error *********/
    /**
     Formats command tokens into a string for log output when there is an error
     in parameters sent in a server command.  Does not print the command.
     \param [tokens] List of tokens in command sent to server.  This is the
     entire command string tokenized, so it includes the command as well.
     */
    std::string handle_message_parameter_error(int command,
                                               std::vector<std::string> tokens)
    {
      std::stringstream message;  // Temporary message buffer
      
      // Print the command parameter tokens.  Don't print token 0, as that is the
      // command for the server.
      message << "server parameter error, command: " << command << " parameters: "
              << this->print_params(tokens);
      
      // Send a string back for the calling function to deal with
      return(message.str());
    }
    /********* ROBO_server::Server::handle_message_parameter_error *********/
    
    
    /**************** ROBROBO_serverOAO_weather::read_message ****************/
    /**
     Takes a string from a message passed to the system and converts it into 
     tokens that are passed back.
     \param [message] The input message string
     \return [tokens] A string vector of tokens from the message string
     \note The character € cannot be used in any text messages!.
     */
    std::vector<std::string> read_message(std::string message)
    {
      std::vector<std::string> tokens;  // Temporary tokens
      std::vector<std::string> tokens2;  // Temporary tokens
      
      // Check for a text message included with the server message. This uses a
      // specific character, €, that shouldn't show up in any messages.
      Tokenize(message, tokens2, "€");
      if (tokens2.size() == 2){
        // Use the tokenizer to break up the first part of the message
        Tokenize(tokens2[0], tokens, " \t\n\0\r");
        // Set the text message to the last token
        tokens.push_back(tokens2[1]);
      }

      // If there is no message, use the tokenizer to break up the whole message
      else {
        Tokenize(message, tokens, " \t\n\0\r");
      }
      
      // Return the tokens
      return (tokens);
    }
    /**************** ROBO_server::read_message ****************/

  public:
    

    /**************** ROBO_server::Server::Server ****************/
    /**
     The constructor for the server class.  This is here just to use it, each
     subclass must create its own constructor and set up the server for 
     operation.
     */
    explicit Server(){}
    /**************** ROBO_server::Server::Server ****************/

    
    /**************** ROBO_server::Server::~Server ****************/
    /**
     The destructor for the server class.  This handles closing out all of the
     server functions.  Do not try to handle any of this in the destructors of
     subclasses; only handle something that is class specific for that server
     in subclass destructors.
     \note None.
     */
    virtual ~Server()
    {
      // Log that the destructor is starting
      std::string function = this->server_name + "~Server";
      this->log.write(function, false, "deconstructing Server class");
            
      // This flag should be set in order to stop the server, but if something
      // else causes the server to stop this is here to make sure the threads
      // are all given the stop signal.  Blocked with nutex to protect it.
      boost::mutex::scoped_lock lock(this->command_mutex);
      this->operating = false;
      lock.unlock();
      
      // Join all the threads.
      this->control_thread.join();
      this->log.write(function, false, "joined control thread");
      this->watchdog_thread.join();
      this->log.write(function, false, "joined watchdog thread");
      this->status_thread.join();
      this->log.write(function, false, "joined status thread");
//      this->error_monitor_thread.join();
//      this->log.write(function, false, "joined error monitor thread");
      
      // Log that this is done...if this doesn't show up then a thread did not
      // join properly.
      this->log.write(function, false, "finished Server class destruction");
    }
    /**************** ROBO_server::Server::~Server ****************/

    
    /**************** ROBO_server::Server::run ****************/
    /**
     This function actually runs the server.  When the server class is created,
     the variables are set up and the threads are started.  But, a function is
     required to keep the server running.  This function should be used as 
     follows:
     \code
     int main(int argc, char* argv[])
     {
       ROBO_port port;  // The connection port to the daemon
       ROBO_server::Server server(port);
       server.run()
     }
     \endcode
     A signal is sent through the server interface to stop the server by setting
     this->operating to false, at which point the run() function terminates and
     the program ends.  
     */
    void run()
    {
      // Log the server is starting
      std::string function = this->server_name + "run";
      this->log.write(function, false, "running the server");
      
      // Set the local copy of the operating variable to the class copy.  This
      // has to be protected by a mutex to avoid locking up threads.  If the
      // threads lock up the watchdog should see it and shut everything down.
      boost::mutex::scoped_lock lock(this->command_mutex);
      bool local_operating = this->operating;
      lock.unlock();
      
      // Check the operating variable each second to see if it has changed the
      // flag.  If it changes to false, then the server is done running and
      // shuts down.
      while(local_operating == true){
        timeout(1.0);  // This times out to the end of the current second
        lock.lock();
        local_operating = this->operating;
        lock.unlock();
      }
      
      // Log that the function is exiting to confirm the server isn't running.
      this->log.write(function, false, "operating flag is false, stopping the server");
    };
    /**************** ROBO_server::Server::run ****************/

  };

}

#endif

/**
 * @file comm.min.h
 * @brief Master Communications Header File
 * @date 2010-07-27
 *
 * @details Declares all of the classes used for communications.
 *
 * Copyright (c) 2010 California Institute of Technology
 * @author Alexander Rudy
 * @note This file combines many other header files into one convenient one.
 *
 *
 * <b>Version History:</b>
 *
 */
/**
 \file tcpip_protected_queue.h
 \brief Definition of a thread-safe double ended queue for TCPIP
 \date 2010-06-15

 \details Will define a threadsafe TCPIP double ended queue for use in the future to handle threaded operations to read and write from queues.

 Copyright (c) 2010 California Institute of Technology
 \author Alexander Rudy
 \note

 <b>Version History:</b>

 */
#ifndef TCPIP_PROTECTED_QUEUE_H_C2MO9C1
#define TCPIP_PROTECTED_QUEUE_H_C2MO9C1

#include <boost/thread.hpp>
#include <deque>

// Local include files
# include "common.h"
# include "file_ops.h"


typedef enum {
	ROBO_PORT_LGSD = 62000,//50000,
	ROBO_PORT_ADCD = 62003,//50010,
  ROBO_PORT_AOSYS = 62006,//50020,
  ROBO_PORT_WEATHERD = 62009,//50030,
  ROBO_PORT_TELSTATD = 62012,//50040,
  ROBO_PORT_TCSD = 62015,//50050,
  ROBO_PORT_VICD = 62018,//50060,
  ROBO_PORT_IRCD = 62021,//50070,
  ROBO_PORT_ROBOD = 62024,//50080,
  ROBO_PORT_TIP_TILT = 62027,//50090,
  ROBO_PORT_QUEUED = 62030,//50100,
  ROBO_PORT_GUIDED = 62033,//50110,
  ROBO_PORT_POWERD = 62036,//50120,
  ROBO_PORT_FILTERD = 62039,//50130,
  ROBO_PORT_SHUTTERD = 62042,//50140,
  ROBO_PORT_MONITORD = 62045,//50150,
  ROBO_PORT_WATCHDOGD = 62048,//50160,
  ROBO_PORT_FITSD = 62051,//50170,
  ROBO_PORT_MOTIOND = 62054,//50180,
  ROBO_PORT_DATAD = 62057,//50190,
  ROBO_PORT_ILLUMINATORD = 62060,//50200,
  ROBO_PORT_MESSAGED = 62063,//50210
  ROBO_PORT_FOCUSD = 62066//50210
} ROBO_port;

void reset_server(std::string executable, pid_t pid, ROBO_port port, 
                  std::string operations = "", std::string host = "localhost");
void kill_server(std::string executable, pid_t pid_in, std::string host);



/** \namespace TCPIP */
namespace TCPIP
{

  /**************** TCPIP::read_message ****************/
  /**
   Takes a string from a message passed to the system and converts it into 
   tokens that are passed back.
   \param [message] The input message string
   \return [tokens] A string vector of tokens from the message string
   \note None.
   */
/*  inline std::vector<std::string> read_message(std::string message)
  {
    std::vector<std::string> tokens;  // Temporary tokens
    
    // Use the tokenizer to break up the message
    Tokenize(message, tokens, " ");
    
    // Return the tokens
    return (tokens);
  }*/
  /**************** TCPIP::read_message ****************/
  
  

	/** A thread-safe queue

   \details Implements a mutex lock to protect the queue from simultaneous read-writes from the same program in different threads. The double ended queue has the basic queue operations, but lacks an iterator.

   */
	class tcpip_protected_queue
  {
  public:

    /** Constructor */
    tcpip_protected_queue();

    /** Destructor */
    virtual ~tcpip_protected_queue();

    /** Determines if the queue is empty. */
    bool empty();

    /** Returns the first element from the queue. */
    std::string front();

    /** Returns the last element from the queue. */
    std::string back();

    /** Removes the first element from the queue */
    void pop_front();

    /** Removes the last element from the queue */
    void pop_back();

    /** Adds an element to the front of the queue */
    void push_front(std::string item);

    /** Adds an element to the back of the queue */
    void push_back(std::string item);

  private:

    /** Locks the queue, preventing other threads from accessing it. */
    void lock();

    /** Attempts to unlock the queue so it can access it. Waits if the queue is locked. */
    void unlock();

    /** Releases the queue from a lock so that another thread may unlock it. */
    void release();

    /** The data structure */
    std::deque<std::string> queue;

    /** The mutual exclusion object */
    boost::mutex mut;

    /** The condition variable which notifies other threads. */
    boost::condition_variable cond;

    /** Simple switch. */
    bool locked;

  };

} /* TCPIP */

#endif /* end of include guard: TCPIP_PROTECTED_QUEUE_H_C2MO9C1 */



/**
 \file tcpip_globals.h
 \brief Parameters which are common to the entire TCPIP namespace.

 \details Contains the constants used throughout the TCPIP namespace to pass messages back and forth and interpret
 commands. Also contains settings about verbosity and the master enable timeout flag.

 Copyright (c) 2010 California Institute of Technology
 \author Alexander Rudy
 \note

 <b>Version History:</b>

 */


#ifndef TCPIP_GLOBALS_H_8AKT9HJ1
#define TCPIP_GLOBALS_H_8AKT9HJ1


#include <cstdlib>

//REMOVED include "tcpip_protected_queue.h"


/**
 \namespace TCPIP
 \brief Namespace for the TCPIP client/server functions and the tcpip_server and tcpip_client classes.


 \details This namespace contains two main classes for handling server-client connections.

 The tcpip_server class creates a server which will accept an unlimited number of connections and will run until it recieves a local tcpip_server::shutdown command or the TCPIP::SHUTDOWN_MESSAGE from the client. The default behavior of the server is to echo commands sent to it to all of the attached clients. Each server connection will create a server_session object to handle the individual connection. All sever_session objects use a single broadcast_room object to handle their connection status and message interaction.

 The tcpip_client class creates a clinet which will connect to a single server, and pass messages to that server as well as recieve them. By default, the client has control string ability, meaning that passing the client the string TCPIP::EXIT_COMMAND or TCPIP::SHUTDOWN_COMMAND to tcpip_client::process_outbound_message will trigger the shutdown or exit methods correctly.

 */
namespace TCPIP
{

	/** A queue object which is thread safe and automatically locks/unlocks for data operations. */
	typedef tcpip_protected_queue tcpip_queue;
  
  /* Strings to indicate status of commands. Be sure to leave spaces intact if
     changing these strings. If the string has a space at the end of it, make
     sure to keep it that way. Otherwise, ADCD::Client::ADCD_client_thread will
     break. */
	const std::string WELCOME_MESSAGE	 = "WELCOME ";  //!<Message sent from server to clients when connection has been made.
	const std::string EXIT_COMMAND		 = "EXIT ";     //!<Command input to client to trigger exit
	const std::string EXIT_MESSAGE		 = "IMGONE ";   //!<Message passed by system to tell units to exit
	const std::string SHUTDOWN_COMMAND = "SHUTDOWN "; //!<Command input to client to trigger shutdown
	const std::string SHUTDOWN_MESSAGE = "GOHOME ";   //!< Message passed by system to tell units to shutdown.
	const std::string CONFIRM_MESSAGE  = "CONFIRM ";  //!< Message passed by system to confirm reciept of system command.
	const std::string ERROR_MESSAGE 	 = "ERROR ";   //!< Message passed by system to indicate an error message that is being passed back
	const std::string COMPLETE_MESSAGE = "COMPLETE ";//!< Message passed by system to confirm completion of a command.
	const std::string RECEIVED_MESSAGE = "RECEIVED ";//!< Message passed by system to confirm reciept of a command.
	const std::string FAILED_MESSAGE 	 = "FAILED ";  //!< Message passed by system to indicate failure
	const std::string PROCESS_MESSAGE  = "PROCESS "; //!< Message passed by system to indicate a process message that is being passed back
	const std::string STATUS_MESSAGE   = "STATUS ";  //!< Message passed by system to indicate a process message that is being passed back
	const std::string BUSY_MESSAGE     = "BUSY ";  //!< Message passed by system to indicate a busy message that is being passed back
  const std::string DATA_MESSAGE    = "DATA"; //!< Message passed by system to indicate a data message is being passed back 
//	const std::string ERROR_CODE       = "ERROR_CODE "; //!< Message passed by system to indicate an error code that is being passed back (unrequested)
//	const std::string ERROR_CODE_CHECK = "ERROR_CODE_CHECK "; //!< Message passed by system to indicate an error code that is being passed back
//	const std::string ERROR_ZENITH_MAX = "ERROR_ZENITH_MAX";  //!< Message passed by system to indicate that the current zenith angle is too large (unrequested)
  const std::string TIP_TILT_MESSAGE   = "TIP_TILT ";  //!< Message passed by system to indicate a tip-tilt message that is being passed back
  const std::string FOCUS_MESSAGE   = "FOCUS ";  //!< Message passed by system to indicate a focus message that is being passed back

	enum  { EV_EXIT, EV_START, EV_SHUTDOWN, EV_CONFIRM }; //!< Event Value Switches for handling inbound events
	enum  { CV_EXIT, CV_START, CV_SHUTDOWN }; //!< Control Value Switches for controlling commands

	enum  { LARGE=20000, MAX_LENGTH=1024, INPUT_LENGTH=1024, HEADER_LENGTH=4 }; //!< System Maximums

	enum  { MAX_CONNECT_ATTEMPTS=20 }; //!< Maximum number of times the client should try to connect to the server before throwing an error.

	enum  { CLIENT_TIMEOUT=60 , SERVER_TIMEOUT=5, SESSION_TIMEOUT=5 }; //!< values for timeout

	enum  { TCP_CONNECT,TCP_READ,TCP_WRITE, TCP_FINAL_WRITE }; //!<Values determine current commands

	const std::string TCP_OP_CONNECT = "TCP Async Connect"; //!<Error message for a connect command
	const std::string TCP_OP_ACCEPT = "TCP Async Accept"; //!<Error message for an accept command
	const std::string TCP_OP_READ = "TCP Async Read"; //!<Error message for a read command
	const std::string TCP_OP_WRITE = "TCP Async Write"; //!<Error message for a normal write command
	const std::string TCP_OP_FINAL_WRITE = "TCP Single Write"; //!<Error message for a single write command

	const int DBM_VERBOSE=0;//!<Setting VERBOSE to 0 disables all extraneous output

	const bool DBM_DANGER=false;	//!<Applies to declared methods which MUST be redefined in higher classes.
	const bool DBM_NOTICE=false;//!<Applies to flags
	const bool DBM_VAR=true;		//!<Prints out variable values at interesting points
	const bool DBM_INFO=true;	//!<Prints out possibly useful information, esp. if there would otherwise be no action
	const bool DBM_BEGIN=false; //!<Applies to general methods.
	const bool DBM_START=true; //!<Applies to start of io_service stack ops.
	const bool DBM_END=true;		//!<Applies to the end of general methods.
	const bool DBM_HANDLE=true;//!<Applies to the beginning of handlers
	const bool DBM_CONST=false; //!<Applies to the end of constructors
	const bool DBM_ERROR=true; //!<Prints out error messages
	const bool DBM_WARNING=true;//!<Prints things that are not what they should be but may not kill the program entirely.

	const bool ENABLE_TIMEOUT=false;//!<Turns timeout functionality on or off globally in program.

} /* TCPIP */

#endif /* end of include guard: TCPIP_GLOBALS_H_8AKT9HJ1 */
/**
 \file tcpip_debug.h
 \brief Declaration of the tcpip_debug class
 \date 2010-06-14

 \details Class used to output messages to standard output.

 Copyright (c) 2010 California Institute of Technology
 \author Alexander Rudy
 \note

 <b>Version History:</b>

 */

#ifndef TCPIP_DEBUG_H_CJ5WTPIQ
#define TCPIP_DEBUG_H_CJ5WTPIQ

#include <iostream>
#include <string>

//REMOVED include "tcpip_globals.h"

/** \namespace TCPIP */
namespace TCPIP
{
	/** \brief Sets up debugging messages.

   \details Outputs debugging messages to standard output if VERBOSE>0 and if the particular debugging flag is on. The debugging flags are in tcpip_globals.h

   */
	class tcpip_debug
  {
  public:

		/** Constructor */
    tcpip_debug () {
      // Set the log file name to the class log name and open the log
      this->log.filename = common_info.log_dir + "communications.log";
    }

		/** Destructor */
    virtual ~tcpip_debug () {}

		/** Outputs a debugging message if VERBOSE>0 */
    void dbm(std::string message) {
      if(DBM_VERBOSE>0) {
        this->log.write("tcpip_debug message", false, message);
        //std::cout<<message<<std::endl;
      }
      return;
    }
    
		/** Outputs a debugging message if VERBOSE>0 */
    void dbm(std::string message, std::string function) {
      if(DBM_VERBOSE>0) {
        this->log.write(function, false, message);
        //std::cout<<message<<std::endl;
      }
      return;
    }
    
		/** Outputs a debugging message if VERBOSE>0 and the flag is set. */
    void dbm(std::string message, bool flag) {
      if(DBM_VERBOSE>0 && flag) {
        this->log.write("tcpip_debug message", false, message);
        //std::cout<<message<<std::endl;
      }
      return;
    }

		/** Outputs a debugging message if VERBOSE>0 and the flag is set. */
    void dbm(std::string message, std::string function, bool flag) {
      if(DBM_VERBOSE>0 && flag) {
        this->log.write(function, false, message);
        //std::cout<<message<<std::endl;
      }
      return;
    }
    
  private:

    /** \var ROBO_logfile log
     \details Log file class container */
    ROBO_logfile log;
    
  };

} /* TCPIP */


#endif /* end of include guard: TCPIP_DEBUG_H_CJ5WTPIQ */
/**
 \file tcpip_handler.h
 \brief Function definitions for the tcpip_strings class.

 \details Defines the tcpip_strings class which provides methods to handle messages strings.

 Copyright (c) 2010 California Institute of Technology
 \author Alexander Rudy
 \note

 <b>Version History:</b>

 */

#ifndef TCPIP_STRINGS_H_GPPTI78V
#define TCPIP_STRINGS_H_GPPTI78V

#include <map>
//REMOVED include "tcpip_debug.h"

namespace TCPIP {

  /** \brief Provides methods which handle message strings.

   \details The methods manipulate TCPIP class message strings to add/remove prefixes or to determine their appropriate control switch.

   */
  class tcpip_strings : protected tcpip_debug {

  public:

    /** Constructor */
    tcpip_strings();

		/** Destructor */
    virtual ~tcpip_strings();

		/** Determines whether the input string has a given prefix */
    bool check_prefix(std::string message, std::string prefix);

		/** Strips a given prefix from a string */
    std::string strip_prefix(std::string message, std::string prefix);

		/** Adds a given prefix to a string */
    std::string prep_prefix(std::string message, std::string);

  protected:

    /** Returns an appropriate switch value for the given map */
    int get_switch(std::string input,std::map<std::string,int> cmap);

		/** Sets up a command map */
    void init_map();

		/** A command map for processing inbound strings. It is initalized in TCPIP::tcpip_strings::init_map */
    std::map<std::string,int> premap;

  }; /* End of tcpip_strings */


} /* TCPIP */




#endif /* end of include guard: TCPIP_STRINGS_H_GPPTI78V */
/**
 \file tcpip_handler.h
 \brief Function definitions for the tcpip_handler class.

 \details Defines the tcpip_handler class which provides methods to handle messages and the state of a session or group of sessions.

 Copyright (c) 2010 California Institute of Technology
 \author Alexander Rudy
 \note

 <b>Version History:</b>

 */



#ifndef TCPIP_HANDLER_H_JM1QXH5N
#define TCPIP_HANDLER_H_JM1QXH5N

#include <cstdlib>
#include <string>
#include <deque>
#include <map>

//REMOVED include "tcpip_debug.h"
//REMOVED include "tcpip_strings.h"

namespace TCPIP
{


  /**
   \brief Provides methods to handle messages and the state of a session or group of sessions

   \details This class creates methods which handle reading and sending strings using an inbox and an outbox. Strings
   are read from the session using the TCPIP::tcpip_handler::read method, and the inbox and outbox. The inbox holds
   commmands which the session does not need to process and are ready for use by the program. The outbox holds
   messages which are ready to be sent. The class also holds flags for the current status of the session.

   */
  class tcpip_handler : protected tcpip_strings
  {
  public:

    /** Constructor */
    tcpip_handler ();

    /** Destructor */
    ~tcpip_handler ();

    /** Sends a string */
    virtual void send(std::string message) =0;

    /** Sends a single string */
    virtual void single_send(std::string message) =0;

    /** Sends a single string, without header */
    virtual void simple_send(std::string message) =0;

    /** Listens for inbound communication */
    virtual void listen() =0;

    /** Reads a string from input and processes it*/
    virtual void read(std::string command);

    /** Returns a pointer to the departure queue for the current session */
    tcpip_queue* get_outbox();

    /** Returns a pointer to the processed arrival queue for the current session */
    tcpip_queue* get_inbox();

    /** Sets the inbox pointer to point at the given inbox */
    void set_inbox(tcpip_queue* new_inbox);

    /** Sets the outbox pointer to point at the given outbox*/
    void set_outbox(tcpip_queue* new_outbox);

    /** Determines whether the handler has an open connection */
    virtual  bool is_open();

    /** Tells the handler to quit whatever it is doing */
    virtual void quit();

    /** Determines whether the handler has been instructed to shutdown */
    bool is_shutdown();

    /** Tells the handler to shutdown at the next convinent point */
    void shutdown();

    /** Determines whether the handler has been told to quit*/
    bool is_exit();

    /** Tells the handler to exit at the next convinent point */
    void exit();

    /** Determines whetehr the handler was commanded or triggered to do the next control action*/
    bool is_triggered();

    /** Tells the handler that it was triggered to do the next control action */
    void trigger();

    /** Determines whether the peer has received the command.*/
    bool is_confirmed();

    /** Tells the handler that the command was received */
    void confirm();

    /** Resets the trigger, shutdown and exit commands */
    void reset();

  	/** Count the number of open connections. */
  	virtual int connection_count();


  private:

    /** Determines whether the session should shutdown at the next clean opportunity*/
    bool switch_shutdown;
    /** Determines whether the session should exit at the next clean opportunity*/
    bool switch_exit;
    /** Determines whether the session was told to shutdown/exit by its peer*/
    bool switch_triggered;
    /** Determines whether the session confirmed the last command by its peer. */
    bool switch_confirm;

  protected:

    /** A queue of processed messages waiting to be handled by the program*/ tcpip_queue * inbox;

    /** A queue of messages waiting to be sent by the session */ tcpip_queue * outbox;

    /** A pointer to the object containing the appropriate local switches

     \details This pointer is almost always set to "this" so that the local switches only effect the actions of the
     current session. The local switch applies to tcpip_handler::confirm, tcpip_handler::trigger and tcpip_handler::exit.

     */
    tcpip_handler * switch_local;

    /** A pointer to the object containing the appropriate general switches

     \details This pointer can be set to an object with the appropriate tcpip_handler properties when it is needed to
     maintain many sessions. This works well to control a group of sessions, as any individual session can tell the
     entire group to shutdown at the next appropriate moment. The general switch currently only applies to tcpip_handler::shutdown.

     */

    tcpip_handler * switch_general;

  private:

    /** A queue of messages waiting to be sent.

     \details This queue is setup as the default outbox, but will be over-ridden by changing the outbox pointer or
     using the TCPIP::tcpip_handler::set_outbox

     */
    tcpip_queue local_outbox;

    /** A queue of processed messages waiting to be acted on by the program

     \details This queue is setup as the default outbox, but will be over-ridden by changing the inbox pointer or
     using the TCPIP::tcpip_handler::set_inbox

     */
    tcpip_queue local_inbox;

  };

} /* TCPIP */

#endif /* end of include guard: TCPIP_HANDLER_H_JM1QXH5N */
/**
 \file tcpip_session.h
 \brief Provides commands to handle tcp reads, writes and timeouts using boost::asio.
 \date 2010-06-14

 \details The tcpip_session class provides the commands which use the boost::asio library to communicate with another object over a TCP/IP connection. The class does not provide connect or accept commands, only commands that are common to the client and server models.

 Copyright (c) 2010 California Institute of Technology
 \author Alexander Rudy
 \note

 <b>Version History:</b>

 */

#ifndef TCPIP_SESSION_H_F1DB1D57
#define TCPIP_SESSION_H_F1DB1D57


#include <boost/asio.hpp>
#include <boost/thread.hpp>

//REMOVED include "tcpip_globals.h"
//REMOVED include "tcpip_handler.h"

namespace TCPIP {

  /** \brief Handles TCPIP reads and writes for the io_service and for external objects.

   \details Provides the commands which use the boost::asio library to communicate with another object over a TCP/IP connection. The class does not provide connect or accept commands, only commands that are common to the client and server models. The class uses an io_service to queue commands. Public methods must post to the io_service to ensure that all io_service requests occur within the correct thread.

   */
  class tcpip_session : public tcpip_handler {
  public:

    /** Constructor which initalizes the io_service objects and the default command messages. */
    tcpip_session(boost::asio::io_service& io_service_in);

    /** Destructor */
    virtual ~tcpip_session();

    /** Posts a quit function to the io_service*/
    void quit();

    /** Posts a send function to the io_service*/
    void send(std::string message);

    /** Posts a send function to the io_service which ignores the queue and sends only one message. */
    void single_send(std::string message);
    
    /** Posts a send function to the io_service which ignores the queue and 
     sends only one message.  The message is unchanged, no headers are added.
     Meant for communications with non-ROBO interfaces. */
    void simple_send(std::string message);
    
    /** Posts a receive function to the io_service */
    void listen();

    /** Determines whether the session is still connected. */
    bool is_open();

    /** Sets the timeout time for the session */
    void set_timeout(const boost::posix_time::time_duration t);

  protected:

		/** Runs the quit process */
    void do_quit();

		/** Runs implementation specific exit actions */
    virtual void do_exit();

		/** Starts a timeout  deadline timer. */
    void do_timeout(bool inbound);

		/** Ends a timeout deadline timer */
    void stop_timeout(bool inbound);

		/** Closes the socket, and reports any errors in the process */
    void do_close();

		/** A reference to the socket used for this session */
    boost::asio::ip::tcp::socket sock;

		/** Sets the current operation of the session for error reporting purposes */
    void set_current_op(int op);

		/** Gets a string detailing the current operation for error reporting. */
    std::string get_current_op();

		/** Kills the session due to an error */
    virtual void do_die(const boost::system::error_code& error);

		/** Receives messages in a loop */
    void do_recieve();

  private:

		/** Determines whether the current operation is an inbound or outbound one. */
    bool is_inbound();

		/** Sends a message from the outbox queue */
    void do_send();

		/** Sends a single message ignoring any queue */
    void do_single_send(std::string request);
    
		/** Sends a single message ignoring any queue, and only the request string */
    void do_simple_send(std::string request);
    

		/** Handles a timeout call from an expired timer or a canceled timer */
    void handle_timeout(const boost::system::error_code& error);

		/** Handles a write call and loops back to continue to empty the inbox*/
    void handle_write(const boost::system::error_code& error);

		/** Handles a read call and loops back to read another message*/
    void handle_read(const boost::system::error_code& error, size_t bytes_transferred);

		/** Handles a read header and reads the main message*/
    void handle_read_header(const boost::system::error_code& error, size_t bytes_transferred);

		/** Handles a single send call and ends*/
    void handle_end(const boost::system::error_code& error);

		/** A reference to the io_service used for this session */
    boost::asio::io_service& io_service_session;

		/** The outgoing character buffer */
    char request[MAX_LENGTH];

		/** The inbound character buffer */
    char reply_[MAX_LENGTH];

		/** The inbound character buffer */
    char header_[HEADER_LENGTH];

		/** The inbound reply as a string */
    std::string reply;

		/** An int denoting the current operation*/
    int current_operation;

		/** The length of the timeout timer */
    boost::posix_time::time_duration timeout;

		/** A timeout timer used for inbound operations */
    boost::asio::deadline_timer timer_in;

		/** A timeout timer used for outbound operations */
    boost::asio::deadline_timer timer_out;

		/** Determines whether the current inbound operation has an active or expired (but not canceled) timer */
    bool has_timeout_in;

		/** Determines whether the current outbound operation has an active or expired (but not canceled) timer */
    bool has_timeout_out;

		/** Determines whether there is an outbound operation already in progress */
    bool in_progress;

		/** Determines the type of timer expiration that occurred for reporting purposes only. */
    int timer_inbound;

		/** The length of the last inbound reply */
    size_t reply_length;

		//TODO: LOCK QUIT THREAD BEFORE SEND HAS FINISHED

  };

}
#endif /* end of include guard: TCPIP_SESSION_H_F1DB1D57 */

/**
 \file tcpip_control.h
 \brief Defines functions for the TCPIP::tcpip_control class which provides methods for controlling server or client objects.
 \date 2010-06-14

 \details

 Copyright (c) 2010 California Institute of Technology
 \author Alexander Rudy
 \note

 <b>Version History:</b>

 */
#ifndef TCPIP_CONTROL_H_5QJSK04Z
#define TCPIP_CONTROL_H_5QJSK04Z

#include <cstdlib>
#include <iostream>
#include <map>
#include <deque>

#include <boost/asio.hpp>

//REMOVED include "tcpip_strings.h"
//REMOVED include "tcpip_session.h"


namespace TCPIP {

  /** \brief Provides basic methods common to client and server objects which control sessions

   \details Provides methods for the client and server classes use in controlling a single sesion and accessing the TCPIP::tcpip_handler::inbox and TPCIP::tpcip_handler::outbox of that session. The class also provides methods to set and reset flags on the given session.

   */
  class tcpip_control : protected tcpip_strings {

  public:

    /** Constructor */
    tcpip_control();

    /** Destructor */
    virtual ~tcpip_control();

    /** Determines whether the attached session has any commands in the inbox. */
    bool has_inbound_command();

    /** Gets the top waiting command off of the inbox and removes it from the inbox.*/
    std::string get_inbound_command();

    /** Processes the top waiting command in the default way. */
    virtual void process_inbound_command(std::string command);

    /** Gets next command from the program in the default way.*/
    virtual std::string get_outbound_command();

    /** Processes the outbound command looking for control strings, if none are found, adds it to the outbox. */
    virtual void process_outbound_command(std::string command);

    /** Determines whether the control structure has any more outbound commands to process (from the default stack) */
    virtual bool has_outbound_command();

    /** Tells the attached session to quit at the next opportune time. */
    void exit();

    /** Tells the attached session to shutdown at the next opportune time. */
    void shutdown();

    /** Tells the attached session to reset all flags. */
    void reset();

    /** Tells the attached session that the current command was triggered by an inbound request (from peer) and not by this program. */
    void trigger();

    /** Sets the attached session using pointers */
    void set_session(tcpip_handler& handler);

    /** Returns a pointer to the attached session */
    tcpip_handler* get_session();

  protected:

    /** The attached session */
    tcpip_handler * session;
    
    bool session_active;

  private:

    /** The default message queue */
    tcpip_queue messages;

  };

} /*TCPIP*/

#endif /* end of include guard: TCPIP_CONTROL_H_5QJSK04Z */
/**
 \file tcpip_client.h
 \brief Declarations for Client-only classes
 \date 2010-06-14

 \details Classes used to handle client connections, which are single connections to an accepting server and read/write capability

 Copyright (c) 2010 California Institute of Technology
 \author Alexander Rudy
 \note

 <b>Version History:</b>

 */



#ifndef TCPIP_CLIENT_H
#define TCPIP_CLIENT_H

#include <cstdlib>
#include <iostream>
#include <cstring>
#include <deque>
#include <map>

#include <boost/asio.hpp>
#include <boost/bind.hpp>
#include <boost/thread.hpp>

//REMOVED include "tcpip_control.h"
//REMOVED include "tcpip_session.h"

/** \namespace TCPIP */
namespace TCPIP {

  /** \brief A session which handles connect, read, write and disconnect functionality for the client

   \details Sessions handle the connect, read, write and disconnect abilities of the client and the address resolution for the client. The client_session also handles the resolution of ip addressess. For the whole client interface, client_session holds the control flags as well as the tcpip_handle::inbox and tcpip_handle::outbox structures.

   */
	class client_session : public tcpip_session
  {
  public:

    /** Constructor which requires a reference to an io_service and the address and port of the server. */
    client_session(boost::asio::io_service& io_service_in, char* address, char* port);

  private:

    /** Method to connect to the server */
    void do_connect();

    /** Method to handle the connection */
    void handle_connect(const boost::system::error_code& error, boost::asio::ip::tcp::resolver::iterator iterator);

    /** Reference to the master io_service for the client */
    boost::asio::io_service& io_service_client;

    /** TCP/IP Lookup Query */
    boost::asio::ip::tcp::resolver::query query;

    /** TCP/IP Resolver  */
    boost::asio::ip::tcp::resolver resolver;

    /** Count of the number of connection attempts */
    int connect_count;

  };


  /** \brief A client object to open a connection to a server

   \details Connects to a server at the constructed address and over the constructed port. Class methods provide for processing inbound and outbound commands, as well as handling control commands which change the state of the client itself.

   Derived classes should overwrite the has_outbound_command() and get_outbound_command() for processing outbound commands from the client.

   Derived classes should overwrite process_inbound_command() to handle inbound commands appropriately once they arrive.

   Overwriting these functions allows the user to leave the run(), stop() and reader() functions intact in their handling of the threads.

   */
  class tcpip_client : public tcpip_control {

  public:
    /** Constructor */
    tcpip_client(char* addr, char* prt);

    /** Destructor */
    virtual ~tcpip_client();

    /** Method to start the io_service.run thread and the inbound command reader thread */
    virtual void run();

    /** Method to return the threads to the main body */
    virtual void stop();

  	/** Reconnects to the same server */
  	virtual void reconnect();

    /** Determines whether the client has a command to pass to the server */
    virtual bool has_outbound_command();

    /** Handles an inbound command and prints it to the standard output by default */
    virtual void process_inbound_command(std::string command);

    /** Gets the outbound command (by default from the user) */
    virtual std::string get_outbound_command();

    /** Processes the outbound command and adds it to the session outbox or alters the session state */
    virtual void process_outbound_command(std::string command);

  protected:

    /** Initializes the command map for outbound commands*/
    void init_map();

    /** Address of server */
    char* address;

    /** Port of server */
    char* port;

    /** Reads a message from the command line */
    std::string cin_read_message();

    /** A thread to handle reading commands from the server */
    boost::thread *readthread;

//    /** A thread to process the inbound commands */
//    boost::thread outputthread;

    /** The io_service for the client. */
    boost::asio::io_service io_service;

    /** The session used for the client connection */
    client_session c;

    /** The command map for commands input to the client from the uesr */
    std::map<std::string,int> postmap;

  };
  /** An example use of the client object from the outside:
   \example example_client.cpp
   */

}
#endif
/**
 \file tcpip_server.h
 \brief Classes to create a multiple connection server on a particular port.
 \date 2010-06-14

 \details TCPIP::tcpip_server a general server class to handle connections and commands, TCPIP::server_session , a class to handle the individual connections, and TCPIP::broadcast_room to handle the management of individual sessions and communications among sessions.

 Copyright (c) 2010 California Institute of Technology
 \author Alexander Rudy
 \note

 <b>Version History:</b>

 */


#ifndef TCPIP_SERVER_H_R9NUNDLM
#define TCPIP_SERVER_H_R9NUNDLM

#include <cstdlib>
#include <iostream>
#include <set>
#include <deque>
#include <list>
#include <algorithm>
#include <boost/bind.hpp>
#include <boost/asio.hpp>
#include <boost/shared_ptr.hpp>
#include <boost/enable_shared_from_this.hpp>
#include <boost/thread.hpp>


//REMOVED include "tcpip_globals.h"
//REMOVED include "tcpip_session.h"
//REMOVED include "tcpip_control.h"

/** \namespace TCPIP */
namespace TCPIP
{

	using boost::asio::ip::tcp;

	/**
   Type to point to individual TCPIP::tcpip_session objects
   */
  typedef boost::shared_ptr<tcpip_session> session_ptr;

	/** \brief Class to manage each individual server session, flags which apply to all sessions (shutdown) and messages passed from the server object to all sessions.

   \details Maintains a set of all open sessions, as well as the TCPIP::tcpip_handler::inbox and TCPIP::tcpip_handler::outbox structures and the general control structures (the shutdown flag) for the server. The TCPIP::tcpip_handler::inbox and TCPIP::tcpip_handler::outbox here supercede the inbox and outbox in TCPIP::server_session.

   Individual server sessions call broadcast_room::join() to add themselves to the list of managed sessions, and must call broadcast_room::leave() when they have disconnected. Server sessions which die (and so are destructed) are not required to call leave.

   */
  class broadcast_room : public tcpip_handler
  {
  public:

		/** Constructor */
    broadcast_room();

		/** Adds the session to the room's set */
    void join(session_ptr session);

		/** Sends a message to all clients */
    void send(std::string dmessage);

    /** Sends a single message (not recursive outbox) to all clients */
    void single_send(std::string dmessage);

    /** Sends a single message (not recursive outbox) to all clients */
    void simple_send(std::string dmessage);

		/** Has all clients listen for inbound messages */
    void listen();

		/** Removes the session from the room. */
    void leave(session_ptr session);

		/** Determines whether the sessions are supposed to remain open */
    bool is_open();

		/** Tells each session to post a quit process */
    void quit();

  	/** Count the number of open connections. */
  	virtual int connection_count();


  protected:

		/** The collection of open sessions to each client */
    std::set<session_ptr> sessions;

  };

  /** \brief Handles an individual connection to a client, managed by TCPIP::broadcast_room

   \details A session which handles connections to clients, and uses an inbox and outbox controlled by the TCPIP::broadcast_room as well as general switches controlled by the TCPIP::broadcast_room

   */
	class server_session
	: public tcpip_session,
	public boost::enable_shared_from_this<server_session>
  {
  public:
    friend class broadcast_room;

		/** Constructs a session attached to the given io_service and broadcast_room */
    server_session(boost::asio::io_service& io_service_in, broadcast_room& room_);

		/** Destructor */
    ~server_session();

		/** Returns a reference to the session's socket */
    tcp::socket& socket();

		/** Starts the sesion's read cycle */
    void start();

  private:

		/** Sets the initial welcome message sent to the client. */
    void setStartMessage(std::string input);

		/** Handles the implementation specific quit functions.*/
    void do_exit();

		/** The reference to the server's io_server */
    boost::asio::io_service& io_service_server;

		/** A reference to the broadcast room which is controlling the sessions */
    broadcast_room& room;

		/** The start message */
    std::string mess_start;

		/** Shared pointer which will point to this object */
    session_ptr sesptr;

  };

  /** \ A shared pointer to a server_session. */
  typedef boost::shared_ptr<server_session> server_session_ptr;


  /** \brief A server object which will accept connections from an unlimited number of clients

   \details The main server object which will create an unlimited connection server on the given port, and can then handle the inbound messages and post outbound messages.

   Derived classes should overwrite the get_outbound_command() function and the process_inbound_command() function if the sequential action of the server processing will work. If a read thread as well as a send thread are needed, then another thread must be added to run and stop, as an element of the overall object, at which point loop is not useful, but a structure like tcpip_client::reader() and \link example_client.cpp \endlink might be useful.

   */
  class tcpip_server : public tcpip_control {

  public:

    /** Constructor which requires a port to serve from */
    tcpip_server(boost::asio::io_service& io_service_in, short port);

    /** Destructor which calls stop() */
    virtual ~tcpip_server();

    /** A function which runs the io_service thread */
    virtual void run();

    /** Merges the io_service thread back onto the main thread */
    virtual void stop();

  protected:

    /** The broadcast room to maintain the servers. */
    broadcast_room room;

  private:

    /** Starts the server acceptor */
    void start_acceptor();

    /** Handles a server accept action. */
    void handle_accept(server_session_ptr new_session, const boost::system::error_code& error);

    /** Reference to the master io_server */
    boost::asio::io_service& io_service_server;

    /** The TCP client acceptor to accept connections */
    tcp::acceptor acceptor_;

    /** The thread to run the io_service */
//    boost::thread *runthread;
    boost::thread runthread;



  };
  /** An example use of the server object from the outside:
   \example example_server.cpp
   */


} /* TCPIP */

#endif /* end of include guard: TCPIP_SERVER_H_R9NUNDLM */
/**
 * @file comm.min.h
 * @brief Master Communications Header File
 * @date 2010-07-27
 *
 * @details Declares all of the classes used for communications.
 *
 * Copyright (c) 2010 California Institute of Technology
 * @author Alexander Rudy
 * @note This file combines many other header files into one convenient one.
 *
 *
 * <b>Version History:</b>
 *
 */

/**
 \file file_ops.h
 \brief Header file for file operations.
 \details File interaction operations are configured through this header file.
  File interactions should use the structures here to open and interact with files
 Copyright (c) 2009-2011 California Institute of Technology.
 \author Dr. Reed L. Riddle  riddle@caltech.edu
 \note None.

 <b>Version History</b>:
 \verbatim
 2009-07-17:  First complete version
 \endverbatim
 */

// Use a preprocessor statement to set a variable that checks if the header has
// already loaded...this avoids loading a header file more than once.
# ifndef ROBO_FILEOPS_H
# define ROBO_FILEOPS_H

// System header files
# include <sys/stat.h>
# include <fstream>
# include <sstream>
# include <boost/thread.hpp>

// Local header files
# include "basic.h"
# include "robo_time.h"


///
typedef enum {
	OPEN_FILE_READ,
	OPEN_FILE_WRITE,
	OPEN_FILE_REWRITE,
	OPEN_FILE_APPEND
} ROBO_FILE_MODE;

// Checks a directory to make sure it is valid
bool directory_check(std::string directory);

int handle_error_message(int error_code, std::string param,
                         std::string & outmsg);


/** \class ROBO_file
 \brief File handling class.
 \details Class that deals with file interactions, storing file  names, status
 information and error information.  Parent for other classes in the software
 that do file interactions. */
class ROBO_file {
private:
  /// Assignment operator
//  ROBO_file operator= (const ROBO_file & in_robo_file);

  /// Copy constructor
//  ROBO_file(const ROBO_file & in_robo_file);

    time_t file_open_time;
    

protected:

public:

    /// Definitions for file operations
    enum {
      CHECK_FILE, MAKE_FILE, REMOVE_FILE
    };

  /** \var std::string filename
   \details Name of file */
  std::string filename;

  /** \var struct stat fileinfo
   \details Structure for system file status information */
  struct stat fileinfo;

  /** \var std::fstream filestream
   \details Stream that reads the file */
  std::fstream filestream;

  /**
   Destructor for the class.  Closes the configuration file on destruction. */
  virtual ~ROBO_file(){
    this->close_file();
  };

  /// Constructor
  ROBO_file(): filename(""), fileinfo(), filestream()
  {};
  
  /// Constructor that uses a string to create the filename 
  ROBO_file(std::string filename_in): fileinfo(), filestream()
  {
    this->filename = filename_in;
    this->file_open_time = 0;
  };

  /// Assignment operator
  ROBO_file operator= (const ROBO_file & in_robo_file)
  {
    return(in_robo_file);
  }

  /// Copy constructor
  ROBO_file(const ROBO_file & in_robo_file)
  {};

  // Opens the file stream for reading
  int open_file_read(ROBO_file & robo_file);
  int open_file_read(std::string filename);

  // Opens a file stream in the mode desired
  int open_file(ROBO_FILE_MODE mode);

  // Closes a file stream
  virtual int close_file();

  // Checks if the file has been modified since opening
  bool modified();

};


/** \class ROBO_config
 \brief Configuration file handling class.
 \details Configuration file handling class.  Parameters from config files and
 functions to interface with config files are contained here.  Config files
 follow the Bash shell file format for variables. Inherits from ROBO_file. */
class ROBO_config: public ROBO_file {
private:
  /// Assignment operator
  ROBO_config operator= (const ROBO_config & in_config);

  /// Copy constructor
  ROBO_config(const ROBO_config & in_config);

public:

  /** \var int n_elements
   \details Number of elements read in config file */
  int n_elements;
  /** \var std::vector<std::string> vars
   \details Vector of config file variable names */
  std::vector<std::string> vars;
  /** \var std::vector<std::string> params
   \details Vector of config file variable paramenter values */
  std::vector<std::string> params;

  // Function to load config parameters from a file
//  int read_config(ROBO_config & config);
  int read_config();

  /**
   Constructor for the class
   \param [in_filename] Sets value of the config filename when called. */
 // Config(std::string in_filename)
  ROBO_config(std::string in_filename): n_elements(), vars(), params()
  {
    this->filename = in_filename;
  };
  
  ROBO_config(): n_elements(), vars(), params()
  {};
  
};


/** \class Config
 \brief Configuration file handling class.
 \details Configuration file handling class.  Parameters from config files and
 functions to interface with config files are contained here.  Config files
 follow the Bash shell file format for variables. Inherits from ROBO_file. */
class Config: public ROBO_file {
private:
  /// Assignment operator
  Config operator= (const Config & in_config);

  /// Copy constructor
  Config(const Config & in_config);

public:

  /** \var int n_elements
   \details Number of elements read in config file */
  int n_elements;
  /** \var std::vector<std::string> vars
   \details Vector of config file variable names */
  std::vector<std::string> vars;
  /** \var std::vector<std::string> params
   \details Vector of config file variable paramenter values */
  std::vector<std::string> params;

  // Function to load config parameters from a file
  int read_config(Config & config);

  /**
   Constructor for the class
   \param [in_filename] Sets value of the config filename when called. */
 // Config(std::string in_filename)
  Config(std::string in_filename): n_elements(), vars(), params()
  {
    this->filename = in_filename;
  };
  
  Config(): n_elements(), vars(), params()
  {};
  
};



enum {
  LOG_NO_ERROR,
  LOG_ERROR,
  LOG_WARNING,
  LOG_DEBUG,
  LOG_EMERGENCY
};


/** \class ROBO_logfile
 \brief Log file management.
 \details This class handles the log file system for ROBO.  Logging of the
 robotic operations is very important, and many items are logging information
 very fast.  This class creates a new thread for each log file entry and
 organizes the threads so that the logs are written in order.
 Inherits from ROBO_file. */
class ROBO_logfile: public ROBO_file {

private:
  /** \var boost::thread log_thread
   \details Thread used for telemetry */
  boost::thread log_thread;

  /** \var mutable boost::mutex log_file_mutex
   \details Mutex to block the variables in the thread while writing the log
   file.  */
  mutable boost::mutex log_file_mutex;

  /** \var unsigned int * actuators
   \details Array containing the driver actuator positions */
  unsigned int thread_exception;

  /** \var std::stringstream function
   \details Function where error was thrown */
  std::stringstream function;

  /** \var unsigned int thread_count
   \details Tracks the number of threads created to write to the log file, used
   to keep thread count in order.  This sets the number of threads spawned, each
   thread gets a value and this is incremented. */
  unsigned int thread_count;

  /** \var unsigned int log_count
   \details When thread_count assigns a value to a log thread, that thread
   waits until this variable equals the thread_count variable and then
   executes.  This keeps logs in order, otherwise entries are added based on
   execution speed instead of real world events. */
  unsigned int log_count;

  int lock_file(int mode);

public:

  /** \var mutable boost::mutex the_mutex
   \details Mutex to block when creating log file entries */
  mutable boost::mutex log_mutex;

  /** \var std::stringstream message
   \details Message for output to the log file */
  std::stringstream message;

  /** \var bool quiet
   \details Flag to print log messages to stdout */
	bool quiet;

  /// Constructor for the class.
	ROBO_logfile(): message(), quiet()
  {
    // Default to writing output to stdout
		this->quiet = false;
    // Initialize thread log counting variables
    this->thread_count = 0;
    this->thread_exception = 0;
    this->log_count = 0;
  };

	/// Deconstructor
  ~ROBO_logfile(){
//    std::cout << "ROBO_logfile deconstructor called" << std::endl << std::flush;
//    while (this->thread_count != this->log_count){
//      usleep(100000);
//      std::cout << " a" << this->thread_count << std::endl << std::flush;
      
//    }
//    std::cout << std::endl << std::flush;
//    this->close_file();

  };
/*  {
  	int i=0;		// Counter
  	
  	// Wait for all the log threads to finish
//  	std::cout << "file: " << this->filename << std::flush << std::endl;
//std::cout << "loga: " << this->thread_count << " " << this->log_count << std::flush << std::endl;
  	while (this->thread_count != this->log_count){
//  	  std::cout << "logw: " << this->thread_count << " " << this->log_count << std::flush << std::endl;
  		timeout(0);
  		i++;
  		if (i == 5){
  			break;
  		}
  	}
  	// Join the log thread and close the log file
    //this->log_thread.join();
    this->close_file();
    //this->filestream.close();
  };*/

  /// Copy constructor
  ROBO_logfile(const ROBO_logfile & in_logfile){};

  // Assignment constructor
  ROBO_logfile operator= (const ROBO_logfile & in_logfile)
  {
  	return (in_logfile);
  }

  //   Create a thread to write log entries to the log file
//  void write(bool err);
  void write(int err);
//  void write(std::string function, bool err, std::string message);
  void write(std::string function, int err, std::string message);

  //Write strings to a log file.
//  void write_log2(std::string message, bool error, std::string function);
  void write_log2(std::string message, int error, std::string function);
//  void write_log(std::string message, bool error, std::string function,
//                  unsigned int counter);
  void write_log(std::string message, int error, std::string function,
                 unsigned int counter);
  // Write configuration information from a configuration file to a log file.
  void write_log_config(std::vector<std::string> variables,
                        std::vector<std::string> values, std::string config_file);
  
  //Get the name of the function for the log file.
  std::string get_function();
  
  //Set the name of the function for the log file.
  void set_function(std::string name);
  
  // Closes a file stream
  int close_file();
  int close_file(std::string func);

};


# endif

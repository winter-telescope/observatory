/**
 \file time.cpp
 \brief ROBO time and coordinate operations.
 \details This file is the program file for operations within the ROBO 
 software suite that deal with time and coordinate functions.  Anything that
 deals with the management of time within the software is defined here.  Also,
 functions that work with astronomical or Earth based coordinate operations or
 transformations are set  up here.

 Copyright (c) 2009-2011 California Institute of Technology.
 \author Dr. Reed L. Riddle  riddle@caltech.edu
 \note

 <b>Version History</b>:
 \verbatim
 2011-05-13:  First complete version
 \endverbatim
 */

// System header files
# include <cmath>

// Local include files
# include "common.h"
# include "robo_time.h"


/**************** timeout ****************/
/**
  Waits until the end of a set time period and then returns on the top of the
  clock on the last second to wait.  So, ask for timeout(4) and it will wait 4
  seconds and then return at the beginning of the next full second (total wait
  is 4.something seconds).
  \param [seconds] Number of seconds to wait
  \note None.
 */
void timeout(float seconds, bool next_sec)
{
  if (seconds < 1 && seconds > 0){
    usleep(seconds * 1000000);
  }
  
  else {
    // Sleep the number of seconds called for
    if (seconds > 0){
      sleep((int)seconds);
    }

    if (next_sec == true){
      // Get the current time to the microsecond
      struct timespec data;                // Time of day container
      if(clock_gettime(CLOCK_REALTIME, &data) != 0){
        return;
      }
      
      // If the microseconds are less than 0.9999999, we sleep that long
      if (data.tv_nsec/1000000000 < 0.999999999)
        usleep((useconds_t)((999999999-data.tv_nsec)/1000));
    }
  }
}
/**************** timeout ****************/


/************ timeout *************/
/**
 This function is a generalized wait statement that produces a waiting log
 message every 5 seconds.
 \note None.
 */
//void timeout(float wait_time, ROBO_logfile & log, std::string function,
//             std::string wait_message)
void timeout(float wait_time, std::string function,
             std::string wait_message)
{
//    int wait_step;
  double start_time;
  double interval;
  double message_time;
  
  //    wait_step = 0;
  start_time = get_clock_time();
  message_time = start_time;
  interval = get_clock_time()- start_time;
  
  // Wait until the time has increased past the limit
  while (interval < wait_time){
    // Create a waiting message every five seconds
    if (message_time - get_clock_time() >= 5){
//      log.write(function, false, wait_message);
      message_time = get_clock_time();
    }
//      if (wait_step == (int) (5 / 0.0001)){
//        this->log.write(function, false, wait_message);
//        wait_step = 0;
//      }
//      wait_step++;
    timeout(0.0001);
    // Get the new interval since start
    interval = get_clock_time()- start_time;
  }
}
/************ timeout *************/


/**************** get_clock_time ****************/
/**
  Gets the current clock time, using the the REALTIME flag from the processor.
  Used mainly for telemetry, tracking the time between actions, etc.
  \note None.
 */
double get_clock_time()
{
	struct timespec data;  // Container for the current time

  if(clock_gettime(CLOCK_REALTIME, &data) != 0){ 
  	return 0;
  }

  return(data.tv_sec + (data.tv_nsec / 1000000000.0));
}
/**************** get_clock_time ****************/


/**************** get_current_time ****************/
/**
 Gets the current time from the system, and then outputs a string with a time
 stamp for that time.  The stamp format is based on the parameters passed to the
 function.
 \param [get_second_fraction] Fraction of a second level desired in the time
 stamp.
 \param [format] The format of the output string.
 \note The possible output formats are:
 \verbatim
 get_current_time(SECOND_WHOLE, TIMESTAMP)  ->  YYYY-MM-DD HH:MM:SS
 get_current_time(SECOND_WHOLE, FILENAME_HOUR)  ->  YYYYMMDDHH
 get_current_time(SECOND_WHOLE, FILENAME_SECOND)  ->  YYYYMMDD-HHMMSS
 get_current_time(SECOND_TENTH, TIMESTAMP)  ->  YYYY-MM-DD HH:MM:SS.S
 get_current_time(SECOND_HUNDREDTH, TIMESTAMP)  ->  YYYY-MM-DD HH:MM:SS.SS
 get_current_time(SECOND_MILLI, TIMESTAMP)  ->  YYYY-MM-DD HH:MM:SS.SSS
 get_current_time(SECOND_MICRO, TIMESTAMP)  ->  YYYY-MM-DD HH:MM:SS.SSSSSS
 \endverbatim
 \note The <i>format</i> parameter has no effect except when <i>get_second_fraction</i>
 parameter is SECOND_WHOLE
 */
std::string get_current_time(int format, bool adjust_date)
{
  std::stringstream current_time;   // String to contain the time
  time_t t;                         // Container for system time
  struct timespec data;             // Time of day container
  struct tm gmt;                    // GMT time container

  // Get the system time, return a bad timestamp if there is an error
  if (clock_gettime(CLOCK_REALTIME, &data) != 0){
    return("BAD TIMESTAMP");
  }

  // Convert the time of day to GMT
  t = data.tv_sec;
  if (gmtime_r(&t, &gmt) == NULL){
    return("BAD TIMESTAMP");
  }
      
  current_time.setf(std::ios_base::right);
  current_time << std::setfill('0') << std::setprecision(0);
  if (format < TIMESTAMP){
    // This is the format for FILENAME_DAY, the base for the rest of the
    // timestamps for file names
    current_time << std::setw(4) << gmt.tm_year + 1900
                 << std::setw(2) << gmt.tm_mon + 1
                 << std::setw(2) << gmt.tm_mday;

    switch (format){
      case FILENAME_HOUR:
        current_time << std::setw(2) << gmt.tm_hour;
        break;
      case FILENAME_SECOND:
        current_time << "_"
                     << std::setw(2) << gmt.tm_hour
                     << std::setw(2) << gmt.tm_min
                     << std::setw(2) << gmt.tm_sec;
        break;
      case FILENAME_MILLISECOND:
        current_time << "_"
                     << std::setw(2) << gmt.tm_hour
                     << std::setw(2) << gmt.tm_min
                     << std::setw(2) << gmt.tm_sec << "."
                     << std::setw(3) << data.tv_nsec/1000000;
        break;
      case FILENAME_MICROSECOND:
        current_time << "_"
                     << std::setw(2) << gmt.tm_hour
                     << std::setw(2) << gmt.tm_min
                     << std::setw(2) << gmt.tm_sec << "."
                     << std::setw(6) << data.tv_nsec/1000;
        break;
      case FILENAME_DAY:
        if (adjust_date == true){
          if (gmt.tm_hour >= common_info.day_switch_time){
            ROBO_time temp;
            gmt.tm_mday++;
            int leap = temp.findleap(gmt.tm_year + 1900);
            if (gmt.tm_mday > temp.days_of_year[leap][gmt.tm_mon + 1]){
              gmt.tm_mday = 1;
              gmt.tm_mon++;
              if(gmt.tm_mon == 12){
                gmt.tm_mon = 0;
                gmt.tm_year++;
              }
            }
            current_time.str("");
            current_time << std::setw(4) << gmt.tm_year + 1900
                         << std::setw(2) << gmt.tm_mon + 1
                         << std::setw(2) << gmt.tm_mday;
          }
        }
        break;
      default:
        ;
    }
  }

  else if (format >= TIMESTAMP){
    current_time << std::setw(4) << gmt.tm_year + 1900   << "-"
                 << std::setw(2) << gmt.tm_mon + 1 << "-"
                 << std::setw(2) << gmt.tm_mday    << " "
                 << std::setw(2) << gmt.tm_hour  << ":"
                 << std::setw(2) << gmt.tm_min << ":"
                 << std::setw(2) << gmt.tm_sec;
    switch (format){
      case SECOND_TENTH:
        current_time << "." << std::setw(1) << data.tv_nsec/100000000;
        break;
      case SECOND_HUNDREDTH:
        current_time << "." << std::setw(2) << data.tv_nsec/10000000;
        break;
      case SECOND_MILLI:
        current_time << "." << std::setw(3) << data.tv_nsec/1000000;
        break;
      case SECOND_MICRO:
        current_time << "." << std::setw(6) << data.tv_nsec/1000;
        break;
      case TIMESTAMP:
      // Fall through
      case SECOND_WHOLE:
      // Fall through
      default:
        ;
    }
  }

  else {
    current_time << std::setw(4) << gmt.tm_year + 1900   << "-"
                 << std::setw(2) << gmt.tm_mon + 1 << "-"
                 << std::setw(2) << gmt.tm_mday    << " "
                 << std::setw(2) << gmt.tm_hour  << ":"
                 << std::setw(2) << gmt.tm_min << ":"
                 << std::setw(2) << gmt.tm_sec;
  }

  return(current_time.str());
}
/**************** get_current_time ****************/


/**************** get_current_time ****************/
/**
 Get the current UNIX clock time, which is seconds since January 1, 1970.  Use
 this mainly for timing of loops where something is supposed to happen each
 second.
 \param [get_gmt] Tell the function to return the UNIX time in GMT
 \return The current UNIX time is returned, either as the clock time or GMT
 */
time_t get_current_time(bool get_gmt)
{
  time_t t;                        // Container for system time

  // Allocate the time container and get the system time
  t = time(NULL);
  
  // UNIX time should never be <= 0
  if (t <= 0){
    return(0);
  }

  // Convert to GMT if requested
  if (get_gmt == true){
    struct tm gmt;                   // GMT time container

    // Convert the time of day to GMT
    if (gmtime_r(&t, &gmt) == NULL){
      return(0);
    }

    // Set the UNIX time to GMT
    t = timegm(&gmt);
  }
  
  // Return the output UNIX time value
  return(t);
}
/**************** get_current_time ****************/


/**************** get_current_time_double ****************/
/**
 Get the current UNIX clock time to nanosecond resolution.  Used for timings
 and tracking times where better than one second resultion is required.
 */
double get_current_time_double()
{
  struct timespec data;            // Time of day container
  double outtime;                  // The output time
  
  // Get the time of day to the nanosecond
  if(clock_gettime(CLOCK_REALTIME, &data) != 0){
    return -1;
  }
  
  // Set the value
  outtime = (double) data.tv_sec + (double) data.tv_nsec / 1000000000;

  return(outtime);
}
/**************** get_current_time_double ****************/


/**************** get_fits_time ****************/
/**
 Gets the current time from the system, and then outputs a string with a time
 stamp for that time.  The stamp format is formatted in the FITS standard:
 2016-01-01T23:45:56.123
 */
std::string get_fits_time()
{
  std::stringstream current_time;  // String to contain the time
  time_t t;                        // Container for system time
  struct timespec data;            // Time of day container
  struct tm gmt;                   // GMT time container
  
  // Get the system time, return a bad timestamp on error
  if(clock_gettime(CLOCK_REALTIME, &data) != 0){
    return("9999-99-99T99:99:99.999");
  }
  
  // Convert the time of day to GMT
  t = data.tv_sec;
  if (gmtime_r(&t, &gmt) == NULL){
    return("9999-99-99T99:99:99.999");
  }
  
  current_time.setf(std::ios_base::right);
  current_time << std::setfill('0') << std::setprecision(0)
  << std::setw(4) << gmt.tm_year + 1900   << "-"
  << std::setw(2) << gmt.tm_mon + 1 << "-"
  << std::setw(2) << gmt.tm_mday    << "T"
  << std::setw(2) << gmt.tm_hour  << ":"
  << std::setw(2) << gmt.tm_min << ":"
  << std::setw(2) << gmt.tm_sec
  << "." << std::setw(3) << data.tv_nsec/1000000;
  
  return(current_time.str());
}
/**************** get_fits_time ****************/



/**************** write_timestamp ****************/
/**
 Reformats a timestamp of the form YYYYMMDD_HHMMSS.SSS to
 YYYY-MM-DD HH:MM:SS.SSS
 \param [timestamp] The time stamp to write
 \note The "_ "in the input format can be any character, and there can be any
 number of decimal places to the seconds.
 */
std::string write_timestamp(std::string timestamp)
{
  std::stringstream message;  // A stream for messages to be logged

  message << timestamp.substr(0,4)  << "-" << timestamp.substr(4,2) << "-"
          << timestamp.substr(6,2)  << " " << timestamp.substr(9,2) << ":"
          << timestamp.substr(11,2) << ":" << timestamp.substr(13,timestamp.size()) << "\t";
  return(message.str());
}
/**************** write_timestamp ****************/


/**************** print_ut_timestamp ****************/
/**
 Reformats a UNIX timestamp to YYYY-MM-DD HH:MM:SS.  Times must be in UT.
 \param [gmt_time_in] The UT time to write
 \note None.
 */
std::string print_ut_timestamp(time_t gmt_time_in)
{
  struct tm gmt;                   // GMT time container

  if (gmtime_r(&gmt_time_in, &gmt) == NULL){
    return("BAD TIMESTAMP");
  }

  std::stringstream out;

  out << std::setfill('0') 
      << std::setw(4) << gmt.tm_year + 1900 << "-"
      << std::setw(2) << gmt.tm_mon + 1 << "-"
      << std::setw(2) << gmt.tm_mday << " "
      << std::setw(2) << gmt.tm_hour << ":"
      << std::setw(2) << gmt.tm_min << ":"
      << std::setw(2) << gmt.tm_sec;

  return(out.str());
}
/**************** print_ut_timestamp ****************/



/***** ROBO_time class routines *****/

/**************** ROBO_time::initialize_class ****************/
/**
 Initializes the Camera class container, called in the constructors for the class.
 */
void ROBO_time::initialize_class()
{
  /** Variable to track days of the year and leap year information */
  int yd[2][13] =
  { {365, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31},
    {366, 31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31} };
  
  // Set up the days_of_year variable.  We have to do this this way to
  // include this in the class, otherwise it has to be a global.
  for (int i = 0; i < 13; i++){
    for (int j = 0; j < 2; j++){
      this->days_of_year[j][i] = yd[j][i];
    }
  }
  
  // Allocate the time container
  time_t tt;
  tt = time(NULL);
  this->t.tm_isdst = -1;

  // Give the rest of the parameters an initial value
  this->is_gmt = false;
  this->unix_time = 0;
  this->leap_year = 0;
  this->second_fraction = 0;
  this->year_time = 0;
}
/**************** ROBO_time::initialize_class ****************/


/**************** ROBO_time::findleap ****************/
/**
 Calculates if an input year is a leap year.
 \param [year] Year to calculate if it is a leap year.
 \note None.
 \return 0 for a normal year, 1 for a leap year.
 */
int ROBO_time::findleap(int year)
{
  // Return 1 if the year is divisible by 4 or if the year is divisible
  // by 400.  Return 0 if the year is divisible by 100.  Otherwise, return
  // 0.  A return of 0 is a normal year, 1 is a leap year.
  return((year%4 == 0) && ((year%100 != 0) || (year%400 == 0)));
}
/**************** ROBO_time::findleap ****************/


/**************** ROBO_time::set_time_y_yd_h_m_s ****************/
/**
 Reads in a string of the format "Y-YD H:M:S" and translates it into time
 parameters for the class.
 \param [time] The input time string.
 \note The format has to match or else this will fail.
 \return NO_ERROR for no errors, ERROR if there is an error
 */
int ROBO_time::set_time_y_yd_h_m_s(std::string & time)
{
  // Break the string into tokens
  std::vector<std::string> tokens;  // Temporary tokens
  int err = Tokenize(time, tokens, " -:");
  // Return an error if there are not 5 tokens
  if (err != 5){
    return(ERROR);
  }
  
  // Convert each token into a time value
  this->t.tm_year = atoi(tokens[0].c_str()) - 1900;
  this->t.tm_yday = atoi(tokens[1].c_str());
  this->t.tm_hour = atoi(tokens[2].c_str());
  this->t.tm_min = atoi(tokens[3].c_str());
  this->t.tm_sec = atoi(tokens[4].c_str());
  this->second_fraction = atof(tokens[4].c_str()) - this->t.tm_sec;
  
  // Find if this is a leap year
  this->leap_year = this->findleap(this->t.tm_year);
  
  // Find the day of the month by subtracting all of the days of previous
  // months, and then set the month day and the month
  int yearday = this->t.tm_yday;
  int i;
  for (i = 1; yearday > days_of_year[this->leap_year][i]; i++){
    yearday -= days_of_year[this->leap_year][i];
  }
  this->t.tm_mday = yearday;
  this->t.tm_mon = i - 1;

  // Return no errors
  return(NO_ERROR);
}
/**************** ROBO_time::set_time_y_yd_h_m_s ****************/


/**************** ROBO_time::set_time_y_m_d_h_m_s ****************/
/**
 Reads in a string of the format "Y-M-D H:M:S" and translates it into time
 parameters for the class.
 \param [time] The input time string.
 \note The format has to match or else this will fail.
 \return NO_ERROR for no errors, ERROR if there is an error
 */
int ROBO_time::set_time_y_m_d_h_m_s(std::string & time)
{
  // Break the string into tokens
  std::vector<std::string> tokens;  // Temporary tokens
  int err = Tokenize(time, tokens, " -:");
  // Return an error if there are not 6 tokens
  if (err != 6){
    return(ERROR);
  }
  
  // Convert each token into a time value
  this->t.tm_year = atoi(tokens[0].c_str()) - 1900;
  this->t.tm_mon = atoi(tokens[1].c_str()) - 1;
  this->t.tm_mday = atoi(tokens[2].c_str());
  this->t.tm_hour = atoi(tokens[3].c_str());
  this->t.tm_min = atoi(tokens[4].c_str());
  this->t.tm_sec = atoi(tokens[5].c_str());
  this->second_fraction = atof(tokens[5].c_str()) - this->t.tm_sec;
  
  // Find if this is a leap year
  this->leap_year = this->findleap(this->t.tm_year);
  
  // Find the year day by adding all of the days of previous months
  int yearday = 0;
  int i;
  for (i = 1; i <= this->t.tm_mon; i++){
    yearday += days_of_year[this->leap_year][i];
  }
  this->t.tm_yday = yearday;
  
  // Return no errors
  return(NO_ERROR);
}
/**************** ROBO_time::set_time_y_m_d_h_m_s ****************/


/**************** ROBO_time::set_time_y ****************/
/**
 Reads in a string of the format "Y.YYY" and translates it into time
 parameters for the class.
 \param [time] The input time string.
 \note The format has to match or else this will fail.
 \return NO_ERROR for no errors, ERROR if there is an error
 */
int ROBO_time::set_time_y(std::string & time)
{
  // Break the string into tokens
  std::vector<std::string> tokens;  // Temporary tokens
  int err = Tokenize(time, tokens, " -:");
  // Return an error if there are more than 1 tokens
  if (err != 1){
    return(ERROR);
  }
  
  // Convert each token into a time value
  double year = atof(tokens[0].c_str());
  int int_year = (int) year;
  this->t.tm_year = int_year - 1900;

  // Find if this is a leap year
  this->leap_year = this->findleap(this->t.tm_year);
  
  double yday = (year - int_year) * days_of_year[this->leap_year][0];
  this->t.tm_yday = (int) yday;
  
  double hour = (yday - this->t.tm_yday) * 24;
  this->t.tm_hour = (int) hour;
  
  double min = (hour - this->t.tm_hour) * 60;
  this->t.tm_min = (int) min;
  
  double sec = (min - this->t.tm_min) * 60;
  this->t.tm_sec = (int) sec;
  this->second_fraction = sec - this->t.tm_sec;
  
  // Find the day of the month by subtracting all of the days of previous
  // months, and then set the month day and the month
  int yearday = this->t.tm_yday;
  int i;
  for (i = 1; yearday > days_of_year[this->leap_year][i]; i++){
    yearday -= days_of_year[this->leap_year][i];
  }
  this->t.tm_mday = yearday;
  this->t.tm_mon = i - 1;

  // Return no errors
  return(NO_ERROR);
}
/**************** ROBO_time::set_time_y_yd_h_m_s ****************/


/**************** ROBO_time::set_time_unix ****************/
/**
 Reads in a string of a UNIX time format and translates it into time
 parameters for the class.
 \param [time] The input time string.
 \note The format has to match or else this will fail.
 \return NO_ERROR for no errors, ERROR if there is an error
 */
int ROBO_time::set_time_unix(std::string & time)
{
  // Convert the string into numbers that can be used 
  std::vector<std::string> tokens;  // Temporary tokens
  int err = Tokenize(time, tokens, ".");
  // Return an error if there are more than 1 tokens
  if (err != 2){
    return(ERROR);
  }
  
  // Make the UNIX time into a tm structure in GMT
  time_t unix_time;
  unix_time = atoi(tokens[0].c_str());
  struct tm gmt;                   // GMT time container
//  if (localtime_r(&unix_time, &gmt) == NULL){
  if (gmtime_r(&unix_time, &gmt) == NULL){
    return(ERROR);
  }
  
  // Make the fraction
  std::string fractime = "0." + tokens[1];
  this->second_fraction = atof(fractime.c_str());

  // Move the parameters over to the ROBO_time data
  this->unix_time = unix_time;
  this->t.tm_year = gmt.tm_year;
  this->t.tm_mon = gmt.tm_mon;
  this->t.tm_mday = gmt.tm_mday;
  this->t.tm_hour = gmt.tm_hour;
  this->t.tm_min = gmt.tm_min;
  this->t.tm_sec = gmt.tm_sec;

  // Find if this is a leap year
  this->leap_year = this->findleap(this->t.tm_year);
  
  // Find the year day by adding all of the days of previous months
  int yearday = 0;
  int i;
  for (i = 1; i <= this->t.tm_mon; i++){
    yearday += days_of_year[this->leap_year][i];
  }
  this->t.tm_yday = yearday;

  // Return no errors
  return(NO_ERROR);
}
/**************** ROBO_time::set_time_unix ****************/


/**************** ROBO_time::set_time ****************/
/**
 Read in a string and convert it into the values used by the ROBO time
 class.
 \param [time] The input time string.
 \param [format] The format of the input string.
 \note The format must match the string or else this will fail.
 \return NO_ERROR for no errors, ERROR if there is an error
 */
int ROBO_time::set_time(std::string & time, Time_string_format format,
                          bool gmt)
{
  int err = NO_ERROR;       // Error flag
  
  if (gmt == true){
    this->is_gmt = true;
  }
  else {
    this->is_gmt = false;
  }
  
  // Set the time based on the input string format
  switch (format){
    // Format:  YYYY-YEARDAY HH:MM:SS
    case TIMEFMT_Y_YD_H_M_S:
      err = this->set_time_y_yd_h_m_s(time);
      break;
    
      // Format:  Y-M-D H:M:S
    case TIMEFMT_Y_M_D_H_M_S:
      err = this->set_time_y_m_d_h_m_s(time);
      break;
      
    // Format:  YYYY
    case TIMEFMT_YEAR:
      err = this->set_time_y(time);
      break;
      
      // Format:  UNIX time, with a possible fractional second
    case TIMEFMT_UNIX:
      err = this->set_time_unix(time);
      break;
      
    // Any unknown format throws an error
    default:
      err = ERROR;
  }
  
  // Return on any errors
  if (err != NO_ERROR){
    return(ERROR);
  }
  
  // Calculate the decimal year for the start date, plus the number of seconds
  // since that time 
  this->year_time = this->t.tm_year +
                      (this->t.tm_yday +
                        (this->t.tm_hour +
                          (this->t.tm_min + 
                            (this->t.tm_sec + this->second_fraction) / 60)
                          / 60)
                        / 24)
                      / days_of_year[this->leap_year][0];

  // Set the UNIX time for the input time
  if (this->is_gmt == true){
    this->unix_time = timegm(&this->t);
  }
  else {
    this->unix_time = mktime(&this->t);
  }
  
  // Return no errors
  return(NO_ERROR);
}
/**************** ROBO_time::set_time ****************/


/**************** ROBO_time::get_time ****************/
/**
 Get the time out of the class values in string format.
 \param [format] The format of the output string.
 \note None.
 \return 
 */
std::string ROBO_time::get_time(Time_string_format format, bool tz_flag)
{
  std::stringstream out_time;   // Output string 
  
  // Switch off the formats for strings
  switch (format){
    // Format:  YYYY-YEARDAY HH:MM:SS
    case TIMEFMT_Y_YD_H_M_S:
      out_time << std::setfill('0') << std::setprecision(0)
        << std::setw(4) << this->t.tm_year + 1900 << "-" 
        << std::setw(3) << this->t.tm_yday << " " 
        << std::setw(2) << this->t.tm_hour << ":" 
        << std::setw(2) << this->t.tm_min << ":" 
        << std::setw(2) << this->t.tm_sec << "."
        << std::setw(3) << (int) (this->second_fraction * 1000);
      break;
    case TIMEFMT_Y_M_D_H_M_S:
      out_time << std::setfill('0') 
        << std::setw(4) << this->t.tm_year + 1900 << "-" 
        << std::setw(2) << this->t.tm_mon + 1 << "-" 
        << std::setw(2) << this->t.tm_mday << " " 
        << std::setw(2) << this->t.tm_hour << ":" 
        << std::setw(2) << this->t.tm_min << ":" 
        << std::setw(2) << this->t.tm_sec << "."
        << std::setw(3) << (int) (this->second_fraction * 1000);
      break;
    case TIMEFMT_GPS:
      out_time << std::setfill('0')
      << std::setw(4) << this->t.tm_year + 1900 << "-"
      << std::setw(2) << this->t.tm_mon + 1 << "-"
      << std::setw(2) << this->t.tm_mday << " "
      << std::setw(2) << this->t.tm_hour << ":"
      << std::setw(2) << this->t.tm_min << ":"
      << std::setw(2) << this->t.tm_sec << "."
      << std::setw(9) << (int) (this->second_fraction * 1000000000);
      break;
    case TIMEFMT_FITS:
      out_time << std::setfill('0')
      << std::setw(4) << this->t.tm_year + 1900 << "-"
      << std::setw(2) << this->t.tm_mon + 1 << "-"
      << std::setw(2) << this->t.tm_mday << "T"
      << std::setw(2) << this->t.tm_hour << ":"
      << std::setw(2) << this->t.tm_min << ":"
      << std::setw(2) << this->t.tm_sec << "."
      << std::setw(3) << (int) (this->second_fraction * 1000);
      break;
    case TIMEFMT_FITS_GPS:
      out_time << std::setfill('0')
      << std::setw(4) << this->t.tm_year + 1900 << "-"
      << std::setw(2) << this->t.tm_mon + 1 << "-"
      << std::setw(2) << this->t.tm_mday << "T"
      << std::setw(2) << this->t.tm_hour << ":"
      << std::setw(2) << this->t.tm_min << ":"
      << std::setw(2) << this->t.tm_sec << "."
      << std::setw(9) << (int) (this->second_fraction * 1000000000);
      break;
    case TIMEFMT_UNIX:
      out_time << this->get_unix_time() << "." 
               << std::setw(9) << (int) (this->second_fraction * 1000000000);
      break;
    case TIMEFMT_ZTF_FILENAME:
    {
      float frac_day;
      frac_day = this->t.tm_hour + this->t.tm_min/60 + this->t.tm_sec/3600;
      frac_day = (frac_day / 24) * 1000000;
      
      out_time << std::setfill('0')
      << std::setw(4) << this->t.tm_year + 1900
      << std::setw(2) << this->t.tm_mon + 1
      << std::setw(2) << this->t.tm_mday
      << std::setw(6) << std::setprecision(0) << frac_day;
      break;
    }
    case TIMEFMT_YEAR:
    {
    	double frac_year;
    	frac_year = this->t.tm_yday + (this->t.tm_hour + this->t.tm_min/60 + this->t.tm_sec/3600) / 24;
    	frac_year = frac_year / days_of_year[this->leap_year][0];
    	double year = this->t.tm_year + 1900 + frac_year;
    			
      out_time << std::setprecision(10)  << std::fixed << year;
      break;
    }
  }

  // Add the time zone flag
  if (tz_flag == true){
    // If this is a GMT/UTC time, add UTC for the time (we are doing astronomy
    // after all!)
    if (this->is_gmt == true){
      out_time << " UTC";
    }
    // Otherwise, add the struct time zone.  Make sure to set it first...
    else {
      out_time << " " << this->t.tm_zone;
    }
  }
  
  // Return the constructed string
  return(out_time.str());
}
/**************** ROBO_time::get_time ****************/


/**************** ROBO_time::get_unix_time ****************/
/**
 Return the UNIX time from the class.
 \note None.
 \return The UNIX time from the class values, seconds since 1970
 */
time_t ROBO_time::get_unix_time()
{
  return(this->unix_time);
}
/**************** ROBO_time::get_unix_time ****************/


/**************** ROBO_time::set_gmt_flag ****************/
/**
 Set the flag to true if the class contains GMT (UTC) time values.
 \param [flag] The GMT/UTC flag, true if GMT false if not.
 \note None.
 */
void ROBO_time::set_gmt_flag(bool flag)
{
  this->is_gmt = flag;
}
/**************** ROBO_time::set_gmt_flag ****************/




/***** Sexagesimal class routines *****/

/**************** Sexagesimal::get ****************/
/**
 Get the numerical value of the sexagesimal variable.
 \note None.
 */
float Sexagesimal::get_value()
{
  return(this->value);
}
/**************** Sexagesimal::get ****************/


/**************** Sexagesimal::get ****************/
/**
 Get the numerical value of the sexagesimal variable.  This version outputs
 the degree value of the angle, which only matters for time angles.
 \note None.
 */
float Sexagesimal::get_degree_value()
{
  return(this->degree_value);
}
/**************** Sexagesimal::get ****************/


/**************** Sexagesimal::get ****************/
/**
 Get the output string of the variable.  Use this for any output strings that
 may be read by software, as the HH:MM:SS.SSS format is easier to handle in
 software than something with special characters.
 \note The output format depends on the type that is defined when the class is 
 created.
 */
std::string Sexagesimal::get()
{
  std::stringstream output;   // Temporary output string

  if (this->sign == 1){
    output << "+";
  }
  else {
    output << "-";
  }
  output << std::setfill('0') << std::setw(2) << this->angle << ":" 
         << std::setfill('0') << std::setw(2) << this->minute << ":" 
         << std::setfill('0') << std::setw(2) << this->second;
  return(output.str());
}

/**************** Sexagesimal::get ****************/
/**
 Get the output string of the variable.  Outputs with the more elaborate format
 instead of a basic formatting.  Use this to print out displays or other places
 that people might read, stick with the standard get() above when outputting
 strings to be used in software or reading input values. 
 \note The output format depends on the type that is defined when the class is 
 created.
 */
std::string Sexagesimal::get_fancy()
{
  std::stringstream output;   // Temporary output string
  std::string sign_string;
  
  if (this->sign == 1){
    sign_string = "+";
  }
  else {
    sign_string = "-";
  }

  // Switch on the type
  switch (this->type){
    // Format:  -DDDdMM'SS.SSS"    Sign only shows for negative values
    case DEGREE_ANGLE:
      output << sign_string
             << std::setfill('0') << std::setw(2) << this->angle << "d" 
             << std::setfill('0') << std::setw(2) << this->minute << "\'" 
             << std::setfill('0') << std::setw(2) << this->second << "\"";
      break;
    // Format:  -HHhMMmSS.SSSs    Sign only shows for negative values
    case RA_ANGLE:
      output << sign_string
             << std::setfill('0') << std::setw(2) << this->angle << "h" 
             << std::setfill('0') << std::setw(2) << this->minute << "m" 
             << std::setfill('0') << std::setw(2) << this->second << "s";
      break;
    // Format:  -HHhMMmSS.SSSs    Sign only shows for negative values
    case HOUR_ANGLE:
      output << sign_string
             << std::setfill('0') << std::setw(2) << this->angle << "h" 
             << std::setfill('0') << std::setw(2) << this->minute << "m" 
             << std::setfill('0') << std::setw(2) << this->second << "s";
      break;
    // Format:  -DDDdMMmSS.SSSs    Sign shows for all values
    case DEC_ANGLE:
      output << sign_string
             << std::setfill('0') << std::setw(2) << this->angle << "d" 
             << std::setfill('0') << std::setw(2) << this->minute << "m" 
             << std::setfill('0') << std::setw(2) << this->second << "s";
      break;
    // Format:  -DDDdMMmSS.SSSs    Sign shows for all values
    case LONGITUDE_ANGLE:
      output << sign_string
             << std::setfill('0') << std::setw(2) << this->angle << "d" 
             << std::setfill('0') << std::setw(2) << this->minute << "m" 
             << std::setfill('0') << std::setw(2) << this->second << "s";
      break;
    // Format:  HH:MM:SS.SSS    No sign
    case TIME_FORMAT:
      output << std::setfill('0') << std::setw(2) << this->angle << ":" 
             << std::setfill('0') << std::setw(2) << this->minute << ":" 
             << std::setfill('0') << std::setw(2) << this->second;
      break;
    default:
      ;
  }
  
  return(output.str());
}
/**************** Sexagesimal::get ****************/



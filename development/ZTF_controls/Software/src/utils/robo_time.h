/**
 \file time.h
 \brief Header file for all ROBO time and coordinate operations.
 \details This file is the header file for operations within the ROBO 
 software suite that deal with time and coordinate functions.  Anything that
 deals with the management of time within the software is defined here.  Also,
 functions that work with astronomical or Earth based coordinate operations or
 transformations are set up here.

 Copyright (c) 2009-2011 California Institute of Technology.
 \author Dr. Reed L. Riddle  riddle@caltech.edu
 \note

 <b>Version History</b>:
 \verbatim
 \endverbatim
 */

// Use a preprocessor statement to set a variable that checks if the header has
// already loaded...this avoids loading the header file more than once.
# ifndef ROBO_TIME_H
# define ROBO_TIME_H

// System header files
# include <iomanip>
# include <sstream>
# include <ctime>
# include <sys/time.h>
# include <cstdlib>

// Local include files
//# include "communications.h"
# include "basic.h"
//# include "file_ops.h"

/** \var const double RAD2DEG
 \details Convert raidans to degrees */
const double RAD2DEG = 57.2957795130823;
/** \var const double PI
 \details The number pi...you know, that one... */
const double PI = 3.14159265358979;
/** \var const double TWOPI
 \details Twice the pi, oh so filling! */
const double TWOPI = 6.28318530717959;
/** \var const double PI_OVER_2
 \details Half of pi, because you're willing to share */
const double PI_OVER_2 = 1.57079632679490;
/** \var const double ARCSEC_IN_RADIAN
 \details Number of arcseconds in a radian */
const double ARCSEC_IN_RADIAN = 206264.8062471;
const int J2000 = 2451545;
const float SEC_IN_DAY = 86400.0;
const double HRS_IN_RADIAN = 3.819718634;
const double DEG_IN_RADIAN = RAD2DEG;

/** \var const float TIME_ANGLE_MIN
 \details Number of arcseconds in a radian */
const float TIME_ANGLE_MIN = 0.;
/** \var const float TIME_ANGLE_MAX
 \details Number of arcseconds in a radian */
const float TIME_ANGLE_MAX = 24.;
/** \var const float LONGITUDE_ANGLE_MIN
 \details Number of arcseconds in a radian */
const float LONGITUDE_ANGLE_MIN = 0.;
/** \var const float LONGITUDE_ANGLE_MAX
 \details Number of arcseconds in a radian */
const float LONGITUDE_ANGLE_MAX = 360.;
/** \var const float LATITUDE_ANGLE_MIN
 \details Number of arcseconds in a radian */
const float LATITUDE_ANGLE_MIN = 0.;
/** \var const float LATITUDE_ANGLE_MAX
 \details Number of arcseconds in a radian */
const float LATITUDE_ANGLE_MAX = 90.;
/** \var const float EPOCH_MIN
 \details Number of arcseconds in a radian */
const float EPOCH_MIN = 1800.;
/** \var const float EPOCH_MAX
 \details Number of arcseconds in a radian */
const float EPOCH_MAX = 2100.;

// Wait for the next second in a process, good to timeout something
//void timeout()
void timeout(float seconds = 0, bool next_sec = true);
void timeout(float wait_time, std::string function,
             std::string wait_message);

// Get time stamps
//std::string get_current_time(int format);
std::string get_current_time(int format, bool adjust_date=false);
time_t get_current_time(bool get_gmt = false);
double get_current_time_double();
std::string get_fits_time();
double get_clock_time();

// Write time stamps
std::string write_timestamp(std::string timestamp);

// Write UT as a nicely formatted string
std::string print_ut_timestamp(time_t gmt_time_in);


/** \class ROBO_time
 \brief Class to carry around time.  This is a convenient class that holds the
 time, both as a UNIX time and as a clock representation.  Use this to take 
 some time being used by the system and get both the time representation and
 a nice output string.
 \details  */
class ROBO_time {
  private:
  
  void initialize_class();

  public:

/** \var tm *t
 \details A standard C library time structure:
    struct tm
    { int tm_sec;      // 0 to 59 (or 60 for occasional rare leap-seconds)
      int tm_min;      // 0 to 59
      int tm_hour;     // 0 to 23
      int tm_mday;     // 1 to 31
      int tm_mon;      // 0 to 11, stupidly 0=January, 11=December
      int tm_year;     // year-1900, so 79 means 1979, 103 means 2003
      int tm_wday;     // 0 to 6, 0=Sunday, 1=Monday, ..., 6=Saturday
      int tm_yday;     // 0 to 365, 0=1st January
      int tm_isdst;    // 0 to 1, 1=DST is in effect, 0=it isn't
      char *tm_zone;   // time zone, e.g. "PDT", "EST".
      int tm_gmtoff; } // time zone in seconds from GMT; EST=-18000, WET=3600*/
    tm t;

    /** \var bool is_gmt
     \details Flag if the time is in GMT */
    bool is_gmt;

    /** \var time_t unix_time
     \details UNIX time value, i.e. the number of seconds since Jan 1, 1970 */
    time_t unix_time;

    /** \var int leap_year
     \details 0 if this is not a leap year, 1  if it is */
    int leap_year;

    /** \var float second_fraction
     \details Fraction of a second in the time (UNIX time doesn't do 
     fractions so we save it just in case) */
    double second_fraction;

    /** \var double year_time
     \details The fractional year (YYY.YYYYYY) for this time */
    double year_time;

    /** \var int days_of_year[2][13]
     \details Number of days in each month for a regular and leap year.  This
     is set up in the constructor */
    int days_of_year[2][13];
    
    // Determine if the input year is a leap year
    int findleap(int year);
    
    // Set the class time from input string, format YYYY-YEARDAY HH:MM:SS
    int set_time_y_yd_h_m_s(std::string & time);
    int set_time_y(std::string & time);
    int set_time_y_m_d_h_m_s(std::string & time);
    int set_time_unix(std::string & time);

    
    /** typedef enum Time_string_format.
      * Definition of Time_string_format, which defines the format flags for
      * time string formatting. */
    typedef enum {
      TIMEFMT_YEAR,         /**< 0, format YYYY.YYYYYY */  
      TIMEFMT_Y_M,          /**< 1, format YYYY-MM */
      TIMEFMT_Y_M_D,        /**< 2, format YYYY-MM-DD */
      TIMEFMT_Y_M_D_H,      /**< 3, format YYYY-MM-DD HH */
      TIMEFMT_Y_M_D_H_M,    /**< 4, format YYYYMM-DD HH:MM */
      TIMEFMT_Y_M_D_H_M_S,  /**< 5, format YYYY-MM-DD HH:MM:SS.SSS */
      TIMEFMT_Y_YD_H_M_S,   /**< 6, format YYYY-YEARDAY HH:MM:SS.SSS */
      TIMEFMT_H_M_S,        /**< 7, format HH:MM:SS.SSS */
      TIMEFMT_UNIX,         /**< 8, format is UNIX ime, seconds since 1970 */
      TIMEFMT_FITS,         /**< 9, format is YYYY-MM-SSTHH:MM:SS.SSS */
      TIMEFMT_GPS,          /**< 10, format is YYYY-MM-SSTHH:MM:SS.SSSSSSSSS */
      TIMEFMT_FITS_GPS,     /**< 9, format is YYYY-MM-SSTHH:MM:SS.SSSSSSSSS */
      TIMEFMT_ZTF_FILENAME  /**< 11, format is YYYYMMDD[fractional day] */
    } Time_string_format;
    
    
    /// Constructor for the class
    ROBO_time()
    {
      // Initialize the class variables
      this->initialize_class();
    }
    
    /// Deconstructor for the class
    ~ROBO_time()
    {
      // Deallocate the time structure
    }
   
    // Set the class time variables from an input string
    int set_time(std::string & time, Time_string_format format, bool gmt = false);
    
    // Get the time out as a formatted string.  Time zone is defaulted to GTM
    std::string get_time(Time_string_format format, bool tz_flag = false);
    
    // Get the UNIX time
    time_t get_unix_time();
    
    // Set the GMT flag
    void set_gmt_flag(bool flag);

};




/** \class Sexagesimal
 \brief Sexagesimal variable class.
 \details This class handles variables that can be expressed in a sexagesimal
 representation.  Astronomical coordinates, latitude, longitude, and similar
 coordinates use this representation.  Times can also be done this way, but
 usually it's better to use ROBO_time variables to handle time */
class Sexagesimal {
  private:
    
    /** \var int type
     \details The type of Coord_angle for the variable */
    int type;
    
    /** \var int angle
     \details The angle for this variable (i.e. hour, degree) */
    int angle;

    /** \var int minute
     \details The minute of the angle */
    int minute;
    
    /** \var float second
     \details The second of the angle */
    float second;
    
    /** \var int sign
     \details The sign of the variable, either 1 or -1 */
    int sign;
    
    /** \var float value
     \details The floating point representation of the sexagesimal number */
    float value;
    
    /** \var float degree_value
     \details The degree value; for hour/time angles, multiply by 15 to get this */
    float degree_value;
    
    /** \var std::string value_string
     \details  */
//    std::string value_string;

  public:
    
    /** typedef enum Coord_angle.
      * Definition of Time_string_format, which defines the format flags for
      * time string formatting. */
   typedef enum {
      DEGREE_ANGLE,         /**< format YYYY.YYYYYY */  
      RA_ANGLE,
      HOUR_ANGLE,
      DEC_ANGLE,
      LONGITUDE_ANGLE,
      TIME_FORMAT
    } Coord_angle;
    
    
    /** Constructor for the class
        \param [type_in] The type of sexagesimal, from Coord_angle
        \note A type for the coordinate must be included whenever this variable
        is created.
     */
    Sexagesimal(int type_in)
    {
      // Set the coordinate type
      if (type_in < DEGREE_ANGLE || type_in > TIME_FORMAT){
        this->type = DEGREE_ANGLE;
      }
      else {
        this->type = type_in;
      }
      this->type = type_in;
      
      // Set the sign to 0.  The sign is either 1 or -1, initializing to 0 
      // should flag when the sign isn't set properly when reading input.
      this->sign = 0;
    }
    
    /**************** Sexagesimal::set ****************/
    /**
     Set the time for sexagesimal class variables with a number as the input.  
     The variable value is templated, so any numerical variable type should be able
     to go through this.
     \param [input] The numerical input value.
     \note This uses a template for the variable type.
     */
    template <class T>
    void set(T input)
    {
      // Set the floating point value for the entire number.
      this->value = input;

      // For an hour angle variable, set the degree value to get from 24 
      // hours to 360 degrees.
      if (this->type == HOUR_ANGLE || this->type == RA_ANGLE){
        this->degree_value = this->value * 15;
      }
      // Otherwise, the degree value should be the same.
      else {
        this->degree_value = this->value;
      }
      
      // Find the sign
      this->sign = 1;
      if (input < 0){
        this->sign = -1;
      }
      // Set the input to positive for the next steps
      input = std::abs(input);
      
      // Convert the numerical value into the sexagesimal representation.  This
      // requires converting the leading numbers to int values and then operating
      // on the remainders to get the answer.
      float temp;   // Temporary variable
      this->angle = (int) input;
      temp = (input - this->angle) * 60;
      this->minute = (int) temp;
      this->second = (temp - this->minute) * 60;
    }
    /**************** Sexagesimal::set ****************/
    
    // Get the time and output in a numerical format
    float get_value();
    
    // Get the degree version of time and output in a numerical format
    float get_degree_value();
    
    // Get the time and output in a string format of HH:MM:SS.SSS.
    std::string get();
    
    // Get the time and output in a string format; the format is set by the 
    // defined type for the class and outputs in a fancier format that matches
    // the format.  
    std::string get_fancy();
    
};

/**************** Sexagesimal::set ****************/
/**
 Set the values for a sexagesimal class variable using a string as input.
 \param [input] The input string.
 \note None.
 */
template <>
inline void Sexagesimal::set <std::string> (std::string input)
{
  // Break the input string into tokens.  The string is separated by looking
  // for spaces, :, ', " and  symbols, which hopefully covers the most
  // likely separators for time and angle inputs.  Can add to this as 
  // necessary, might want h, d, m and other alphabel characters eventually.
  std::vector<std::string> tokens;  // Temporary tokens
  Tokenize(input, tokens, " :\'\"");
  int size = tokens.size();
  
  // If there are no tokens (which should not be possible), then set everything
  // to 0
  if (size == 0 || size > 3){
    this->angle = 0;
    this->sign = 0;
    this->minute = 0;
    this->second = 0;
    this->value = 0;
  }

  // Set the tokens
  else {
    // The first token is the first value, duh.  Check the sign of the number
    // and set the sign variable.
    this->angle = atoi(tokens[0].c_str());
    if (tokens[0][0] == '-'){
      this->sign = -1;
    }
    else {
      this->sign = 1;
    }
    this->angle = std::abs(this->angle);
    // If there is only one token, set the minute and second based on the remainder
    if (size == 1){
    	float temp = fabs(atof(tokens[0].c_str())) - this->angle;
    	temp = temp * 60;
      this->minute = (int) temp;
      this->second = (temp - this->minute) * 60;
      
    }
    // Same deal with token 3.  Note that is a float, we carry decimal values
    // here instead of breaking them out.
    else if (size == 2){
      this->minute = atoi(tokens[1].c_str());
    	this->second = (atof(tokens[1].c_str()) - this->minute) * 60;
    }
    else {
      this->minute = atoi(tokens[1].c_str());
      this->second = atof(tokens[2].c_str());
    }
    // Set the floating point value for the entire number.
    this->value = this->sign * (this->angle + this->minute / 60. + this->second / 3600.);
  }
  
  // For an hour angle variable, set the degree value to get from 24 
  // hours to 360 degrees.
  if (this->type == HOUR_ANGLE || this->type == RA_ANGLE){
    this->degree_value = this->value * 15;
  }
  // Otherwise, the degree value should be the same.
  else {
    this->degree_value = this->value;
  }
}
/**************** Sexagesimal::set ****************/

/** \class Coord
 \brief Astronomical coordinate handling class.
 \details  
class Coord {
  private:
    
    
  
  public:
    
    
};
*/


# endif


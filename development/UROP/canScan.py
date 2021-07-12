# -*- coding: utf-8 -*-
"""
Created on Mon Jun 14 18:01:42 2021

@author: Abigail Schipper
"""
import astropy.units as u
from astropy.time import Time
from astropy.coordinates import SkyCoord, EarthLocation, AltAz, get_moon, get_body


def RAtoAzimuth(RA,Dec,Time=Time.now(),location=EarthLocation.of_site('Palomar')):
    '''

    Parameters
    ----------
    RA : String
        Right ascension of body you wish to observe. in format '00h00m00.00s'
    Dec : String
         Declination of body you wish to observe in format '00d00m00.00s'.
    Time : astropy Time i.e. Time ('YYYY-MM-DD HH:MM:SS')
        Time (in UTC) you'll be observing. Defaults to now.
    location : astropy EarthLocation i.e. EarthLocation(lat=00.00*u.deg, lon=+00.00*u.deg,height=00*u.m), optional
        Location you'll be observing. Defaults to Palomar Observatory

    Returns
    -------
    Astropy coordinate
        The AltAz coordinate of the inputted body
    '''
    RAcoord=SkyCoord(RA,Dec,frame='icrs') 
    return RAcoord.transform_to(AltAz(obstime=Time,location=location))

def above_horizon(RA,Dec,Time=Time.now(), location=EarthLocation(lat=33.3563*u.deg, lon=-116.8650*u.deg, height=1712*u.m)):
    '''
    Parameters
    ----------
    RA : String
        Right ascension of body you wish to observe. in format '00h00m00.00s'
    Dec : String
         Declination of body you wish to observe in format '00d00m00.00s'.
    Time : astropy Time i.e. Time ('YYYY-MM-DD HH:MM:SS')
        Time (in UTC) you'll be observing. Defaults to now.
    location : astropy EarthLocation i.e. EarthLocation(lat=00.00*u.deg, lon=+00.00*u.deg,height=00*u.m), optional
        Location you'll be observing. Defaults to Palomar Observatory
    
    Returns
    -------
    Boolean
        True if elevation of object is more than 20 degrees above the horizon.
        False if elevation of object is less than 20 degrees above the horizon
    '''
    AltAz=RAtoAzimuth(RA,Dec,Time,location) #Convert to AltAz
    altString="{0.alt}".format(AltAz) #altitude reading in a string
    altitude=float(altString.split()[0]) #just altitude as a float
    return altitude>=20 #is the altitude greater than 15 degrees?
      

def avoid_zenith(RA,Dec,Time=Time.now(), location=EarthLocation.of_site('Palomar')):
    '''
    Parameters
    ----------
    RA : STRING
        Right ascension of body you wish to observe. in format '00h00m00.00s'
    Dec : String
         Declination of body you wish to observe in format '00d00m00.00s'.
    LocalTime : astropy Time i.e. Time ('YYYY-MM-DD HH:MM:SS')
        Time (in UTC) date you will be observing. Defaults to now.
    location : astropy EarthLocation i.e. EarthLocation(lat=00.00*u.deg, lon=+00.00*u.deg,height=00*u.m), optional
        DESCRIPTION. The default is is Palomar Observatory
    timezone : astropy integer with units hours i.e. 0*u.hour, optional
        DESCRIPTION. The default is -7*u.hour which is California in Daylight Savings (Mar-Nov)

    Returns
    -------
    Boolean
        True if object is more than 5 degrees away from zenith 
        False if object is within 5 degrees of zenith (i.e. elevation 85 to 95 degs)

    '''
    AltAz=RAtoAzimuth(RA,Dec,Time,location) #Convert to AltAz
    altString="{0.alt}".format(AltAz) #altitude reading in a string
    altitude=float(altString.split()[0]) #just altitude as a float
    return abs(altitude-90)>5 #is the altitude greater than 15 degrees?

def avoid_moon(RABody,DecBody,Filter,Time=Time.now(),location=EarthLocation.of_site('Palomar')):
    '''
     Parameters
    ----------
    RABody : String
        Right ascension of body you wish to observe. in format '00h00m00.00s'
    DecBody : String
         Declination of body you wish to observe in format '00d00m00.00s'.
    Filter : String
        Filter being used on telescope. 'u' for Ultraviolet and 'r' for Red.
    Time : astropy Time i.e. Time ('YYYY-MM-DD HH:MM:SS')
        Time (in UTC) you'll be observing. Defaults to now.
    location : astropy EarthLocation i.e. EarthLocation(lat=00.00*u.deg, lon=+00.00*u.deg,height=00*u.m), optional
        Location you'll be observing. Defaults to Palomar Observatory
        
    Returns
    -------
    Tuple
        First term is Boolean:
            True if object is more than 15 degrees away from moon 
            False if object is within 15 degrees of moon
        Second Term is String:
            "Moon: DEGREES OF SEPARATION degs "

    '''
    if Filter=='u':
        keepOut=25
    elif Filter=='r':
        keepOut=15
    body=SkyCoord(RABody,DecBody,frame='icrs') #convert RA and Dec into a skycoord
    moon=get_moon(Time,location) #get coordinates of moon
    sep=moon.separation(body) #find angular separation between moon and body
    return (keepOut<sep.deg,'Moon: '+str(sep.deg)+' degs\n') #is separation more than 15 degrees?

def avoid_planet(RABody,DecBody,Time=Time.now(),location=EarthLocation.of_site('Palomar'), Planets=['Mercury','Venus','Mars','Jupiter','Saturn']):
    '''
    
     Parameters
    ----------
    RABody : String
        Right ascension of body you wish to observe. in format '00h00m00.00s'
    DecBody : String
         Declination of body you wish to observe in format '00d00m00.00s'.
    Time : astropy Time i.e. Time ('YYYY-MM-DD HH:MM:SS')
        Time (in UTC) you'll be observing. Defaults to now.
    location : astropy EarthLocation i.e. EarthLocation(lat=00.00*u.deg, lon=+00.00*u.deg,height=00*u.m), optional
        Location you'll be observing. Defaults to Palomar Observatory
        
    Returns
    -------
    Tuple
        First Term Boolean:
            True if object is more than 1 degree away from all Planets 
            False if object is within 1 degree of any Planet
        Second Term String:
            "PLANET: DEGREES OF SEPARATION degs" ordered closest to farthest
            

    '''
    body=SkyCoord(RABody,DecBody,frame='icrs') #convert RA and Dec into a skycoord
    distPlanets={}
    returnPlanets=''
    avoidPlanet=True
    for i in range (len(Planets)):
        planet=get_body(Planets[i],Time,location) #get coordinate of each planet
        sep=planet.separation(body) #get separation between planet and body
        distPlanets[float(str(sep.deg).split()[0])]=Planets[i] #store separation as key and planet as value in a dictionary
        if 1>sep.deg: #if any planet is closer than 1 degree, turn to False
            avoidPlanet=False
    for distance in sorted(distPlanets): returnPlanets+=distPlanets[distance]+': '+str(distance)+' degs\n' #sort planets closest to farthest from body
    return (avoidPlanet,returnPlanets)



def CanScan(RA,Dec,Filter,moreData=False,Time=Time.now(), location=EarthLocation.of_site('Palomar')):
    '''

    Parameters
    ----------
    RA : STRING
        Right ascension of body you wish to observe. in format '00h00m00.00s'
    Dec : String
         Declination of body you wish to observe in format '00d00m00.00s'.
    Filter : String
        Filter being used on telescope. 'u' for Ultraviolet and 'r' for Red.
    moreData : Boolean
        False if you just want a boolean return (default), True if you want results of each scan test and distances to moon and planets
    Time : astropy Time i.e. Time ('YYYY-MM-DD HH:MM:SS')
        Time (in UTC) you'll be observing. Defaults to now.
    location : astropy EarthLocation i.e. EarthLocation(lat=00.00*u.deg, lon=+00.00*u.deg,height=00*u.m), optional
        Location you'll be observing. Defaults to Palomar Observatory

    Returns
    -------
    If moreData==False:
        Boolean 
             True if it passes all scan tests
             False if fails any scan test
    If moreData==True:
        String
            Can Scan! followed by the moon distance, then the distances of the planets closest to farthest
            Uh Oh! followed by the boolean for each test, followed by the the moon distance, then the distances of the planets closest to farthest

    '''
    aboveHorizon=above_horizon(RA, Dec, Time, location)
    avoidZenith=avoid_zenith(RA, Dec, Time, location)
    avoidMoon=avoid_moon(RA, Dec, Filter, Time, location)
    avoidPlanets=avoid_planet(RA,Dec, Time, location)
    if not moreData: return aboveHorizon and avoidZenith and avoidMoon[0] and avoidPlanets[0] #returns boolean for if it passes scan test
    if aboveHorizon and avoidZenith and avoidMoon[0] and avoidPlanets[0]: #if passes all of the scan tests
        return 'Can Scan!\n'+str(avoidMoon[1])+ avoidPlanets[1]
    else: #if it fails any of the scan tests
        return 'Uh Oh!\n'+ 'Above Horizon? '+str(aboveHorizon)+'\nAvoids Zenith? '+str(avoidZenith)+'\nAvoids Moon? '+str(avoidMoon[0])+ '\nAvoids Planets? '+str(avoidPlanets[0])+'\n'+str(avoidMoon[1])+str(avoidPlanets[1])
    
   

### TEST CASES ###
# print(RAtoAzimuth('13h42m08.10s', '+09d28m38.61s',Time('2021-06-15T06:00:00')))
print(CanScan('13h42m08.10s', '+09d28m38.61s','u',Time=Time('2021-06-15T06:00:00')))
print(CanScan('08h19m24.2s','+20d55m34.6s','u',Time=Time('2021-06-15T06:00:00')))
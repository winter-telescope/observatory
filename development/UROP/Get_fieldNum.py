# -*- coding: utf-8 -*-
"""
Created on Mon Jun 21 15:35:52 2021

@author: cruzs
"""
import astropy.units as u
from astropy.coordinates import Angle
import pandas as pd

def GetFieldNum(ra, dec, fieldNums):
    '''

    Parameters
    ----------
    ra : STRING
        Right ascension of body you wish to observe in format '00h00m00.00s'
    Dec : STRING
         Declination of body you wish to observe in format '00d00m00.00s'
    fieldNums : DataFrame
        Dataframe of field numbers associated with any two RA and Dec pair
        
    Returns
    -------
    Integer
        Associated field ID number for ra and dec pair
    '''
    
    ra,dec = Angle(ra), Angle(dec) #Converting ra and dec to angles
    ra,dec = float(ra.to_string(unit = u.degree, decimal = True)), float(dec.to_string(unit = u.degree, decimal = True))
    
    #print(ra,dec)
    
    closest_dec = float(fieldNums.iloc[(fieldNums['Dec']-dec).abs().argsort()[:1]]["Dec"])
    narrowedDf = fieldNums[fieldNums.Dec == closest_dec]
    
    return int(narrowedDf.loc[[narrowedDf["RA"].sub(ra).abs().idxmin()]]["# ID"])

data = pd.read_fwf(r"C:\Users\cruzs\Documents\Palomar\GIT\code\scheduler\daily_summer_scheduler\data\SUMMER_fields.txt")
df = pd.DataFrame(data)
#print(df.shape)

print("Field ID number: " + str(GetFieldNum('13h42m08.10s', '+09d28m38.61s', df)))
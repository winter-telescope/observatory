# -*- coding: utf-8 -*-
"""
Created on Mon Jun 21 13:39:00 2021

@author: Abigail Schipper
"""

import pandas as pd
import astropy.units as u
from astropy.coordinates import Angle
import requests

def fieldFinder(RA,Dec,decimal=False,sigma=0.13009,file='SUMMER_fields.txt',names=['ID',"RA",'Dec','EBV','GalLong','GalLat','EclLong','EclLat']):
    '''
    Parameters
    ----------
    RA: Float
        Right ascension in decimal form
    Dec: Float
        Declination in decimal form
    decimal: Boolean
        True if RA/Dec in decimal form. False if RA/Dec in 00h00m00s/00d00m00s form (default)
    Sigma: FLoat
        Distance that the field's Dec can be from desired Dec. Defaults to 13.009
    File: String
        File name of file with fields. Defaults to "SUMMER_fields.txt
    Names: List of strings
        Names of columns. Defaults to ['ID',"RA",'Dec','EBV','GalLong','GalLat','EclLong','EclLat'])
    
    Returns
    -------
    Integer
        Field ID closest to given RA Dec
    '''
    if decimal==False: #if RA Dec in 00h00m00s format, convert to decimal
        RA,Dec = Angle(RA), Angle(Dec) #Converting ra and dec to angles
        RA,Dec = float(RA.to_string(unit = u.degree, decimal = True)), float(Dec.to_string(unit = u.degree, decimal = True))
    #import data and create a DataFrame
    data=pd.read_fwf(file)
    df=pd.DataFrame(data)
    #find rows with Decs closest to desired Dec
    decs=df['Dec'].between(abs(Dec)-sigma,abs(Dec)+sigma)
    absDecs=df[decs]
    #the data imported such that the negative values do not show up as negative, so this loop ensures that, if desired Dec is negative/positive, it gets the proper results
    if Dec>0:
        while absDecs.iloc[0,0]>302864: #positive Decs should have an ID less than this
            absDecs=absDecs.drop([absDecs.iloc[0,0]-1])
    else:
        while absDecs.iloc[0,0]<302864: #negative Decs should have an ID less than this
            absDecs=absDecs.drop([absDecs.iloc[0,0]-1])
    smallestDist=360 #max distance it can be is 360, so this is the initial smallest
    for row in range(len(absDecs)): #find closest RA by comparing each distance and saving when it is the new shortest
        if abs(RA-absDecs.iloc[row,1])<smallestDist:
            smallestDist=abs(RA-absDecs.iloc[row,1])
            bestRow=row
    return absDecs.iloc[bestRow,0]



def getRADecs(url):
    '''

    Parameters
    ----------
    url : String
        A url of supernovae from a csv in https://sites.astro.caltech.edu/ztf/bts/explorer.php?f=s&subsample=sn&classstring=Ia&quality=y&purity=y&ztflink=lasair&startsavedate=2021-05-31&endsavedate=2021-06-15&endpeakmag=19.0&reverse=y.

    Returns
    -------
    RAs : A list of strings
        RAs of supernovae in form 00h00m00s
    Decs : A list of strings
        Decs of supernovae in form 00h00m00s.

    '''
    request=requests.get(url)
    text=request.text
    split=text.split(',')
    RAs=[]
    for i in range((len(split)-15)//14):
        raCol=split[(14*i)+16]
        splitRA=raCol.split(':')
        RAs.append(splitRA[0]+'h'+splitRA[1]+'m'+splitRA[2]+'s')
    
    Decs=[]
    for i in range((len(split)-15)//14):
        decCol=split[(14*i)+17]
        splitDec=decCol.split(':')
        Decs.append(splitDec[0]+'d'+splitDec[1]+'m'+splitDec[2]+'s')
    return RAs, Decs
    

def get_fields(url=None,RAs=None,Decs=None,sigma=0.13009,file='SUMMER_fields.txt',names=['ID',"RA",'Dec','EBV','GalLong','GalLat','EclLong','EclLat']):
    '''
    
    Either have a url with the RA/Decs, or input your own through RAs and Decs.
    Parameters
    ----------
    url : String
        A URL of the supernovae from a csv in https://sites.astro.caltech.edu/ztf/bts/explorer.php?f=s&subsample=sn&classstring=Ia&quality=y&purity=y&ztflink=lasair&startsavedate=2021-05-31&endsavedate=2021-06-15&endpeakmag=19.0&reverse=y.RIPTION. Defaults to none if you have no url
    RAs: List of strings
        List of RAs in form 00h00m00s. Defaults to None. Leave as none if using a url for RA/Decs
    Decs: List of strings
        List of Decs in form 00d00m00s. Defaults to None. Leave as none if using a url for RA/Decs
    sigma : FLoat, optional
        Distance that the field's Dec can be from desired Dec. Defaults to 0.13009
    file : String, optional
        File name of file with fields. Defaults to "SUMMER_fields.txt
    names : List of strings, optional
        Names of columns. Defaults to ['ID',"RA",'Dec','EBV','GalLong','GalLat','EclLong','EclLat'])

    Returns
    -------
    fields : List of integers
        Field IDs of each RA/Dec

    '''
    if RAs==None and Decs==None:  
        RAs,Decs=getRADecs(url)
    fields=[]
    for i in range(len(RAs)):
        fields.append(fieldFinder(RAs[i],Decs[i]))
    return fields
                
        
    
    
    
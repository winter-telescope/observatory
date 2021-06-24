import pandas as pd
import requests
import astropy.units as u
from astropy.coordinates import Angle

def get_fields(url=None,rochester=False,RAs=None,Decs=None,sigma=0.13009,file='SUMMER_fields.txt',names=['ID',"RA",'Dec','EBV','GalLong','GalLat','EclLong','EclLat']):
    '''
    
    Either have a url with the RA/Decs, or input your own through RAs and Decs.
    Parameters
    ----------
    url : String
        A URL of the supernovae from a csv in https://sites.astro.caltech.edu/ztf/bts/explorer.php?f=s&subsample=sn&classstring=Ia&quality=y&purity=y&ztflink=lasair&startsavedate=2021-05-31&endsavedate=2021-06-15&endpeakmag=19.0&reverse=y.RIPTION.
        or https://www.rochesterastronomy.org/sn2021/snlocations.html
        Defaults to none if you have no url
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
    data = pd.read_fwf("SUMMER_fields.txt")
    df = pd.DataFrame(data)
    if RAs==None and Decs==None:
        if not rochester:
            RAs,Decs=getRADecs(url)
        else:
            RAs,Decs=get_html_panda(url)
    fields=[]
    for i in range(len(RAs)):
        fields.append(GetFieldNum(RAs[i], Decs[i], df))
    return fields
        
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
    
    ra,dec = Angle(ra,unit=u.deg), Angle(dec,unit=u.deg) #Converting ra and dec to angles
    ra,dec = float(ra.to_string(unit = u.degree, decimal = True)), float(dec.to_string(unit = u.degree, decimal = True))
    
    #print(ra,dec)
    
    closest_dec = float(fieldNums.iloc[(fieldNums['Dec']-dec).abs().argsort()[:1]]["Dec"])
    narrowedDf = fieldNums[fieldNums.Dec == closest_dec]
    
    return int(narrowedDf.loc[[narrowedDf["RA"].sub(ra).abs().idxmin()]]["# ID"])


data = pd.read_fwf("SUMMER_fields.txt")
df = pd.DataFrame(data)

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

def get_html_panda(URL):
    html = requests.get(URL).content
    df_list = pd.read_html(html)
    df = df_list[-1]
    return df['R.A.'],df['Decl.']
    

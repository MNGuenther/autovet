import numpy as np
import fitsio
#import os
import kepselfflatten
#import itertools




#'Candidate' Class
class Candidate(object):

    """ Obtain meta and lightcurve information for a specific candidate. """
    

    def __init__(self,id,filepath,observatory='NGTS',field_dic=None,label=-10,candidate_data={'per':0.,'t0':0.,'tdur':0.},stellar_radius=1., field_periods=None, field_epochs=None):
        """
        Take candidate and load lightcurve, dependent on observatory.
        
        Arguments:
        id          -- object identifier. Observatory dependent.
                       if NGTS, id should be either a single obj_id (int / string) or array_like containing multiple obj_ids (int / string)
        filepath    -- location of object file. Observatory dependent.
                       if NGTS, filepath should be array_like containing ['fieldname', 'ngts_version'] 
        observatory -- source of candidate. Accepted values are: [NGTS,Kepler,K2]
        label       -- known classification, if known. 0 = false positive, 1 = planet. -10 if not known.
        candidate_data   -- details of candidate transit. Should be a dict containing the keys 'per', 't0' and 'tdur' (planet period, epoch and transit duration, all in days). If not filled, certain features may not work. Candidate will be ignored in flattening procedure
        stellar_radius   -- estimate of the host star radius, in solar radii. Used to estimate the planetary radius.
        field_periods    -- array of all candidate periods from that field.
        field_epochs    -- array of all candidate epochs from that field.
        """
        self.id = id
        self.filepath = filepath
        self.obs = observatory 
        self.field_dic = field_dic
        self.label = label
        self.candidate_data = candidate_data
        self.stellar_radius = stellar_radius  #in solar, will default to 1 if not given
        
        self.lightcurve, self.info = self.LoadLightcurve()
        self.exp_time = np.median(np.diff(self.lightcurve['time']))
        self.field_periods = field_periods
        self.field_epochs = field_epochs
        if observatory == 'Kepler' or observatory == 'K2':
            self.lightcurve_f = self.Flatten()
        else:
            self.lightcurve_f = self.lightcurve

    def LoadLightcurve(self):
        """
        Load lightcurve from set observatory.
        
        Returns:
        lc -- lightcurve as dict. Minimum keys are [time, flux, error].
        """
        if self.obs=='NGTS':
            #self.field = os.path.split(filepath)[1][:11]
            lc, info = self.NGTSload()
        elif self.obs=='NGTS_synth':
            lc = self.NGTS_synthload()
            info = None
        elif self.obs=='Kepler' or self.obs=='K2':
            lc = self.KepK2load()
            info = None
        elif self.obs=='TESS':
            lc = self.TESSload()
            info = None
        else:
            print 'Observatory not supported'
        return lc, info
        
    def NGTS_synthload(self):
        dat = np.genfromtxt(self.filepath)
        time = dat[:,0]
        flux = dat[:,1]
        err = dat[:,2]
        nancut = np.isnan(time) | np.isnan(flux) | np.isnan(err) | (flux==0)
        norm = np.median(flux[~nancut])
        lc = {}
        lc['time'] = time[~nancut]/86400.
        lc['flux'] = flux[~nancut]/norm
        lc['error'] = err[~nancut]/norm
        return lc
 
    
    def NGTSload(self):
        '''
        filepath = ['fieldname', 'ngts_version']
        obj_id = 1 or '000001' or [1,2,3] or ['000001','000002','000003']
        '''
        from ngtsio import ngtsio

        lc_keys = ['HJD', 'SYSREM_FLUX3', 'FLUX3_ERR']
        info_keys = ['OBJ_ID','FIELDNAME','NGTS_VERSION','FLUX_MEAN','RA','DEC','NIGHT','AIRMASS','CCDX','CCDY','CENTDX','CENTDY']
        passflag = False
        
        #if there is no field_dic passed, use ngtsio to read out the info for a single object from the fits files
        if self.field_dic is None:
            if self.filepath is not None:
                fieldname, ngts_version = self.filepath
                dic = ngtsio.get( fieldname, ngts_version, lc_keys + info_keys, obj_id=str(self.id).zfill(6), silent=True, set_nan=True )
            else:
                passflag = True
        #if a field_dic was passed (in memory), then select the specific object and store it into dic
        else:
            ind_obj = np.where( self.field_dic['OBJ_ID'] == self.id )[0]
            if (len(ind_obj)>0) and ('FLUX3_ERR' in self.field_dic.keys()):
                dic = {}
                for key in ['OBJ_ID','FLUX_MEAN','RA','DEC']:
                    dic[key] = self.field_dic[key][ind_obj][0]
                for key in ['HJD','SYSREM_FLUX3','FLUX3_ERR','CCDX','CCDY','CENTDX','CENTDY']:
                    dic[key] = self.field_dic[key][ind_obj].flatten()
                for key in ['FIELDNAME','NGTS_VERSION','NIGHT','AIRMASS']:
                    dic[key] = self.field_dic[key]
            else:  #this is a candidate that wasn't in the field_dic
                passflag = True
        if passflag:
            lc = {}
            lc['time'] = np.zeros(10)-10
            lc['flux'] = np.zeros(10)-10
            lc['error'] = np.zeros(10)-10
            info = 0
            return lc, info
                
        nancut = np.isnan(dic['HJD']) | np.isnan(dic['SYSREM_FLUX3']) | np.isnan(dic['FLUX3_ERR']) | np.isinf(dic['HJD']) | np.isinf(dic['SYSREM_FLUX3']) | np.isinf(dic['FLUX3_ERR']) | (dic['SYSREM_FLUX3']==0)
        norm = np.median(dic['SYSREM_FLUX3'][~nancut])
        lc = {}
        lc['time'] = dic['HJD'][~nancut]/86400.
        lc['flux'] = 1.*dic['SYSREM_FLUX3'][~nancut]/norm
        lc['error'] = 1.*dic['FLUX3_ERR'][~nancut]/norm
        
        info = {}
        for info_key in info_keys: 
            if isinstance(dic[info_key], np.ndarray):
                info[info_key] = dic[info_key][~nancut]
            else:
                info[info_key] = dic[info_key]
        info['nancut'] = nancut
        
        del dic
        return lc, info
        
        
    
    def KepK2load(self,inputcol='PDCSAP_FLUX',inputerr='PDCSAP_FLUX_ERR'):
        """
        Loads a Kepler or K2 lightcurve, normalised and with NaNs removed.
        
        Returns:
        lc -- lightcurve as dict, with keys time, flux, error
        """
        if self.filepath[-4:]=='.txt':
            dat = np.genfromtxt(self.filepath)
            time = dat[:,0]
            flux = dat[:,1]
            err = dat[:,2]
        else:
            dat = fitsio.FITS(self.filepath)
            time = dat[1]['TIME'][:]
            flux = dat[1][inputcol][:]
            err = dat[1][inputerr][:]
        nancut = np.isnan(time) | np.isnan(flux) | np.isnan(err)
        norm = np.median(flux[~nancut])
        lc = {}
        lc['time'] = time[~nancut]
        lc['flux'] = flux[~nancut]/norm
        lc['error'] = err[~nancut]/norm
        if self.obs=='K2':
            linfit = np.polyfit(lc['time'],lc['flux'],1)
            lc['flux'] = lc['flux'] - np.polyval(linfit,lc['time']) + 1
        del dat
        return lc

    def TESSload(self):
        """
        Loads a TESS lightcurve (currently just the TASC WG0 simulated ones), normalised and with NaNs removed.
        
        Returns:
        lc -- lightcurve as dict, with keys time, flux, error. error is populated with zeros.
        """
        dat = np.genfromtxt(self.filepath)
        time = dat[:,0]
        flux = dat[:,1]
        err = np.zeros(len(time))
        nancut = np.isnan(time) | np.isnan(flux)
        norm = np.median(flux[~nancut])
        lc = {}
        lc['time'] = time[~nancut]
        lc['flux'] = flux[~nancut]/norm
        lc['error'] = err[~nancut]/norm
        del dat
        return lc

    def Flatten(self,winsize=6.,stepsize=0.3,polydegree=3,niter=10,sigmaclip=8.,gapthreshold=1.):
        """
        Flattens loaded lightcurve using a running polynomial
        
        Returns:
        lc_flatten -- flattened lightcurve as dict, with keys time, flux, error
        """
        lc = self.lightcurve
        if self.candidate_data['per']>0:
            lcf = kepselfflatten.Kepflatten(lc['time']-lc['time'][0],lc['flux'],lc['error'],np.zeros(len(lc['time'])),winsize,stepsize,polydegree,niter,sigmaclip,gapthreshold,lc['time'][0],False,True,self.candidate_data['per'],self.candidate_data['t0'],self.candidate_data['tdur'])        
        else:
            lcf = kepselfflatten.Kepflatten(lc['time']-lc['time'][0],lc['flux'],lc['error'],np.zeros(len(lc['time'])),winsize,stepsize,polydegree,niter,sigmaclip,gapthreshold,lc['time'][0],False,False,0.,0.,0.)
        lc_flatten = {}
        lc_flatten['time'] = lcf[:,0]
        lc_flatten['flux'] = lcf[:,1]
        lc_flatten['error'] = lcf[:,2]
        return lc_flatten

    

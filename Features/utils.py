import numpy as np
from scipy import interpolate,stats

def SPhot(lc,P_rot,k=5):
    """
    S_phot,k diagnostic (see Mathur et al 2014)
    """
    while k*P_rot > (lc['time'][-1] - lc['time'][0])/3.:
        k -= 1
        
    if k == 0:
        return np.zeros(10)
            
    #make time segments
    segwidth = k * P_rot
    
    nsegments = np.floor((lc['time'][-1]-lc['time'][0])/segwidth)   #will skip data at the end if segwidth doesn't exactly fit lc length
    tboundaries = np.arange(nsegments) * segwidth + lc['time'][0]
    
    #set up output array and index count
    
    pointindex = 0
    sphot = []
    npoints = []
    segtimes = []
    expectednpoints = segwidth/np.median(np.diff(lc['time']))
    while lc['time'][-1]-lc['time'][pointindex] > segwidth:
        stopindex = np.searchsorted(lc['time'],lc['time'][pointindex]+segwidth)
        if stopindex - pointindex > 0.75*expectednpoints:
            sphot.append(np.std(lc['flux'][pointindex:stopindex]))
            npoints.append(stopindex-pointindex)
            segtimes.append(np.mean(lc['time'][pointindex:stopindex]))
        pointindex += 1
        
    sphot = np.array(sphot)
    return sphot


def CalcContrast(SPhotseg,SPhotglob):  #SPhotglob is std of whole lightcurve
    """
    Contrast (see Mathur et al 2014)
        
    Will be returned as part of SPhot.
    """
    nhigh = SPhotseg>=SPhotglob
    SPhothigh = np.mean(SPhotseg[nhigh])
    SPhotlow = np.mean(SPhotseg[~nhigh])
    return SPhothigh/SPhotlow

def CutOutliers(time,flux):
    threshold = np.percentile(flux,[2,98])
    mednorm = np.median(flux)
    MAD_calc = 1.4826 * np.median(np.abs(flux - mednorm))
    sigmathreshold = [5*MAD_calc + mednorm,mednorm - 5*MAD_calc]
    if threshold[1] > sigmathreshold[1]:  #takes the least active cut option
        cut = (flux<threshold[1])&(flux>threshold[0])
    else:
        cut = (flux<sigmathreshold[1])&(flux>sigmathreshold[0])

    return time[cut],flux[cut]

def MovingAverage(interval, window_size): #careful with start and end. Also requires regular grid.
    window= np.ones(int(window_size))/float(window_size)
    return np.convolve(interval, window, 'same')

def FillGaps_Linear(time,flux):       
    cadence = np.median(np.diff(time))
    npoints = np.floor((time[-1]-time[0])/cadence)
    interp_times = np.arange(npoints)*cadence + time[0]
    if interp_times[-1] > time[-1]:
        interp_times = interp_times[:-1]
    interp_obj = interpolate.interp1d(time,flux,kind='linear')
    interp_flux = interp_obj(interp_times)
    return interp_times,interp_flux


def phasefold(time,per):
    return np.mod(time,per)/per
    
def BinPhaseLC(phaselc,nbins):
    bin_edges = np.arange(nbins)/float(nbins)
    bin_indices = np.digitize(phaselc[:,0],bin_edges) - 1
    binnedlc = np.zeros([nbins,2])
    binnedlc[:,0] = 1./nbins * 0.5 +bin_edges  #fixes phase of all bins - means ignoring locations of points in bin, but necessary for SOM mapping
    binnedstds = np.zeros(nbins)
    for bin in range(nbins):
        if np.sum(bin_indices==bin) > 0:
            binnedlc[bin,1] = np.mean(phaselc[bin_indices==bin,1])  #doesn't make use of sorted phase array, could probably be faster?
            binnedstds[bin] = np.std(phaselc[bin_indices==bin,1])
        else:
            binnedlc[bin,1] = np.mean(phaselc[:,1])  #bit awkward this, but only alternative is to interpolate?
            binnedstds[bin] = np.std(phaselc[:,1])
    return binnedlc,binnedstds

# -*- coding: utf-8 -*-
"""
Created on Fri Mar 10 16:37:37 2017

@author:
Maximilian N. Guenther
Battcock Centre for Experimental Astrophysics,
Cavendish Laboratory,
JJ Thomson Avenue
Cambridge CB3 0HE
Email: mg719@cam.ac.uk
"""

import numpy as np
import matplotlib.pyplot as plt
from ngtsio import ngtsio

from Loader.Loader import Candidate
from Loader.NGTS_MultiLoader import NGTS_MultiLoader
from Features.Centroiding.Centroiding_autovet_wrapper import centroid_autovet



def test():

    # a) laod candidate for a specific NGTS object
    obj_id = '009861'
    fieldname = 'NG0304-1115'
    ngts_version = 'TEST18'
    
    dic = ngtsio.get(fieldname, ['PERIOD','EPOCH','WIDTH'], obj_id=obj_id, silent=True)
    period = dic['PERIOD'] / 3600. / 24. #in days
    epoch = dic['EPOCH'] / 3600. / 24. #in days
    width = dic['WIDTH'] / 3600. / 24. #in days
    
    filepath = [fieldname, ngts_version]
    can = Candidate( obj_id, filepath, observatory='NGTS', field_dic=None, label=None, hasplanet={'per':period, 't0':epoch, 'tdur':width} )
    print can.lightcurve
    print can.info
    
    centroid_autovet( can )


    # b) load candidates with the NGTS_MultiLoader function
#    infile = 'test_infile.txt'
#    NGTS_MultiLoader(infile)



if __name__ == '__main__':
    test()
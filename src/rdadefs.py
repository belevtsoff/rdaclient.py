'''
@author: Dmytro Bielievtsov

This module contains BrainVision Remote Data Access (RDA) API definitions.
The module is based on the API implementation (in C) found in the FieldTrip
package http://fieldtrip.fcdonders.nl (rdadefs.h)

Refer to the Chapter 12 of the BrainAmp user manual for detailed API
description

'''
from ctypes import *

#===============================================================================
# Type structures
#===============================================================================

class rda_msg_hdr_t(Structure):
    '''
    RDA message header
    
    '''
    _pack_ = 1
    _fields_ = [
                ('guid', c_ubyte * 16),
                ('nSize', c_ulong),
                ('nType', c_ulong),
               ]
    
    
class rda_msg_data_t(Structure):
    '''
    RDA data message
    
    '''
    _pack_ = 1
    _fields_ = [
                ('hdr', rda_msg_hdr_t),
                ('nBlock', c_ulong),
                ('nPoints', c_ulong),
                ('nMarkers', c_ulong),
               ]
    
    @classmethod
    def full(cls, nChannels, nPoints, markersLength):
        '''
        Gets a complete structure including variable fields
        
        @param nChannels: number of channels (from start message)
        @param nPoints: number of samples (from fixed part)
        @param markersLength: Length of the 'Markers' in bytes
        
        '''
        class rda_msg_start_full_t(Structure):
            _pack_ = 1
            _fields_ = list(cls._fields_) # copy
            _fields_.extend([
                             ('fData', c_float * nChannels * nPoints),
                             ('Markers', c_ubyte * markersLength)
                             ])
            
            varLength = sizeof(c_float) * nChannels * nPoints + \
                        sizeof(c_ubyte) * markersLength
            
        return rda_msg_start_full_t
    
    def read_markers(self):
        pass
    
    
class rda_msg_start_t(Structure):
    '''
    RDA start message (sent from the server after the client has connected)
    
    '''
    _pack_ = 1
    _fields_ = [
                ('hdr', rda_msg_hdr_t),
                ('nChannels', c_ulong),
                ('dSamplingInterval', c_double),
               ]
    
    @classmethod
    def full(cls, nChannels, stringLength):
        '''
        Gets a complete structure including variable fields
        
        @param nChannels: number of channels (from start message)
        @param stringLength: the length of the sChannelNames field in bytes
        
        '''
        class rda_msg_start_full_t(Structure):
            _pack_ = 1
            _fields_ = list(cls._fields_) # copy
            _fields_.extend([
                             ('dResolutions', c_double * nChannels),
                             ('sChannelNames', c_ubyte * stringLength)
                             ])
            
            varLength = sizeof(c_double) * nChannels + \
                        sizeof(c_ubyte) * stringLength
                        
        return rda_msg_start_full_t
    

class rda_marker_t(Structure):
    '''
    RDA marker structure
    
    '''
    _pack_ = 1
    _fields_ = [
                ('nSize', c_ulong),
                ('nPosition', c_ulong),
                ('nPoints', c_ulong),
                ('nChannel', c_int),
               ]
    
    @classmethod
    def full(cls, stringLength):
        '''
        Gets a complete structure including variable fields
        
        @param stringLength: the length of the sTypeDesc field in bytes
        
        '''
        class rda_marker_full_t(Structure):
            _pack_ = 1
            _fields_ = list(cls._fields_) # copy
            _fields_.extend([
                             ('sTypeDesc', c_ubyte * stringLength)
                             ])
            
            varLength = sizeof(c_ubyte) * stringLength
            
        return rda_marker_full_t

#===============================================================================
# Constants
#===============================================================================

RDA_START_MSG = 1
RDA_INT_MSG = 2
RDA_STOP_MSG = 3
RDA_FLOAT_MSG = 4

RDA_GUID = (c_ubyte * 16).from_buffer(create_string_buffer \
           ('\x8e\x45\x58\x43\x96\xc9\x86\x4c\xaf\x4a\x98\xbb\xf6\xc9\x14\x50'))

__all__ = ['rda_marker_t', 'rda_msg_hdr_t', 'rda_msg_data_t',
           'rda_msg_start_t', 'blah']

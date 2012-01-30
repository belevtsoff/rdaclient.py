'''
@author: Dmytro Bielievtsov

Provides a two-dimensional circular buffer with homogeneous elements

classes:
    RingBuffer: the buffer
    datatypes: supported datatypes
    BufferHeader: header structure
    BufferError: error definition
    
'''

from multiprocessing import Array
import ctypes as c
import numpy as np
import logging

class RingBuffer(object):
    '''
    Provides a two-dimensional circular buffer with homogeneous elements
    
    The buffer can be used simultaneously by several processes, because
    both data and metadata are stored in a single sharectypes byte array.
    First, the buffer object is created and initialized in one of the 
    processes. Second, its raw array is shared with others. Third, those
    processes create their own RingBuffer objects and initialize them
    so that they all point to the same shared raw array
    (see initialize_from_raw method's docstring).
    
    Structure:
    
    The buffer consists of a buffer interface (self) and the raw sharectypes
    byte array which has header, data, and pocket subsections (self.raw).
    
    1. header section
    Contains the metadata such as size of the sections, current write
    pointer, datatype, number of channels (number of columns) and total
    number of samples (not bytes) written
    
    2. data section
    Contains the actual data in the buffer. When the write pointer reaches
    the end of the section it jumps to the beginning overwriting the old
    data.
    
    3. pocket section
    The pocket section always contains the same data as the leftmost such
    chunk of the data section. This is done to avoid data copies when reading
    a data chunk (up to the size of the pocket) first part of which happens
    to be located at the end of the data section while the second - already
    in the beginning. This might be useful when reading the data with a 
    sliding window.
    
    '''
    def __init__(self):
        '''
        Creates new buffer interface
        
        '''
        self.logger = logging.getLogger('ringbuffer')
        self.__initialized = False
    
    def __str__(self):
        '''
        __str__ overload for printing buffer contents
        
        '''
        return self.__buf[:self.bufSize].T.__str__() + '\n' + self.__pocket.T.__str__()
    
    def __getattr__(self, name):
        '''
        __getattr__ overload to avoid accessing buffer attributes before it's
        initialized 
        
        @param name: name of the attribute
        
        @return: attribute, if possible
        
        '''
        init = self.__initialized
        
        if init:
            return object.__getattribute__(self, name)
        else:
            raise BufferError(1)
    
    #------------------------------------------------------------------------------
    # Properties    
    
    # number of written samples
    def __get_nsamples(self):
        return self.__hdr.nSamplesWritten
    def __set_nsamples(self, value):
        self.__hdr.nSamplesWritten = value
    nSamplesWritten = property(__get_nsamples, __set_nsamples)        
    
    # read-only attributes
    writePtr = property(lambda self: self.nSamplesWritten % self.bufSize, None, None,
                        'the current write pointer position')
    is_initialized = property(lambda self: self.__initialized, None, None,
                        'indicated whether buffer is initialized')
    raw = property(lambda self: self.__raw, None, None,
                        'raw buffer array')
    nChannels = property(lambda self: self.__nChannels, None, None,
                        'dimensionality of a sample')
    bufSize = property(lambda self: self.__bufSize, None, None,
                        'buffer capacity in samples')
    pocketSize = property(lambda self: self.__pocketSize, None, None,
                        'size of the buffer pocket in samples')
    nptype = property(lambda self: self.__nptype, None, None,
                        'the type of the data in the buffer')
    
    #------------------------------------------------------------------------------
    
    def initialize(self, nChannels, nSamples, windowSize=1, nptype='float32'):
        '''
        Initialize the buffer with a new raw array
         
        @param nChannels:  dimensionality of a single sample
        @param nSamples:   the buffer capacity in samples
        @param windowSize: optional, the size of the window to be used for
                           reading the data. The pocket of the this size will
                           be created
        @param nptype:     the type of the data to be stored
                           
        '''
        self.__initialized = True
        
        # checking parameters
        if nChannels < 1:
            self.logger.warning('nChannels must be a positive integer, setting to 1')
            nChannels = 1
        if nSamples < 1:
            self.logger.warning('nSamples must be a positive integer, setting to 1')
            nSamples = 1
        if windowSize < 1:
            self.logger.warning('wondowSize must be a positive integer, setting to 1')
            windowSize = 1
        
        # initializing
        sizeBytes = c.sizeof(BufferHeader) + \
                    (nSamples + windowSize) * nChannels * np.dtype(nptype).itemsize
        
        raw = Array('c', sizeBytes)
        hdr = BufferHeader.from_buffer(raw.get_obj())
        
        hdr.bufSizeBytes = nSamples * nChannels * np.dtype(nptype).itemsize
        hdr.pocketSizeBytes = windowSize * nChannels * np.dtype(nptype).itemsize
        hdr.dataType = datatypes.get_code(nptype)
        hdr.nChannels = nChannels
        hdr.nSamplesWritten = 0
        
        self.initialize_from_raw(raw.get_obj())
    
    def initialize_from_raw(self, raw):
        '''
        Initialize the buffer with the compatible external raw array. All the
        metadata will be read from the header region of this array.   
        
        @param raw: the raw array to initialize with
                           
        '''
        self.__initialized = True
        hdr = BufferHeader.from_buffer(raw)
        
        # datatype
        nptype = datatypes.get_type(hdr.dataType)
        
        bufOffset = c.sizeof(hdr)
        pocketOffset = bufOffset + hdr.bufSizeBytes
        
        bufSizeFlat = hdr.bufSizeBytes / np.dtype(nptype).itemsize
        pocketSizeFlat = hdr.pocketSizeBytes / np.dtype(nptype).itemsize
         
        # create numpy view objects pointing to the raw array
        self.__raw = raw
        self.__hdr = hdr
        self.__buf = np.frombuffer(raw, nptype, bufSizeFlat, bufOffset)\
                                          .reshape((-1, hdr.nChannels))
        self.__pocket = np.frombuffer(raw, nptype, pocketSizeFlat, pocketOffset)\
                                                   .reshape((-1, hdr.nChannels))
        
        # helper variables
        self.__nChannels = hdr.nChannels
        self.__bufSize = len(self.__buf)
        self.__pocketSize = len(self.__pocket)
        self.__nptype = nptype
    
    def __get_local_idx(self, startIdx, endIdx, nocheck=False):
        '''
        Checks for availability of requested chuck and returns local indices
        if the requested chunk is non-contiguous, uses a pocket, if the
        pocket is too small uses slow (copy) mode and issues a corresponding
        warning
        
        @param startIdx: chunk start index (in samples)
        @param endIdx:   chunk end index (in samples)
        @param nocheck:  whether to check availability
        
        @return: slice tuple or list of indices depending on the mode 
        
        '''
        
        # availability check
        e = self.check_availablility(startIdx, endIdx)
        if e and not nocheck: raise BufferError(e)
        
        chunkSize = endIdx - startIdx
        localStartIdx = startIdx % self.bufSize
        localEndIdx = endIdx % self.bufSize
        
        # whole buffer
        if localStartIdx == localEndIdx == 0:
            return localStartIdx, self.bufSize
        
        # contiguous chunk
        if (localEndIdx - localStartIdx) > 0:
            return localStartIdx, localEndIdx
        # split chunk
        else:
            # can't use pocket
            if chunkSize > self.pocketSize:
                self.logger.warning('buffer: slow mode')
                idxList = range(localStartIdx, self.bufSize)
                idxList.extend(range(localEndIdx))
                return idxList
            # using pocket
            else:
                if chunkSize != self.pocketSize:
                    self.logger.info('buffer: buffer pocket is larger than the window size')
                return localStartIdx, self.bufSize + localEndIdx

    def __write_buffer(self, data, idx):
        '''
        Writes data to buffer.
        
        @param data: properly shaped numpy array
        @param idx: local indices, returned by the __get_local_idx method
        
        '''
        # if the slicing (contiguous chunk)
        if len(idx) == 2 and (idx[1] - idx[0]) > 0:
            
            i, j = idx
            self.__buf[i:j] = data
            
            # copying needed parts to/from the pocket
            if i < self.bufSize <= j:
                self.__buf[:j - self.bufSize] = self.__pocket[:j - self.bufSize].copy()
            elif i < j <= self.pocketSize:
                self.__pocket[i:j] = self.__buf[i:j].copy()
            elif i < self.pocketSize <= j:
                self.__pocket[i:] = self.__buf[i:self.pocketSize].copy()
        
        # if the advanced indexing is used (the pocket is too small)             
        else:
            i, j = min(idx), max(idx)
            self.__buf[idx] = data
            self.__pocket[:] = self.__buf[:self.pocketSize]
        
    def __read_buffer(self, idx):       
        '''
        Reads the data from buffer
        
        @param idx: local indices, returned by the __get_local_idx method
        
        @return: numpy view on the requested chunk
        '''
        if len(idx) == 2 and (idx[1] - idx[0]) > 0:
            i, j = idx
            return self.__buf[i:j]
        else:
            return self.__buf[idx]
    
    def check_availablility(self, sampleStart, sampleEnd):
        '''
        Checks whether the requested data samples are available.
        
        @param sampleStart: first sample index (included)
        @param sampleEnd: last samples index (excluded)
        
        @return: 0 if the data is available
                 2 if (part of) the data is already overwritten
                 3 if (part of) the data is not yet in the buffer
                 
        '''
        if sampleEnd > self.nSamplesWritten:
            return 3 # data is not ready
        if (self.nSamplesWritten - sampleStart) > self.bufSize:
            return 2 # data is already erased
        
        return 0
    
    def get_data(self, sampleStart, sampleEnd, wprotect=True):
        '''
        Gets the data from the buffer. If possible, the data is returned in
        the form of a numpy view on the corresponding chunk (without copy).
        If the data is not available, rises an exception
         
        @param sampleStart: first sample index (included)
        @param sampleEnd:   last samples index (excluded)
        @param wprotect:    protect returned views from occasional writes
        
        @return: data chunk (numpy view or numpy array)
        
        '''
        idx = self.__get_local_idx(sampleStart, sampleEnd)
        data = self.__read_buffer(idx)
        data.setflags(write=not wprotect)
        return data
        
    def put_data(self, data):
        '''
        Pushes the data to the buffer
        
        @param data: properly shaped numpy array
        
        '''
        datashape = data.shape
        if len(datashape) != 1:
            if (data.shape[1] != self.nChannels):
                raise BufferError(4)
        else:
            datashape = (len(data), 1)
            if self.nChannels != 1:
                raise BufferError(4)

        sampleEnd = self.nSamplesWritten + len(data)
        sampleStart = (len(data) > self.bufSize) and (sampleEnd - self.bufSize) or self.nSamplesWritten
        
        idx = self.__get_local_idx(sampleStart, sampleEnd, nocheck=True)
        self.__write_buffer(data.reshape(datashape)[sampleStart - sampleEnd :], idx)
        import time; time.sleep(0.001)
        self.nSamplesWritten += len(data)


class datatypes():
    '''
    A helper class to interpret the typecode read from buffer header.
    To add new supported datatypes, add them to the 'type' dictionary
    
    '''
    types = {0:'float32',
             1:'int16'}
    @classmethod
    def get_code(cls, type):
        '''
        Gets buffer typecode given numpy datatype
        
        @param type: numpy datatype, string (e.g. 'float32')
        
        '''
        idx = cls.types.values().index(type)
        return cls.types.keys()[idx]
    @classmethod
    def get_type(cls, code):
        '''
        Gets numpy datatype given a buffer typecode
        
        @param code: typecode, integer (e.g. 0)
        
        '''
        return cls.types[code]
    
    
class BufferHeader(c.Structure):
    '''
    A ctypes structure describing the buffer header 
    
    '''
    _pack_ = 1
    _fields_ = [
                ('bufSizeBytes', c.c_ulong),
                ('pocketSizeBytes', c.c_ulong),
                ('dataType', c.c_uint),
                ('nChannels', c.c_ulong),
                ('nSamplesWritten', c.c_ulong)
                ]
    
class BufferError(Exception):
    '''
    Represents different types of buffer errors
    
    '''
    def __init__(self, code):
        '''
        Initializes a BufferError with given error code
        
        @param code: error code
        
        '''
        self.code = code
    def __str__(self):
        '''
        Prints the error
        
        '''
        if self.code == 1:
            return 'buffer is not initialized (error %s)' % repr(self.code)
        elif self.code in [2, 3]:
            return 'unable to get indices (error %s)' % repr(self.code)
        elif self.code == 4:
            return 'writing incompatible data (error %s)' % repr(self.code)
        else:
            return '(error %s)' % repr(self.code)




if __name__ == '__main__':
    buf1 = RingBuffer()
    buf2 = RingBuffer()
    
#    buf1.initialize(2, 10, 3)
    buf1.initialize(2, 15, 3)
    buf2.initialize_from_raw(buf1.raw)
    
    buf1.put_data(np.array([[1, 2], [3, 4]]))
    buf2.put_data(np.array([[5, 6], [7, 8]]))
    
    print buf1
    print buf2
    
    dat = buf2.get_data(1, 4)
    dat[0, 0] = 100
    
    print buf1
    print buf2
    
    
    
    
    
    
    
    

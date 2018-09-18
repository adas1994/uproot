#!/usr/bin/env python

# Copyright (c) 2017, DIANA-HEP
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 
# * Redistributions of source code must retain the above copyright notice, this
#   list of conditions and the following disclaimer.
# 
# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
# 
# * Neither the name of the copyright holder nor the names of its
#   contributors may be used to endorse or promote products derived from
#   this software without specific prior written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import struct

import uproot.write.sink.cursor

class TDirectory(object):
    def __init__(self, cursor, sink, fName, fNbytesKeys, fNbytesName, fSeekDir=100, fSeekParent=0, fSeekKeys=0):
        cursor.write_string(sink, fName)
        cursor.write_data(sink, b"\x00")

        self.fNbytesKeys = fNbytesKeys
        self.fNbytesName = fNbytesName
        self.fSeekDir = fSeekDir
        self.fSeekParent = fSeekParent
        self.fSeekKeys = fSeekKeys

        self.cursor = uproot.write.sink.cursor.Cursor(cursor.index)
        self.sink = sink
        self.update()

        cursor.skip(self._format1.size)

    def update(self):
        fVersion = 1005
        fDatimeC = 1573188772   # FIXME!
        fDatimeM = 1573188772   # FIXME!
        self.cursor.update_fields(self.sink, self._format1, fVersion, fDatimeC, fDatimeM, self.fNbytesKeys, self.fNbytesName, self.fSeekDir, self.fSeekParent, self.fSeekKeys)

    _format1 = struct.Struct(">hIIiiqqq")
    _format2 = struct.Struct(">i")

    def startkeys(self, tfile, allocationbytes=1024, growfactor=10):
        self.tfile = tfile
        self.allocationbytes = allocationbytes
        self.growfactor = growfactor

        self.fSeekKeys = self.tfile._fSeekFree
        self.fNbytesKeys = uproot.write.objects.TKey.TKey._keylen(b"TFile", self.tfile._filename, b"") + self._format2.size

        fillcursor = uproot.write.sink.cursor.Cursor(self.fSeekKeys + self.allocationbytes)
        fillcursor.update_data(self.sink, b"\x00")
        self.tfile._expandfile(fillcursor)

        self.keycursor = uproot.write.sink.cursor.Cursor(self.fSeekKeys)
        self.headkey = uproot.write.objects.TKey.TKey(self.keycursor, self.sink, b"TFile", self.tfile._filename,
                                                      fObjlen  = 4,
                                                      fSeekKey = self.fSeekKeys,
                                                      fNbytes  = self.fNbytesKeys)

        self.nkeys = 0
        self.nkeycursor = uproot.write.sink.cursor.Cursor(self.keycursor.index)
        self.keycursor.write_fields(self.sink, self._format2, self.nkeys)

        self.update()

    def addkey(self, fClassName, fName, fTitle=b"", fObjlen=0, fCycle=1, fSeekKey=100, fSeekPdir=0, fNbytes=None):
        if self.keycursor.index + uproot.write.objects.TKey.TKey._keylen(fClassName, fName, fTitle) > self.fSeekKeys + self.allocationbytes:
            self.allocationbytes *= self.growfactor

            olddata = self.sink.read(self.nkeycursor.index, self.keycursor.index)
            self.fSeekKeys = self.tfile._fSeekFree

            fillcursor = uproot.write.sink.cursor.Cursor(self.fSeekKeys + self.allocationbytes)
            fillcursor.update_data(self.sink, b"\x00")
            self.tfile._expandfile(fillcursor)

            self.keycursor = uproot.write.sink.cursor.Cursor(self.fSeekKeys)
            self.headkey = uproot.write.objects.TKey.TKey(self.keycursor, self.sink, b"TFile", self.tfile._filename,
                                                          fObjlen  = 4,
                                                          fSeekKey = self.fSeekKeys,
                                                          fNbytes  = self.fNbytesKeys)
            self.keycursor.write_data(self.sink, olddata)
            
        self.nkeys += 1
        self.nkeycursor.update_fields(self.sink, self._format2, self.nkeys)
        key = uproot.write.objects.TKey.TKey(self.keycursor, self.sink, fClassName, fName, fTitle=fTitle, fObjlen=fObjlen, fCycle=fCycle, fSeekKey=fSeekKey, fSeekPdir=fSeekPdir, fNbytes=fNbytes)

        self.headkey.fObjlen += key.fKeylen
        self.headkey.fNbytes += key.fKeylen
        self.headkey.update()

        self.fNbytesKeys += key.fKeylen
        self.update()

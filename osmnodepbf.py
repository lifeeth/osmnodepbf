# -*- coding: utf-8 -*-
# vim: ai ts=4 sts=4 et sw=4
"""
       Based on parsepbf.py by
       Chris Hill <osm@raggedred.net>

       This program is free software; you can redistribute it and/or modify
       it under the terms of the GNU General Public License as published by
       the Free Software Foundation; either version 3 of the License, or
       (at your option) any later version.

       This program is distributed in the hope that it will be useful,
       but WITHOUT ANY WARRANTY; without even the implied warranty of
       MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
       GNU General Public License for more details.

       You should have received a copy of the GNU General Public License
       along with this program. If not, see <http://www.gnu.org/licenses/>.
"""
__author__ = 'Praneeth Bodduluri'
__email__ = 'lifeeth[at]gmail.com'


import osmformat_pb2
import fileformat_pb2
from struct import unpack
import zlib

class Parser:
    """This class helps parse the pbf file for nodes with the specified tags"""

    def __init__(self,filename):
        """Initialize the class with the filename of the pbf you want to parse"""
        self.filename = filename
        self.fpbf=open(self.filename, "r")
        self.tags = {}
        self.nodes = []
        self.blobhead=fileformat_pb2.BlobHeader()
        self.blob=fileformat_pb2.Blob()
        self.hblock=osmformat_pb2.HeaderBlock()
        self.primblock=osmformat_pb2.PrimitiveBlock()
        self.membertype = {0:'node',1:'way',2:'relation'}
        if self.readPBFBlobHeader()==False:
            return False
        #read the blob
        if self.readBlob()==False:
            return False
        #check the contents of the first blob are supported
        self.hblock.ParseFromString(self.BlobData)
        for rf in self.hblock.required_features:
            if rf in ("OsmSchema-V0.6","DenseNodes"):
                pass
            else:
                raise TypeError("not a required feature %s" % rf )

    def readPBFBlobHeader(self):
        """Read a blob header, store the data for later"""
        size=self.readint()
        if size <= 0:
            return False

        if self.blobhead.ParseFromString(self.fpbf.read(size))==False:
            return False
        return True

    def readBlob(self):
        """Get the blob data, store the data for later"""
        size=self.blobhead.datasize
        if self.blob.ParseFromString(self.fpbf.read(size))==False:
            return False
        if self.blob.raw_size > 0:
            # uncompress the raw data
            self.BlobData=zlib.decompress(self.blob.zlib_data)
            #print "uncompressed BlobData %s"%(self.BlobData)
        else:
            #the data does not need uncompressing
            self.BlobData=raw
        return True

    def readNextBlock(self):
        """read the next block. Block is a header and blob, then extract the block"""
        # read a BlobHeader to get things rolling. It should be 'OSMData'
        if self.readPBFBlobHeader()== False:
            return False
        if self.blobhead.type != "OSMData":
            print "Expected OSMData, found %s"%(self.blobhead.type)
            return False
            # read a Blob to actually get some data
        if self.readBlob()==False:
            return False
        # extract the primative block
        self.primblock.ParseFromString(self.BlobData)
        return True

    def readint(self):
        """read an integer in network byte order and change to machine byte order. Return -1 if eof"""
        be_int=self.fpbf.read(4)
        if len(be_int) == 0:
            return -1
        else:
            le_int=unpack('!L',be_int)
            return le_int[0]

    def parse(self,tag = {},refresh = False):
        """This parses the pbf for nodes for the given tags"""
        if refresh:
			self.__init__(self.filename)
        while self.readNextBlock():
            for pg in self.primblock.primitivegroup:
                if len(pg.nodes)>0:
                    self.processNodes(pg.nodes,tag)
                if len(pg.dense.id)>0:
                    self.processDense(pg.dense,tag)
        return self.nodes

    def processNodes(self,nodes,tag={}):
        """This process the nodes adding the ones with the requested tag to a list"""
        NANO=1000000000L
        found_tag = False
        gran=float(self.primblock.granularity)
        latoff=float(self.primblock.lat_offset)
        lonoff=float(self.primblock.lon_offset)
        for nd in nodes:
            node = {}
            node["tag"] = []
            for i in range(len(nd.keys)):
                ky=nd.keys[i]
                vl=nd.vals[i]
                sky=self.primblock.stringtable.s[ky] #Key
                svl=self.primblock.stringtable.s[vl] #Value
                node["tag"].append({sky:svl})
                if sky in tag.keys():
                    if ( svl in tag.values() ) or ( tag.values()[0] == "*") :
                        found_tag = True
                if not len(tag):
                    try:
                        self.tags[node["sky"]].append(node["svl"])
                    except:
                        self.tags[node["sky"]] = [node["svl"]]
            if found_tag:
                node["nodeid"]=nd.id
                node["lat"]=float(nd.lat*gran+latoff)/NANO
                node["lon"]=float(nd.lon*gran+lonoff)/NANO
                node["vs"]=nd.info.version
                node["ts"]=nd.info.timestamp
                node["uid"]=nd.info.uid
                node["user"]=nd.info.user_sid
                node["cs"]=nd.info.changeset
                node["tm"]=ts*self.primblock.date_granularity/1000
                self.nodes.append(node)
                found_tag = False

    def processDense(self, dense, tag={}):
        """process a dense node block"""
        NANO=1000000000L
        found_tag = False
        #DenseNode uses a delta system of encoding os everything needs to start at zero
        lastID=0
        lastLat=0
        lastLon=0
        tagloc=0
        cs=0
        ts=0
        uid=0
        user=0
        gran=float(self.primblock.granularity)
        latoff=float(self.primblock.lat_offset)
        lonoff=float(self.primblock.lon_offset)
        for i in range(len(dense.id)):
            node={}
            node["tag"] = []
            lastID+=dense.id[i]
            lastLat+=dense.lat[i]
            lastLon+=dense.lon[i]
            lat=float(lastLat*gran+latoff)/NANO
            lon=float(lastLon*gran+lonoff)/NANO
            user+=dense.denseinfo.user_sid[i]
            uid+=dense.denseinfo.uid[i]
            vs=dense.denseinfo.version[i]
            ts+=dense.denseinfo.timestamp[i]
            cs+=dense.denseinfo.changeset[i]
            suser=self.primblock.stringtable.s[user]
            tm=ts*self.primblock.date_granularity/1000
            if tagloc<len(dense.keys_vals):  # don't try to read beyond the end of the list
                while dense.keys_vals[tagloc]!=0:
                    ky=dense.keys_vals[tagloc]
                    vl=dense.keys_vals[tagloc+1]
                    tagloc+=2
                    sky=self.primblock.stringtable.s[ky] #Key
                    svl=self.primblock.stringtable.s[vl] #Value
                    node["tag"].append({sky:svl})
                    if sky in tag.keys():
                        if ( svl in tag.values() ) or ( tag.values()[0] == "*") :
                            found_tag = True
                    if not len(tag):
                        try:
                            self.tags[node["sky"]].append(node["svl"])
                        except:
                            self.tags[node["sky"]] = [node["svl"]]
            tagloc+=1
            if found_tag:
                node["nodeid"]=lastID
                node["lon"]=lon
                node["lat"]=lat
                node["user"]=suser
                node["uid"]=uid
                node["version"]=vs
                node["changeset"]=cs
                node["time"]=tm
                self.nodes.append(node)
                found_tag = False

    def return_tags(self, refresh = False):
        """Returns all the keyvalue pairs in the tag list"""
        if len(self.tags) == 0 or refresh:
            self.parse()
        return self.tags



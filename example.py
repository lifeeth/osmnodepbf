#!/usr/bin/env python
from osmnodepbf import osmnodepbf

foo = osmnodepbf.Parser("india.osm.pbf")

#tags = foo.return_tags(refresh=True) # To see what tags are available

railway_stations = foo.parse({"railway":"station"})

print len(railway_stations)

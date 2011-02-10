This module helps to extract pois from osm pbf files with specified tags


Example usage
-------------

import osmnodepbf

foo = osmnodepbf.parser("some.osm.pbf") 

tags = foo.return_tags(refresh=True) # To see what tags are available

railways_stations = foo.parse({"railway":"station"})

#!/usr/bin/env python

## little example
## usage is: example.py osmfile.pbf

import sys
import osmnodepbf

foo = osmnodepbf.Parser(sys.argv[1])

## list all tags
#tags = foo.return_tags(refresh=False) # To see what tags are available
#for tag, keys in tags.items():
#    print tag, sorted(list(keys))

## filter some nodes with the given tag:
bus_stops = foo.parse({"highway":"bus_stop"})

print len(bus_stops)

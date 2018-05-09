#!/usr/bin/env python

import json
import sys

# Parse the JSON args
json_args = sys.argv[1]
args_dict = json.loads(json_args)

# Say hello
print "Hello world! Hello {name}!".format(name=args_dict['name'])

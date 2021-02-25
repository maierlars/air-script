#!/bin/env python3

import json
import sys
import parser

if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise RuntimeError("invalid parameter")
    file = sys.argv[1]

    with open(file, "r") as f:
        source = f.read()

        ast = parser.parse(source)

        # add type checks and code analysis here

        air = ast.airify()

        print(json.dumps(air, indent=2))

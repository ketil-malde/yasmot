#!/bin/bash 
#
# Tests are listed between the EOFs in the form:
# <sha1sum> <command>

status=0
while read sum cmd; do
    echo -n "$cmd ... "
    check=$($cmd | sha1sum | cut -f1 -d' ')
    if [ $check == $sum ]; then echo "passed."; else echo "FAILED!"; status=255; fi
    done\
	<<EOF
a2e9031bb4695be8d10167359c5d4d2e22527bb2 python3 parser.py tests/L.csv
e7bd2891fb15d75087cce4fed7b166d024199dba python3 stracks.py -s --track=0 tests/stereo*
4ed3070d277257fb8342f04f0da8aa4b5b273128 python3 stracks.py tests/lab2
a44dd9f46940f72af50b62b841b9ecb16e676467 python3 stracks.py --max_age 2 --time_pattern frame_\{:d\}.txt tests/lab2
EOF

exit $status

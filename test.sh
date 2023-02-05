#!/bin/bash 

status=0
while read sum cmd; do
    echo -n "$cmd ... "
    check=$($cmd | sha1sum | cut -f1 -d' ')
    if [ $check == $sum ]; then echo "passed."; else echo "FAILED!"; status=255; fi
done <<EOF
7c16489da9b182882d4722643e1394e8abfa183d python3 stracks.py -s --track=0 tests/stereo*
e4d3070d277257fb8342f04f0da8aa4b5b273128 python3 stracks.py tests/lab2
EOF

exit $status

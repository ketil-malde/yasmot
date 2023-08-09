#!/bin/bash 
#
# Tests are listed between the EOFs in the form:
# <sha1sum> <command>

# To generate explicit oututs:
# grep py...3 test.sh | while read s cmd; do echo $cmd; $(echo $cmd) > tests_out/$s.out; done

set -e -o pipefail

status=0
while read sum cmd; do
    echo -n "$cmd ... "
    check=$($cmd | sha1sum | cut -f1 -d' ')
    if [ $check == $sum ]; then
	echo "passed."
    else
	echo "FAILED!"
	$cmd > $sum.out
	status=255
    fi
    done\
	<<EOF
b198fb325a02cd2f38bbddaa01fe76ac0f2a745f python3 parser.py tests/L.csv
ed53fccebf70e9b200b48e94343e5bd14290fc31 python3 stracks.py -s --no-track --shape 1228,1027 tests/stereo1_Left.csv tests/stereo1_Right.csv
77db6356a284b4f61553acab2f3993e769dd93d6 python3 stracks.py tests/lab2
bc22a05c6283c68483bce2d5967eabc116a319f3 python3 stracks.py --max_age 2 --time_pattern frame_\{:d\}.txt tests/lab2
cbc79d570df3c7d586d344534864cef72ea7d4ba python3 stracks.py tests/error3.csv
2f1d0711a7e6c3206b4484d1a1983628e8c494c1 python3 stracks.py tests/lab2 --interpolate
8c9a0bdcc1e79d0666716646533aa8198b0932ef python3 stracks.py -c tests/consensus/y8x*
EOF

exit $status

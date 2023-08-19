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
ac8fd8659cf8bbd652886a6cf0106bd081b27ec6 python3 stracks.py tests/lab2
13d62f1ea1f67da480f8d8fa4d289e229386b978 python3 stracks.py --max_age 2 --time_pattern frame_\{:d\}.txt tests/lab2
19eaeb0b0dd5eb19bc3f78b59a14b5e49e2bbe1a python3 stracks.py tests/error3.csv
367ee297dfed7b4b46ca43fc5f847a14f2feccd5 python3 stracks.py tests/lab2 --interpolate
5db67348f697d29f66e5ed9700f364d779ae47ce python3 stracks.py -c tests/consensus/y8x*
EOF

exit $status

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
b198fb325a02cd2f38bbddaa01fe76ac0f2a745f python3 src/stracks/parser.py tests/L.csv
ed53fccebf70e9b200b48e94343e5bd14290fc31 python3 src/stracks/main.py -s --no-track --shape 1228,1027 tests/stereo1_Left.csv tests/stereo1_Right.csv
a3aae3bacbfbd418d243f0a7e09bf92dae9eab9a python3 src/stracks/main.py -s --shape 1228,1027 tests/stereo1_Left.csv tests/stereo1_Right.csv
1e856023ea79bc61decdb9499bb4f1e207b775eb python3 src/stracks/main.py tests/lab2
8c48b6ece4db0ea5d6925954e95214cf89fbaf22 python3 src/stracks/main.py --max_age 2 --time_pattern frame_\{:d\}.txt tests/lab2
2a14b4639ce0f30a3b6ab6b6f3084ed2cb8f455a python3 src/stracks/main.py tests/error3.csv
b7213abfdb7352c52975d2eeef9e28ace19927ec python3 src/stracks/main.py tests/lab2 --interpolate
64f0161579349b6e7a431e8aab69807bf18e7a18 python3 src/stracks/main.py -c tests/consensus/y8x*
EOF

exit $status


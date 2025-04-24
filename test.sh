#!/bin/bash 
#
# Tests are listed between the EOFs in the form:
# <sha1sum> <command>

# To generate explicit oututs:
# grep py...3 test.sh | while read s cmd; do echo $cmd; $(echo $cmd) > tests_out/$s.out; done

set -e -o pipefail

export PYTHONPATH=src

if [ -d venv ]; then
    source venv/bin/activate
else
    python3 -m venv venv
    source venv/bin/activate    
    pip install -r requirements.txt
    pip install .
fi

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
b198fb325a02cd2f38bbddaa01fe76ac0f2a745f python3 -m src.yasmot.parser tests/L.csv
ed53fccebf70e9b200b48e94343e5bd14290fc31 python3 -m src.yasmot.main -s --no-track --shape 1228,1027 tests/stereo1_Left.csv tests/stereo1_Right.csv
dd1c1a9132ab9d337182a30b9cccc9269e378c7b python3 -m src.yasmot.main -s --shape 1228,1027 tests/stereo1_Left.csv tests/stereo1_Right.csv
1e856023ea79bc61decdb9499bb4f1e207b775eb python3 -m src.yasmot.main tests/lab2
fe37f2b601046395e39f8a12f240ef3234f0d49d python3 -m src.yasmot.main --max_age 2 --time_pattern frame_\{:d\}.txt tests/lab2
2a14b4639ce0f30a3b6ab6b6f3084ed2cb8f455a python3 -m src.yasmot.main tests/error3.csv
ce0f1f7b14f06fe3a949eec98c9923e8265fb308 python3 -m src.yasmot.main tests/lab2 --interpolate
64f0161579349b6e7a431e8aab69807bf18e7a18 python3 -m src.yasmot.main -c tests/consensus/y8x*
EOF

exit $status


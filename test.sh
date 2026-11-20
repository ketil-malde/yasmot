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

mkdir -p .tests

status=0
while read sum cmd; do
    echo -n "$cmd ... "
    if check=$($cmd | tee .tests/$sum.out | sha1sum | cut -f1 -d' '); then
	if [ $check == $sum ]; then
	    echo -e "\033[32mpassed.\033[0m"
	else
	    echo -e "\033[31mFAILED!\033[0m"
	    status=255
	fi
    else
	    echo -e "\033[31m *** Program error *** \033[0m"
        status=255
    fi
    done\
	<<EOF
d9e5719f929ce1f4ae2cac843bf7c7b83a5b9807 python3 -m src.yasmot.parser tests/L.csv
e14570394c0f18f2b46bcdf616406fcca83833e7 python3 -m src.yasmot.main -s --no-track --shape 1228,1027 tests/stereo1_Left.csv tests/stereo1_Right.csv
7dee5a6ce7206f15ff989bd2379c53eb70f7542f python3 -m src.yasmot.main -s --shape 1228,1027 tests/stereo1_Left.csv tests/stereo1_Right.csv
e49b7ef985bbdb604a9822cf36cbde244ecdc10f python3 -m src.yasmot.main tests/lab2
e49b7ef985bbdb604a9822cf36cbde244ecdc10f python3 -m src.yasmot.main --max-age 2 --framelabel-pattern frame_\{:d\}.txt tests/lab2
b0c6a784d284f6e870bade1cf1f0e7949a8c3073 python3 -m src.yasmot.main tests/error3.csv
5173404842612b4711d8b4396eedbab42b155205 python3 -m src.yasmot.main tests/lab2 --interpolate --max-age 3
23f9e203fea1f638b437fe6382bbad50112aeae9 python3 -m src.yasmot.main -c tests/consensus/y8x*
46645a95038d975c252f0ce06b7e418a57560cbb python3 -m src.yasmot.main --max-age 2 --framelabel-pattern \{:d\} -s --shape 1228,1027 tests/stereo1_Left.csv tests/stereo1_Right.csv
7dee5a6ce7206f15ff989bd2379c53eb70f7542f python3 -m src.yasmot.main --max-age 0.2 --framelabel-pattern %Y%m%d%H%M%S%f --timestamp -s --shape 1228,1027 tests/stereo1_Left.csv tests/stereo1_Right.csv
8bcb71bdc4eec63c8552a8598e72130b25588d02 python3 -m src.yasmot.main -s --no-track -F 0.765 -D 60 --shape 1228,1027 tests/stereo1_Left.csv tests/stereo1_Right.csv
a88c48bc4f362a4bea7c1e133ab88cafc3aa826a python3 -m src.yasmot.main -s --no-track -F 0.765 -D 60 --fovx 94.4 --shape 1184,1000 tests/ST357left.csv tests/ST357right.csv
EOF

exit $status

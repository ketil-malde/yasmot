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
    fi
    done\
	<<EOF
b198fb325a02cd2f38bbddaa01fe76ac0f2a745f python3 -m src.yasmot.parser tests/L.csv
0efce5d5adc2591f273c72e342b21135411b5fe9 python3 -m src.yasmot.main -s --no-track --shape 1228,1027 tests/stereo1_Left.csv tests/stereo1_Right.csv
68842a31c5b80add4ba6904e9b1d9ddff9afb68c python3 -m src.yasmot.main -s --shape 1228,1027 tests/stereo1_Left.csv tests/stereo1_Right.csv
d7fad65ece11c6b66033b26491c2d2815d746758 python3 -m src.yasmot.main tests/lab2
d7fad65ece11c6b66033b26491c2d2815d746758 python3 -m src.yasmot.main --max-age 2 --framelabel-pattern frame_\{:d\}.txt tests/lab2
efaa15533e478ddf4db1fda103d1860f329561a4 python3 -m src.yasmot.main tests/error3.csv
ed08e7453c4031f9e798a98f963239833e270dd5 python3 -m src.yasmot.main tests/lab2 --interpolate --max-age 3
be5a9a80a1989dcd7bdbbe95c5dc2458d86ff13d python3 -m src.yasmot.main -c tests/consensus/y8x*
209de867e4c3d2ec4b194f449e576c0205e750ed python3 -m src.yasmot.main --max-age 2 --framelabel-pattern \{:d\} -s --shape 1228,1027 tests/stereo1_Left.csv tests/stereo1_Right.csv
68842a31c5b80add4ba6904e9b1d9ddff9afb68c python3 -m src.yasmot.main --max-age 0.2 --framelabel-pattern %Y%m%d%H%M%S%f --timestamp -s --shape 1228,1027 tests/stereo1_Left.csv tests/stereo1_Right.csv
0c663a0239a08ba4d4844db702b983d20a9ba4db python3 -m src.yasmot.main -s --no-track -F 0.73 -D 60 --shape 1228,1027 tests/stereo1_Left.csv tests/stereo1_Right.csv
EOF

exit $status

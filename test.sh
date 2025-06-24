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
6ec8812dff9a788e6453315e134ded7b4ec090c5 python3 -m src.yasmot.parser tests/L.csv
0ecef4d5feba6f4bca97028100b6b15b8773c1b2 python3 -m src.yasmot.main -s --no-track --shape 1228,1027 tests/stereo1_Left.csv tests/stereo1_Right.csv
3f3f539e15b7c759d7c6bc86d284481be83c816f python3 -m src.yasmot.main -s --shape 1228,1027 tests/stereo1_Left.csv tests/stereo1_Right.csv
3dccc135fc11beb20edccde43f671065103e0c33 python3 -m src.yasmot.main tests/lab2
3dccc135fc11beb20edccde43f671065103e0c33 python3 -m src.yasmot.main --max-age 2 --framelabel-pattern frame_\{:d\}.txt tests/lab2
b0c6a784d284f6e870bade1cf1f0e7949a8c3073 python3 -m src.yasmot.main tests/error3.csv
5173404842612b4711d8b4396eedbab42b155205 python3 -m src.yasmot.main tests/lab2 --interpolate --max-age 3
23f9e203fea1f638b437fe6382bbad50112aeae9 python3 -m src.yasmot.main -c tests/consensus/y8x*
457dcfe11cb4014a3db1a6c19fcede246c4ba3a3 python3 -m src.yasmot.main --max-age 2 --framelabel-pattern \{:d\} -s --shape 1228,1027 tests/stereo1_Left.csv tests/stereo1_Right.csv
3f3f539e15b7c759d7c6bc86d284481be83c816f python3 -m src.yasmot.main --max-age 0.2 --framelabel-pattern %Y%m%d%H%M%S%f --timestamp -s --shape 1228,1027 tests/stereo1_Left.csv tests/stereo1_Right.csv
c7d198a961a2f3c742964cc42fc137ea5bd48482 python3 -m src.yasmot.main -s --no-track -F 0.73 -D 60 --shape 1228,1027 tests/stereo1_Left.csv tests/stereo1_Right.csv
5c7eebe0928b6261263a33c95884f2efee93328a python3 -m src.yasmot.main -s --no-track -F 0.73 -D 60 --fovx 94.4 --shape 1228,1027 tests/ST357left.csv tests/ST357right.csv
EOF


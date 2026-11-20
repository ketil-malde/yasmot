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
d1466131ea38acb57cd5abc73d75031e5865ddfa python3 -m src.yasmot.main -s --no-track --shape 1228,1027 tests/stereo1_Left.csv tests/stereo1_Right.csv
87989c2c5aa74b18f81e31982e3c2542bef6bfb0 python3 -m src.yasmot.main -s --shape 1228,1027 tests/stereo1_Left.csv tests/stereo1_Right.csv
e49b7ef985bbdb604a9822cf36cbde244ecdc10f python3 -m src.yasmot.main tests/lab2
e49b7ef985bbdb604a9822cf36cbde244ecdc10f python3 -m src.yasmot.main --max-age 2 --framelabel-pattern frame_\{:d\}.txt tests/lab2
b0c6a784d284f6e870bade1cf1f0e7949a8c3073 python3 -m src.yasmot.main tests/error3.csv
5173404842612b4711d8b4396eedbab42b155205 python3 -m src.yasmot.main tests/lab2 --interpolate --max-age 3
23f9e203fea1f638b437fe6382bbad50112aeae9 python3 -m src.yasmot.main -c tests/consensus/y8x*
c5dd57fc8dcfc3a9d86b5e28abfede17abe24762 python3 -m src.yasmot.main --max-age 2 --framelabel-pattern \{:d\} -s --shape 1228,1027 tests/stereo1_Left.csv tests/stereo1_Right.csv
87989c2c5aa74b18f81e31982e3c2542bef6bfb0 python3 -m src.yasmot.main --max-age 0.2 --framelabel-pattern %Y%m%d%H%M%S%f --timestamp -s --shape 1228,1027 tests/stereo1_Left.csv tests/stereo1_Right.csv
df01523592ad2b99304d428f760d80a79f0f7c36 python3 -m src.yasmot.main -s --no-track -F 0.765 -D 60 --shape 1228,1027 tests/stereo1_Left.csv tests/stereo1_Right.csv
9dd1e6a3b353c621bf0d38b9abac7df970ac4a30 python3 -m src.yasmot.main -s --no-track -F 0.765 -D 60 --fovx 94.4 --shape 1184,1000 tests/ST357left.csv tests/ST357right.csv
EOF

exit $status

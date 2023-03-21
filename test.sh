#!/bin/bash 
#
# Tests are listed between the EOFs in the form:
# <sha1sum> <command>

# To generate explicit oututs:
# grep py...3 test.sh | while read s cmd; do echo $cmd; $(echo $cmd) > tests_out/$s.out; done

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
00f396809617e38bd1156f7d87f8eca42f531214 python3 stracks.py -s --track=0 tests/stereo1_Left.csv tests/stereo1_Right.csv
26e8bdf5352a792786d26b738d4d213bbcc369b2 python3 stracks.py tests/lab2
bc22a05c6283c68483bce2d5967eabc116a319f3 python3 stracks.py --max_age 2 --time_pattern frame_\{:d\}.txt tests/lab2
ebcdcfabf938ed5562528662a417fc8660fa21ca python3 stracks.py tests/error3.csv
EOF

exit $status

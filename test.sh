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
c92d1cb6c36068e531995ba0205a8926e97e6079 python3 stracks.py -s --track=0 tests/stereo1_Left.csv tests/stereo1_Right.csv
ba5954871e62f83447c4190bd269eab13944edad python3 stracks.py tests/lab2
bc22a05c6283c68483bce2d5967eabc116a319f3 python3 stracks.py --max_age 2 --time_pattern frame_\{:d\}.txt tests/lab2
bf33ed99f3852eef6e27d95e8a987d2359d6b92b python3 stracks.py tests/error3.csv
EOF

exit $status

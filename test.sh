#!/bin/bash 
#
# Tests are listed between the EOFs in the form:
# <sha1sum> <command>

status=0
while read sum cmd; do
    echo -n "$cmd ... "
    check=$($cmd | sha1sum | cut -f1 -d' ')
    if [ $check == $sum ]; then echo "passed."; else echo "FAILED!"; status=255; fi
    done\
	<<EOF
b198fb325a02cd2f38bbddaa01fe76ac0f2a745f python3 parser.py tests/L.csv
1b51a787a2ba431b97bb6b6c3d38468ce0898f11 python3 stracks.py -s --track=0 tests/stereo*
59b960bffddab667289cdda69e7dbdf755232a23 python3 stracks.py tests/lab2
379c7b25283c7ad3f145d2697de5a61065900f31 python3 stracks.py --max_age 2 --time_pattern frame_\{:d\}.txt tests/lab2
a7c8d17d408a86066e8f1a5bae955b8c412c16f1 python3 stracks.py tests/error3.csv
EOF

exit $status

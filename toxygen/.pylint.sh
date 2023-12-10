#!/bin/sh

ROLE=logging
/var/local/bin/pydev_pylint.bash -E -f text *py [a-nr-z]*/*py  >.pylint.err
/var/local/bin/pydev_pylint.bash *py [a-nr-z]*/*py  >.pylint.out

sed -e "/Module 'os' has no/d" \
    -e "/Undefined variable 'app'/d" \
    -e '/tests\//d' \
    -e "/Instance of 'Curl' has no /d" \
    -e "/No name 'path' in module 'os' /d" \
    -e "/ in module 'os'/d" \
    -e "/.bak\//d" \
	-i .pylint.err .pylint.out

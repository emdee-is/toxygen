#!/bin/sh

ROLE=logging
/var/local/bin/pydev_pylint.bash -E -f text *py [a-nr-z]*/*py  >.pylint.err
/var/local/bin/pydev_pylint.bash *py [a-nr-z]*/*py  >.pylint.out

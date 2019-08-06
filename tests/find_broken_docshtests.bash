#!/bin/bash

# Docshtests need to start with 4 spaces, so fail if a line looks almost like a
# docshtest but not quite.
# Invert the status code of grep.
! grep --perl-regexp '^  (\$|\s\$)' "$@"

#!/bin/bash

FILE=$1
CSV="${FILE%.*}".csv
TMPFILE=.tmp.$FILE

[ -n "$2" ] && CSV=$2

cat $FILE |\
    sed "s/], /,\n/g" |\
    sed "s/, /,/g" |\
    sed "s/null//g" |\
    sed "s/\[//g" |\
    sed "s/]//g" |\
    sed "s/{\"colnames\": //g" |\
    sed "s/\"fields\": //g" |\
    grep -v "SELECT" > $TMPFILE

mv $TMPFILE $CSV

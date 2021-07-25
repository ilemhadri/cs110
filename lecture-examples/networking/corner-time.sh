#!/bin/bash
# escape sequences can be found here:
# http://ascii-table.com/ansi-escape-sequences.php

ESC=
while [ 1 ]; do 
    # save cursor position
    printf "${ESC}[s"
    # move to top left
    printf "${ESC}[H"
    # white text, red background, bold
    printf "${ESC}[37;41;1m"
    ./time-client myth51 12345 
    # restore cursor position
    printf "${ESC}[u"
    sleep 0.2 
done

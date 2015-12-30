#!/bin/bash
# If webapp is not running, run it.

if [ -z "$(ps -ef | grep '[a]achaos.webapp')" ]
then
	cd ~/code/py/aachaos
	python3 -m aachaos.webapp 2>&1 > /dev/null & 
fi

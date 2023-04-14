#!/bin/bash
echo "Bot started! Use Ctrl + C to stop it!"

for (( ; ; ))
do
	python3 main.py && break
done


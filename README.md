# Multi-Core-Cache-Hierarchy-simulation
Please execute the following code to generate the address trace
-----------------------------------------------------------------------
make obj-intel64/addrtrace.so

../../../pin -t obj-intel64/addrtrace.so -o addr_prog1 -- ./prog1 8  

../../../pin -t obj-intel64/addrtrace.so -o addr_prog2 -- ./prog2 8

../../../pin -t obj-intel64/addrtrace.so -o addr_prog3 -- ./prog3 8

../../../pin -t obj-intel64/addrtrace.so -o addr_prog4 -- ./prog4 8

I assume that all the address traces are present inside Traces folder.

To run the simulator:

Run the following in terminal:

python3 main.py

Dependencies:

cache.py and all the trace files obtained on running addrtrace.cpp

Python modules: math, os, collections


To run all the trace files it takes 1hr 25 mins in our 2 core 1.7GHz system.
Prog 1 takes 1hr 15 min and Prog 2,Prog 3, Prog 4 combined takes 7-8mins in total.

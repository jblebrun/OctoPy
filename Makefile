.PHONY: test

test: 
	PYTHONPATH=. python3 test/programs.py
	PYTHONPATH=. python3 test/calc.py

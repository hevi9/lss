# development helpers for lndirs

NAME = "lss"

.PHONY: dist

help:
	@echo Targets:
	@echo "  dev         - install as development mode (symlinks)"
	@echo "  check       - check project"
	@echo "  clean       - clean generated build files"

dev: clean
	sudo apt-get -y install python3-pip
	pip3 install --user --upgrade pip
	pip3 install --user --upgrade flake8 pytest tox wheel
	pip3 install --user --process-dependency-links -e .

check:
	flake8 lss test setup.py
	tox

clean:
	rm -rfv $(shell find . \
	-name "build" -o \
	-name "dist" -o \
	-name "__pycache__" -o \
	-name "*~" -o \
	-name "*.bak" -o \
	-name "*.vpp~*" -o \
	-name "*.egg-info" -o \
	-name "*.eggs" -o \
	-name "*.cache" -o \
	-name ".tox")

dist: clean
	rm -rfv dist
	python3.5 setup.py bdist_wheel
	unzip -l dist/$(NAME)-*-py3-none-any.whl

checkdist: dist
	tox --installpkg dist/$(NAME)-*-py3-none-any.whl

# Copyright (C) 2015 Petri Heinilä, License LGPL 2.1

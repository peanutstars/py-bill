SHELL   := /bin/bash
VERSION := $(shell cat VERSION)
NULL    := /dev/null
STAMP   := $(shell date +%Y%m%d-%H%M)
ZIP_FILE:= $(shell basename $(PWD))-$(STAMP).zip

REQUIRE_TXT	:= requirements.txt


all: test


freeze:
	$(VIRTUAL_ENV)/bin/pip freeze > $(REQUIRE_TXT)

setup:
	$(VIRTUAL_ENV)/bin/pip install -r $(REQUIRE_TXT)

test:
	# python setup.py test
	PYTHONPATH=$(PROJECT_ROOT)/src python -m unittest discover -p "test*.py"

clean:
	@rm -rf build pysp.egg-info .eggs *.sqlite
	@(find . -name *.pyc -exec rm -rf {} \; 2>$(NULL) || true)
	@(find . -name __pycache__ -exec rm -rf {} \; 2>$(NULL) || true)

zip: clean
	@(7z a ../$(ZIP_FILE) ../$(shell basename $(PWD)))


.PHONY: test freeze setup clean zip

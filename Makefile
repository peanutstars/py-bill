SHELL   := /bin/bash
VERSION := $(shell cat VERSION)
NULL    := /dev/null
STAMP   := $(shell date +%Y%m%d-%H%M)
ZIP_FILE:= $(shell basename $(CURDIR))-$(STAMP).zip
APP_DIR	:= $(CURDIR)/dpkg/opt/psapps/pybill

REQUIRE_TXT	:= requirements.txt

REPO_HASH           := $(shell git rev-parse --short HEAD)
FULL_VERSION        := $(VERSION)-$(REPO_HASH)
VERSION_PY_FILE     := ./src/core/version.py
VERSION_HTML_FILE   := src/web/templates/parts/_version.html


all: test


freeze:
	$(VIRTUAL_ENV)/bin/pip freeze > $(REQUIRE_TXT)

setup:
	$(VIRTUAL_ENV)/bin/pip install -r $(REQUIRE_TXT)

test:
	# python setup.py test
	PYTHONPATH=$(CURDIR)/src DEBUG_PYTHON=1 python -m unittest discover -p "test*.py"

clean:
	@rm -rf build pysp.egg-info .eggs *.sqlite dpkg/opt
	@(find . -name *.pyc -exec rm -rf {} \; 2>$(NULL) || true)
	@(find . -name __pycache__ -exec rm -rf {} \; 2>$(NULL) || true)

zip: clean
	@(7z a ../$(ZIP_FILE) ../$(shell basename $(CURDIR)))

version:
	@(echo -e "\n\
	# This file is generated by automatically.\n\
	# \n\
	class Version:\n\
		@staticmethod\n\
		def get():\n\
			return \"$(FULL_VERSION)\"\n\
	" > $(VERSION_PY_FILE))
	@(echo -e "Ver $(FULL_VERSION)" > $(VERSION_HTML_FILE))



install:
	@[ ! -e "$(APP_DIR)" ] && mkdir -p $(APP_DIR)
	@cp -a ./src/* $(APP_DIR)
	@cp -a $(REQUIRE_TXT) $(APP_DIR)

dpkg: clean version install
	@[ -e "$(APP_DIR)/html5" ] && rm -rf "$(APP_DIR)/html5"
	@scripts/makedpkg.sh


.PHONY: test freeze setup clean zip version install dpkg

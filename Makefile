# Convenience Makefile for the TyphoonAE development environment.

ifndef PYTHON
	PYTHON := python2.5
endif

all: bin/buildout
	@bin/buildout -NU

bin/buildout: buildout.cfg
	$(PYTHON) bootstrap.py --distribute

cleanup:
	@echo "Cleaning up ..."
	- @epmd -kill
	@rm -rf var
	@mkdir -p var/log
	@rm -f etc/*.conf etc/ejabberd.cfg etc/celeryconfig.py*

update:
	@hg pull
	@hg update -v

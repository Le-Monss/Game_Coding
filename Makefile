ACME ?= acme
PYTHON ?= python3
PRG = build/catch-the-star.prg
D64 = build/catch-the-star.d64

.PHONY: all prg disk check test clean
all: disk check
prg: $(PRG)
disk: $(D64)

$(PRG): src/catch_the_star.asm
	mkdir -p build
	$(ACME) -f cbm -o $@ -l build/catch-the-star.labels -r build/catch-the-star.report $<

$(D64): $(PRG) tools/make_d64.py
	$(PYTHON) tools/make_d64.py $(PRG) $@

check: $(D64)
	$(PYTHON) tools/verify_build.py

# Optional machine-code tests need py65: python3 -m pip install py65==1.2.0
test: check
	$(PYTHON) -m unittest discover -s tests -v

clean:
	rm -f $(PRG) $(D64) build/catch-the-star.labels build/catch-the-star.report

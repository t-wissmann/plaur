A2X = a2x
ASCIIDOC = asciidoc
PYSRC = $(wildcard plaur/*.py)
GITVERSION = git-r$(shell git rev-list --count HEAD).$(shell git rev-parse --short HEAD)

.PHONY: doc clean

doc: plaur.1 plaur.html

plaur.1: plaur.txt
	$(A2X) -f manpage -a "manversion=plaur $(GITVERSION)" -a "date=`date +%Y-%m-%d`" $<

plaur.html: plaur.txt
	$(ASCIIDOC) -v $<

plaur.txt: plaur.py $(PYSRC) plaur_concept.txt
	./plaur.py asciidoc > $@ || (rm -f $@ ; false)

#sed 's,^[#] ,== ,' $< | sed 's,^[`][`][`]$,----,' > $@
plaur_concept.txt: plaur_concept.md
	cat $< \
		| sed 's,^# ,== ,' \
		| sed 's,^## ,=== ,' \
		| sed 's,^```$$,----,' \
		| sed 's,`,+,g' \
		> $@ || (rm -f $@ ; false)

clean:
	rm -f plaur.1 plaur.html plaur.txt plaur_concept.txt


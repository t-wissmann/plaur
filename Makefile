A2X = a2x
ASCIIDOC = asciidoc

.PHONY: doc clean

doc: plaur.1 plaur.html

plaur.1: plaur.txt
	$(A2X) -f manpage -a "date=`date +%Y-%m-%d`" $<

plaur.html: plaur.txt
	$(ASCIIDOC) -v $<

plaur.txt: plaur plaur_concept.txt
	./plaur asciidoc > $@ || (rm -f $@ ; false)

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


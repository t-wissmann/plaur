A2X = a2x
ASCIIDOC = asciidoc

.PHONY: doc

doc: plaur.1 plaur.html

plaur.1: plaur.txt
	$(A2X) -f manpage -a "date=`date +%Y-%m-%d`" $<

plaur.html: plaur.txt
	$(ASCIIDOC) $<

plaur.txt: plaur
	./plaur asciidoc > $@


presentation.pdf: presentation.tex beamerthemesesalcf.sty $(wildcard sesalcf-assets/*)
	latexmk -xelatex -shell-escape -use-make presentation.tex

all: presentation.pdf

clean:
	latexmk -CA || true
	rm -rf *.snm *.nav *.vrb *.pyg _minted-* *.config.minted *.data.minted .tools

.PHONY: clean all

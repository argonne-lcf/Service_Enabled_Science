presentation.pdf: presentation.tex beamerthemesesalcf.sty $(wildcard sesalcf-assets/*) $(wildcard figures/*)
	latexmk -xelatex -shell-escape -use-make presentation.tex

all: presentation.pdf

# Build inside the TeX Live container: no local TeX install needed.
# (The image is ~5 GB; the first run pulls it.)
TEXLIVE_IMAGE ?= texlive/texlive:latest

docker:
	docker run --rm -v "$(CURDIR)":/w -w /w --user "$$(id -u):$$(id -g)" \
	  -e HOME=/tmp $(TEXLIVE_IMAGE) make presentation.pdf

clean:
	latexmk -CA || true
	rm -rf *.snm *.nav *.vrb *.pyg _minted-* *.config.minted *.data.minted .tools

.PHONY: clean all docker

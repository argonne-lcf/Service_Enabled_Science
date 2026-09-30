SOURCES = presentation.tex beamerthemesesalcf.sty $(wildcard sesalcf-assets/*) $(wildcard figures/*) $(wildcard opencode-shots/*)

presentation.pdf: $(SOURCES)
	latexmk -xelatex -shell-escape -use-make presentation.tex

# Handout: every overlay collapsed onto one page, no \pause build-ups.
handout: handout.pdf

handout.pdf: $(SOURCES)
	latexmk -xelatex -shell-escape -use-make -jobname=handout \
	  -usepretex='\PassOptionsToClass{handout}{beamer}' presentation.tex

all: presentation.pdf

# Build inside the TeX Live container: no local TeX install needed.
# (The image is ~5 GB; the first run pulls it.)
TEXLIVE_IMAGE ?= texlive/texlive:latest
TARGET ?= presentation.pdf

docker:
	docker run --rm -v "$(CURDIR)":/w -w /w --user "$$(id -u):$$(id -g)" \
	  -e HOME=/tmp $(TEXLIVE_IMAGE) make $(TARGET)

clean:
	latexmk -CA || true
	latexmk -CA -jobname=handout presentation.tex || true
	rm -rf *.snm *.nav *.vrb *.pyg _minted-* *.config.minted *.data.minted .tools

.PHONY: clean all handout docker

# plaur - a pleasant AUR experience
plaur is a helper for installing packages from [Arch (Linux) User Repository
(AUR)](http://aur.archlinux.org) that uses the power of git.

For the concepts and the basic usage can be found in
[plaur_concept.md](plaur_concept.md) or in the man page.

## Installation
Since plaur is written in Python 3, it suffices to install its run-time
dependencies:

  - git
  - python (version 3)
  - pyalpm

Additional requirements for the documentation:

  - asciidoc
  - Makefile
  - sed

The man page `plaur.1` and HTML documentation `plaur.html` are created by:
```
$ make
```

[//]: # (vim: tw=80)

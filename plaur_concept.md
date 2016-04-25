# USING PLAUR
## The Concept
The main idea is to build a _plaur repository_ which is your custom version of
the Arch User Repository (AUR). In your plaur repository you can trust the
contents of all packages, in particular the `PKGBUILD` files.

There are two ways of filling the plaur repository with (new) packages:

  - By adding a new package from the AUR. But before you can actually build
    that new package, you have to `verify` it first. That means: after looking
    at the `PKGBUILD` (and other shipped files), you tell the plaur repository
    that the package does not contain malicious code.
  - By updating an existing package in your plaur repository to a new version
    from the AUR. Again, you have to `verify` the new version. But now, `plaur`
    only shows you the differences to the last verified version, so you do not
    need to go through all the `PKGBUILD` again!

All the information  is automatically saved in a *git(1)* repository. So you
can easily synchronize the AUR packages between various arch linux systems.

## First Steps
Similar to git, create a new directory with the name of you choice, enter it,
and then type:
```
$ plaur init
```
This will initialize a git repository and create empty configuration files
`plaur.ini` and `packages.ini`. The main information -- which packages you have
added and which version you have verified -- is saved in the `packages.ini` and
is tracked by git.

## Adding a new package
In order to import a new package (e.g. named _mypackagename_) from the AUR,
type:
```
$ plaur add mypackagename
```
This will do nothing but saving in the `packages.ini` that you are interested
of that package. The following command downloads the package content (in fact
downloads and updates all package contents).
```
$ plaur fetch
```
This will result in a new directory for the new package, containing its
git-repository from the AUR. You have multiple ways for reviewing its content.
The easiest way is:
```
$ plaur verify
```
It will show all the unverified package contents and asks you whether it looks
trustworthy. If all the dependencies of the new packages are met, you can
directly build it. But in general (or in order to be sure are that all
dependencies are there), you can perform a dependency check:
```
$ plaur depadd
```
It will check if there are any unresolved dependencies. It will prompt for
installing them from the repositories via pacman, if possible. The still
unresolved dependencies are added to your plaur repository, via `plaur add`.
Just like before, you need to download and verify those via
```
$ plaur fetch && plaur verify
```
You can iterate that whole proces of 
```
$ plaur depadd && plaur fetch && plaur verify
```
in order to add the dependencies' dependencies, and so on, until no new
dependencies arise.

Finally, you can start building the packages, using `plaur build`.
Unfortunately, it is not yet implemented to build all the packages in
_dependency order_.




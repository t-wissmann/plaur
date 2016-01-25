#!/bin/bash -e

main() {
case "$1" in
    init)
        git init
        check_directories
        ;;
    add)
        check_directories
        shift
        add_aur "$@"
        ;;
    diff)
        git diff --cached
        ;;
    verify)
        check_directories
        shift
        verify "$@"
        ;;
    *)
        error "unknown command \"$1\""
        print_help >&2
        ;;
esac
}

print_help() {
cat <<EOF
Usage: $0 SUBCOMMAND ARGS

where SUBCOMMAND is of the following:
EOF
}

::() {
    echo -e "\e[1;31m:: \e[1;37m$*\e[0m"
}

ask() {
    local input
    read -s -r -n 1 -p "$* [yN]" input || true
    case "$input" in
        Y|y) return 0 ;;
        *) return 1 ;;
    esac
}

error() {
    echo "$0 Error: $*" >&2
}

# Check that we have a git repository and the important directories
check_directories() {
    git_root=$(git rev-parse --show-toplevel)
    aur_directory="$git_root/aur"
    mkdir -p "$aur_directory"
}

# install a new package
add_aur() {
    git_url="https://aur.archlinux.org/${1}.git"
    git clone "$git_url" "$aur_directory/${1}"
    echo "" > "$aur_directory/${1}.head"
    git add "$aur_directory/${1}.head"
    echo "${1}/" >> "$aur_directory/.gitignore"
    git add "$aur_directory/.gitignore"
    git ca -m "Add $aur_directory/${1}"
    #cp "$aur_directory/$1/.git/refs/heads/master" "
    #git_at "$1" rev-parse HEAD > "$aur_directory/${1}.head"
}

git_at() {
    local d="$1"
    shift
    GIT_DIR="$d/.git" GIT_WORK_TREE="$d" git "$@"
}

is_verified() {
    git_at "$aur_directory/$1" rev-parse HEAD \
        | diff - "$aur_directory/$1.head" >/dev/null
}

verify() {
    for p in "$@" ; do
        if is_verified "$p" ; then
            :: "$p already verified"
            continue
        else
            last_verified="$(< $aur_directory/$1.head)"
            :: "Showing changes since the last verified version"
            if [[ -n "$last_verified" ]] ; then
                git_at "$aur_directory/$p" diff "$last_verified" "HEAD"
            else
                git_at "$aur_directory/$p" ls-files |
                    while read line ; do
                        echo -e "\e[1;32m====> \e[1;37m $line \e[1;32m<====\e[0m"
                        cat "$aur_directory/$p/$line"
                    done | less -R
            fi
            if ask "Verify the above source package?" ; then
                git_at "$aur_directory/$p" rev-parse HEAD \
                    > "$aur_directory/$p.head"
                git add "$aur_directory/$p.head"
                git commit -m "Verify $p"
            fi
        fi
    done
}

main "$@"

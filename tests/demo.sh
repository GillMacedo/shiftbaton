#!/bin/sh
# Runs three made-up shifts in a throwaway repo, through the stand-in claude in tests/fakes.
set -e
root=$(pwd)
work=$(mktemp -d)
git -C "$work" init -q
mkdir -p "$work/loop"
cp loop/prompt.md "$work/loop/prompt.md"
cp .gitignore "$work/.gitignore"
git -C "$work" add .
git -C "$work" -c user.name=Demo -c user.email=demo@example.com commit -q -m Start
PATH="$root/tests/fakes:$PATH" FAKE_SCRIPT=commit,commit,done python3 loop/loopctl.py --root "$work" run --max-usd 5

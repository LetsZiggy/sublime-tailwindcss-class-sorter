#!/bin/bash

sed -i "s/VERSION = \"[0-9]\+.[0-9]\+.[0-9]\+\"/VERSION = \"${1}\"/g" boot.py && \
sed -i "s/VERSION = \"[0-9]\+.[0-9]\+.[0-9]\+\"/VERSION = \"${1}\"/g" tailwindcss-class-sorter.py && \
git add . && \
echo "${1}" | { read version; echo "${version}" | sed 's/\.[0-9]\+$/\.\*/g' | { read edited; git commit -m "feat: tailwindcss-class-sorter ${edited} support"; }; } && \
echo "${1}" | { read version; echo "${version}" | sed 's/\.[0-9]\+$/\.\*/g' | { read edited; git tag -a "v${version}" -m "tailwindcss-class-sorter ${edited} support"; }; }

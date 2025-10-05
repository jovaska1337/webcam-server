#!/bin/bash

path="$(realpath "$(dirname "${BASH_SOURCE[0]}")")"

# ensure venv exists
if [[ ! -d "${path}/venv" ]]; then
	python -m venv "${path}/venv" || exit 1
	"${path}/venv/bin/pip" install -r "${path}/requirements.txt" || exit 1
fi

# run program
cd "$path" && exec "${path}/venv/bin/python" "${path}/main.py"

#!/usr/bin/env bash

watchmedo auto-restart --directory=./src --pattern=*.py --recursive --ignore-patterns=venv -- "$@"

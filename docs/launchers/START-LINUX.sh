#!/bin/bash
# Starts The Kill-Day Almanac from this drive on another Linux computer.
cd "$(dirname "$0")" || exit 1
exec tools/linux-amd64/killday-serve --library . --open

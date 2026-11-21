#!/bin/bash
# Starts The Kill-Day Almanac from this drive. Close this window to stop it.
cd "$(dirname "$0")" || exit 1
case "$(uname -m)" in
    arm64) binary=tools/darwin-arm64/killday-serve ;;
    *) binary=tools/darwin-amd64/killday-serve ;;
esac
echo "Starting The Kill-Day Almanac. Keep this window open while you use it."
exec "$binary" --library . --open

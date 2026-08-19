#!/usr/bin/env bash
set -euo pipefail

driver_directory="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
output_directory="${1:-$driver_directory}"
sources=(driver.s clock.s channels.s)

for tool in ca65 ld65; do
    if ! command -v "$tool" > /dev/null 2>&1; then
        echo "$tool is missing: the player driver is built with cc65 (sudo apt install cc65)" >&2
        exit 1
    fi
done

work_directory="$(mktemp -d)"
trap 'rm -rf "$work_directory"' EXIT

objects=()
for source in "${sources[@]}"; do
    object="$work_directory/${source%.s}.o"
    ca65 --cpu 6502 --include-dir "$driver_directory" -o "$object" "$driver_directory/$source"
    objects+=("$object")
done

ld65 \
    --config "$driver_directory/nsf.cfg" \
    --mapfile "$work_directory/driver.map" \
    -Ln "$work_directory/driver.labels" \
    -o "$output_directory/driver.bin" \
    "${objects[@]}"

address() {
    local symbol="$1"
    local value
    value="$(awk -v name=".$symbol" '$3 == name { print $2 }' "$work_directory/driver.labels")"
    if [[ -z "$value" ]]; then
        echo "the linker reported no address for $symbol" >&2
        exit 1
    fi
    echo $((16#$value))
}

load_address="$(address __PRG_START__)"
init_address="$(address nsf_init)"
play_address="$(address nsf_play)"
song_address="$(address song_data)"
driver_length="$(wc -c < "$output_directory/driver.bin")"

if ((song_address - load_address != driver_length)); then
    echo "the song starts at $((song_address - load_address)) bytes and the driver is $driver_length long" >&2
    exit 1
fi

printf 'driver.bin  %d bytes, $%04X-$%04X\n' "$driver_length" "$load_address" "$((song_address - 1))"
printf 'init        $%04X\n' "$init_address"
printf 'play        $%04X\n' "$play_address"
printf 'song        $%04X\n' "$song_address"

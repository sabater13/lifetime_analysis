#!/bin/bash

INPUT_DIR="/global/cfs/cdirs/dune/www/data/2x2/nearline_run3/flowed_charge/Operations/20261103-LowIntensityBeam_LRSselfTrigger_Physics"

OUTPUT_DIR="/pscratch/sd/e/esabater/2x2_lifetime/lifetime_analysis"

mkdir -p "$OUTPUT_DIR"

count=0

find "$INPUT_DIR" -maxdepth 1 -type f -name "packet-*.FLOW.hdf5" | sort |
while read -r file; do

    filename=$(basename "$file")

    # Extract timestamp: YYYY_MM_DD_HH_MM_SS
    timestamp=$(echo "$filename" | grep -oE '[0-9]{4}_[0-9]{2}_[0-9]{2}_[0-9]{2}_[0-9]{2}_[0-9]{2}')

    # Select files after November 3, 2026, 21:00 CST
    if [[ "$timestamp" > "2026_11_03_21_00_00" ]]; then
        #echo "$file"
    #fi # remove if running over all

    # run over the last few files
    #done | tail -n 10 | while read -r file; do

        filename=$(basename "$file")

        echo "Processing: $filename"

        python3 lifetime_quick_fit.py "$file" \
            --output-plot "$OUTPUT_DIR/lifetime_quickfits_with_new_event_builder/plots/${filename}.png" \
            --output-json "$OUTPUT_DIR/lifetime_quickfits_with_new_event_builder/jsons/${filename}.json"

        ((count++))
        if ((count >= 10)); then
            break
        fi

    fi # comment out if running over the last few files

done
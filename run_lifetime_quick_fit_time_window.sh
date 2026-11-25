#!/bin/bash

INPUT_DIR="/global/cfs/cdirs/dune/www/data/2x2/nearline_run3/flowed_charge/Operations/20261103-LowIntensityBeam_LRSselfTrigger_Physics"

OUTPUT_DIR="/pscratch/sd/e/esabater/2x2_lifetime/lifetime_analysis/lifetime_quickfits_20261104_05-09"

mkdir -p "$OUTPUT_DIR/plots"
mkdir -p "$OUTPUT_DIR/jsons"

# Time window: November 4, 2026, 05:00–09:00
START_TIME="2026_11_04_05_00_00"
END_TIME="2026_11_04_09_00_00"

selected_files=()

while IFS= read -r -d '' file; do

    filename=$(basename "$file")

    # Extract timestamp: YYYY_MM_DD_HH_MM_SS
    timestamp=$(echo "$filename" | grep -oE '[0-9]{4}_[0-9]{2}_[0-9]{2}_[0-9]{2}_[0-9]{2}_[0-9]{2}')

    # Select files between 05:00 and 09:00
    if [[ -n "$timestamp" && "$timestamp" > "$START_TIME" || "$timestamp" == "$START_TIME" ]]; then

        if [[ "$timestamp" < "$END_TIME" ]]; then
            echo "Selected: $filename"
            selected_files+=("$file")
        fi

    fi

done < <(find "$INPUT_DIR" -maxdepth 1 -type f -name "packet-*.FLOW.hdf5" -print0 | sort -z)


echo ""
echo "=========================================="
echo "Total files selected: ${#selected_files[@]}"
echo "=========================================="

if (( ${#selected_files[@]} == 0 )); then
    echo "ERROR: No files found in the requested time window."
    exit 1
fi


echo ""
echo "Running pooled lifetime fit..."

python3 lifetime_quick_fit.py "${selected_files[@]}" \
    --output-plot "$OUTPUT_DIR/plots/lifetime_20261104_05-09.png" \
    --output-json "$OUTPUT_DIR/jsons/lifetime_20261104_05-09.json"

echo ""
echo "Done!"
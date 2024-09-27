#!/bin/sh

# Download large file from Google Drive
URL="https://drive.usercontent.google.com/download?id=1U4bFDfcix7UKhCBBRQIgNFEQCFB9uG6P&export=download&confirm=t"
TARGET_DIR="data"
# Create the target directory if it doesn't exist
mkdir -p "$TARGET_DIR"
# Download the file
curl -o "$TARGET_DIR/180724_dashboard_hexs.parquet" "$URL"

# Run the server
gunicorn app:server
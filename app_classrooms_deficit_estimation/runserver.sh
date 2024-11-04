#!/bin/sh

# Create the target directory if it doesn't exist
TARGET_DIR="data"
mkdir -p "$TARGET_DIR"

# Download large file from Google Drive
URL="https://drive.usercontent.google.com/download?id=1U4bFDfcix7UKhCBBRQIgNFEQCFB9uG6P&export=download&confirm=t&uuid=bb707ce2-cd98-4e2f-8a75-d8bf29ae2810&at=AENtkXZL8aofRGksI2_gRIUaZjrS%3A1730686851830"
curl "$URL" -o "$TARGET_DIR/180724_dashboard_hexs.parquet"

# Run the server
gunicorn app:server

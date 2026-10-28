#!/bin/sh
cd "$(dirname "$0")" || exit 1
python3 setup_ai.py --backend cpu

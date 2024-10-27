#!/bin/bash

TARGET_PATH="/home/okumnas/project/python/NatteeScraper-clone"
CURR_PATH=$(pwd)

echo "Run from path: $CURR_PATH."

# Check if TARGET_PATH exists
if [ ! -d "$TARGET_PATH" ]; then
  echo "Error: TARGET_PATH does not exist: $TARGET_PATH"
  exit 1
fi

# Check if virtual environment exists
if [ ! -f "$TARGET_PATH/venv/bin/activate" ]; then
  echo "Error: Virtual environment not found in: $TARGET_PATH/venv"
  exit 1
fi

# Activate virtual environment
source "$TARGET_PATH/venv/bin/activate" || {
  echo "Failed to activate virtual environment"
  exit 1
}

# Check if main.py exists
if [ ! -f "$TARGET_PATH/main.py" ]; then
  echo "Error: main.py not found in $TARGET_PATH"
  deactivate
  exit 1
fi

# Navigate to current path
cd "$CURR_PATH" || {
  echo "Failed to navigate to $CURR_PATH"
  deactivate
  exit 1
}

# Run the Python script

if [ "$1" == "genfile" ]; then
  python "$TARGET_PATH/main.py" --generate-input-file "$CURR_PATH" --link-erunner
else
  python "$TARGET_PATH/main.py"
fi

if [ $? -ne 0 ]; then
  echo "Python script failed to run"
  deactivate
  exit 1
fi

# Deactivate virtual environment
deactivate

#!/bin/bash

source venv/bin/activate

export TESTING=1
pytest -n 0 --setup-only
pytest -n 8

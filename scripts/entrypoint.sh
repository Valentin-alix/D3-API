#!/bin/bash

poetry run uvicorn --workers 1 --host 0.0.0.0 main:app
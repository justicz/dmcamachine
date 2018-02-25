#!/bin/bash

set -f
set -e
set -u
set -o pipefail
set -x

# If we're already running, stop
docker kill dmcarunning || true

# Build the image
docker build -t dmcamachine .

# What port should I run on?
PRT=51086

# What is my ip?
HSTIP=127.0.0.1

# Change these to the appropriate directories for persistent storage
TMP_DOWNLOAD_DIR=/srv/http/dmcamachine/tmptorrents
DOWNLOAD_DIR=/srv/http/dmcamachine/torrents

# Make sure they exist on the host
mkdir -p $TMP_DOWNLOAD_DIR $DOWNLOAD_DIR

# Run the container
docker run -d -v $TMP_DOWNLOAD_DIR:/dmca/static/tmp -v $DOWNLOAD_DIR:/dmca/static/torrents -p $HSTIP:$PRT:80 -it --rm --name dmcarunning dmcamachine


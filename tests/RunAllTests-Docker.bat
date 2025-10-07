#!/bin/bash

set -e

chrome --version
chromedriver -v
node -v

# Runs all API 2 Selenium Webdriver automated tests in Docker container. Takes about 14 minutes to run.
echo Running API 2 Tests

val=$(node station.js)
echo $val
if [[ "$val" == *"failed."* ]]; then
  exit 1
fi

val=$(node vessels.js)
echo $val
if [[ "$val" == *"failed."* ]]; then
  exit 1
fi

val=$(node cruise.js)
echo $val
if [[ "$val" == *"failed."* ]]; then
  exit 1
fi

val=$(node cast.js)
echo $val
if [[ "$val" == *"failed."* ]]; then
  exit 1
fi

val=$(node niskin.js)
echo $val
if [[ "$val" == *"failed."* ]]; then
  exit 1
fi

val=$(node bottle.js)
echo $val
if [[ "$val" == *"failed."* ]]; then
  exit 1
fi

val=$(node metadata.js)
echo $val
if [[ "$val" == *"failed."* ]]; then
  exit 1
fi

val=$(node event.js)
echo $val
if [[ "$val" == *"failed."* ]]; then
  exit 1
fi

val=$(node underway.js)
echo $val
if [[ "$val" == *"failed."* ]]; then
  exit 1
fi

val=$(node hplc.js)
echo $val
if [[ "$val" == *"failed."* ]]; then
  exit 1
fi

val=$(node nut.js)
echo $val
if [[ "$val" == *"failed."* ]]; then
  exit 1
fi

val=$(node chl.js)
echo $val
if [[ "$val" == *"failed."* ]]; then
  exit 1
fi

val=$(node cruise_track.js headless local)
echo $val
if [[ "$val" == *"failed."* ]]; then
  exit 1
fi

val=$(node upload.js headless local)
echo $val
if [[ "$val" == *"failed."* ]]; then
  exit 1
fi

exit 0
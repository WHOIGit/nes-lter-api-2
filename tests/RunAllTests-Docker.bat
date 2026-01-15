#!/bin/bash

set -e

chrome --version
chromedriver -v
node -v

# If running in docker on command line, run command to create /data/token.txt in api service.

#docker compose -f docker-compose-testing.yml exec -T api python manage.py shell -c "from django.contrib.auth #import get_user_model; from rest_framework.authtoken.models import Token; from pathlib import Path; #U=get_user_model(); u,_=U.objects.get_or_create(username='admin'); t,_=Token.objects.get_or_create(user=u); #Path('/data/token.txt').write_text(t.key)"

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

val=$(node landing.js headless local)
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
FROM python:3.12-slim

# geospatial libraries
RUN apt-get update && apt-get install -y binutils libproj-dev libgdal-dev libpoppler-dev

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/WHOIGit/amplify-storage-utils.git /app/amplify-storage-utils
RUN pip install hatch
WORKDIR /app/amplify-storage-utils
RUN hatch build
RUN pip install dist/*.whl
ENV PYTHONPATH="/app/amplify-storage-utils:$PYTHONPATH"

WORKDIR /build
COPY requirements.txt .

RUN pip install -r requirements.txt

WORKDIR /api
COPY ./api .

CMD python manage.py runserver
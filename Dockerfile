FROM python:3.12-slim-bookworm

# geospatial libraries
RUN apt-get update && apt-get install -y binutils libproj-dev libgdal-dev libpoppler-dev git

WORKDIR /app

WORKDIR /build
COPY requirements.txt .

RUN pip install -r requirements.txt

WORKDIR /api
COPY ./api .

RUN python manage.py collectstatic --noinput

CMD ["python", "manage.py", "runserver"]

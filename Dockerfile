FROM python

# geospatial libraries
RUN apt-get update && apt-get install -y binutils libproj-dev libgdal-dev libpoppler-dev

WORKDIR /build
COPY requirements.txt .

RUN pip install -r requirements.txt

WORKDIR /api
COPY ./api .

CMD python manage.py runserver
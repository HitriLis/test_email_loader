FROM python:3.10-bullseye

# set env variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /var/app/

RUN apt-get update && apt-get install -y wget
RUN apt-get install -y python3-dev gcc libc-dev libffi-dev
RUN apt-get -y install libpq-dev gcc

# install dependencies
COPY app/requirements.txt /var/app/
RUN pip install --upgrade pip
RUN pip install -r requirements.txt
# copy project
COPY --chown=www-data:www-data app /var/app/
RUN chown -R www-data:www-data /var/app/

EXPOSE 8000
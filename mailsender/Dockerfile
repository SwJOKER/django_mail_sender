FROM python:2.7-alpine

# set work directory
WORKDIR /usr/src/mailsender

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# install dependencies
RUN apk update \
    && apk add postgresql-dev gcc python2-dev musl-dev postgresql-client

RUN pip install --upgrade pip
COPY ./requirements.txt .
RUN pip install -r requirements.txt

COPY ./entrypoint.sh .
# sed for fix windows style line endings
RUN sed -i 's/\r$//g' ./entrypoint.sh
RUN chmod +x ./entrypoint.sh

# copy project
#COPY . .

ENTRYPOINT ["/usr/src/mailsender/entrypoint.sh"]
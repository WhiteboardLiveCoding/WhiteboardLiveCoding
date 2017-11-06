FROM tiangolo/uwsgi-nginx-flask:python3.6
ARG ARG_BLOB_ACCOUNT
ARG ARG_BLOB_KEY

ENV BLOB_ACCOUNT $ARG_BLOB_ACCOUNT
ENV BLOB_KEY $ARG_BLOB_KEY

COPY ./WLC /app/main
COPY ./uwsgi.ini /app/uwsgi.ini
COPY ./requirements.txt /app/requirements.txt
WORKDIR /app
RUN pip install -r requirements.txt

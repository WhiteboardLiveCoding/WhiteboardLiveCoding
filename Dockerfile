FROM tiangolo/uwsgi-nginx-flask:python3.6
ARG ARG_BLOB_ACCOUNT
ARG ARG_BLOB_KEY
ARG ARG_HACKER_RANK_KEY

ENV BLOB_ACCOUNT $ARG_BLOB_ACCOUNT
ENV BLOB_KEY $ARG_BLOB_KEY
ENV HACKER_RANK_KEY $ARG_HACKER_RANK_KEY

COPY ./WLC /app/main
COPY ./uwsgi.ini /app/uwsgi.ini
COPY ./requirements.txt /app/requirements.txt
WORKDIR /app
RUN pip install --upgrade -r requirements.txt

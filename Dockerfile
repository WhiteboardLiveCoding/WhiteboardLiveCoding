FROM tiangolo/uwsgi-nginx-flask:python3.6

COPY ./WLC /app/main
COPY ./uwsgi.ini /app/uwsgi.ini
COPY ./requirements.txt /app/requirements.txt
WORKDIR /app
RUN pip install -r requirements.txt

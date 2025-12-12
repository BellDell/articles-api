FROM python:3.11-slim

ENV VIRTUAL_ENV=/usr/local
RUN pip install \
    flask \
    flask-sqlalchemy \
    pytest

WORKDIR /home/practical
COPY . .
CMD bash

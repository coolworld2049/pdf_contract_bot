FROM python:3.11.7-slim-bullseye as pdf_contract_bot

RUN pip install poetry==1.4.2

WORKDIR /app

COPY pyproject.toml poetry.lock /app/

RUN poetry config virtualenvs.create false

RUN poetry install -n

COPY . /app/
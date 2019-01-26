# Tantalus
# Version 1.0

FROM python:2.7.15

ENV PYTHONUNBUFFERED 1

RUN mkdir /tantalus

WORKDIR /tantalus

ADD . /tantalus/

RUN pip install --upgrade pip && pip install -r requirements.txt --ignore-installed

EXPOSE 8000

ENTRYPOINT ["python", "manage.py"]

CMD ["runserver", "8000"]
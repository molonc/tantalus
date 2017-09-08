# Tantalus Sequence File Manager

## Asyncronous transfers using celery

### Setup

Make sure you have [Rabbit-MQ](https://www.rabbitmq.com/) installed.  On OSX:

```
brew install Rabbit-MQ
```

Install django celery with pip:

```
pip install django-celery
```

### Running

The tantalus module must be importable, the easiest way is to set your PYTHONPATH.

```
export PYTHONPATH=/home/amcpherson/tantalus
```

Start the celery worker, for instance on rocks:

```
celery -A tantalus worker -l DEBUG --queues rocks -c 4
```

### Tests

To run the tests, type:

```
python manage.py test tantalus/tests/
```
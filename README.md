# Tantalus Sequence File Manager

## Asyncronous transfers using celery

### Setup

Make sure you have (Rabbit-MQ)[https://www.rabbitmq.com/] installed.  On OSX:

```
brew install Rabbit-MQ
```

Install django celery with pip:

```
pip install django-celery
```

### Running

Start the celery worker:

```
celery -A tantalus worker -l info
```


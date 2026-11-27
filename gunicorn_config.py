# Gunicorn config untuk production
bind = "0.0.0.0:5000"
workers = 2
worker_class = "geventwebsocket.gunicorn.workers.GeventWebSocketWorker"
timeout = 120
keepalive = 5
accesslog = "/var/log/sharehosting/access.log"
errorlog = "/var/log/sharehosting/error.log"
loglevel = "info"

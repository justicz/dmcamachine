FROM nginx

LABEL maintainer "maxj@mit.edu"

RUN apt-get update && apt-get install -y python2.7-dev python-pip transmission-daemon

RUN pip install uwsgi flask transmissionrpc

ADD dmca /dmca

RUN chmod 755 /dmca
RUN chmod 755 /dmca/static

COPY nginx.conf /etc/nginx/nginx.conf

CMD service nginx start && \
	transmission-daemon --incomplete-dir /dmca/static/tmp/ -w /dmca/static/torrents/ -gsr 2 && \
	sleep 2 && \
	uwsgi --chdir /dmca --ini /dmca/dmca.ini


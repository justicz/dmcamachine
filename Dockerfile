FROM nginx

LABEL maintainer "maxj@mit.edu"

RUN apt-get update && apt-get install -y python3-dev python3-pip transmission-daemon

RUN pip3 install uwsgi flask transmissionrpc requests beautifulsoup4

ADD dmca /dmca

RUN chmod 755 /dmca
RUN chmod 755 /dmca/static

COPY nginx.conf /etc/nginx/nginx.conf

CMD service nginx start && \
	transmission-daemon --incomplete-dir /dmca/static/tmp/ -w /dmca/static/torrents/ -gsr 2 && \
	sleep 2 && \
	uwsgi --chdir /dmca --ini /dmca/dmca.ini


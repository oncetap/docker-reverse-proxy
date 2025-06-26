FROM busybox:musl

WORKDIR /web

COPY web/ .

CMD ["busybox", "httpd", "-f", "-p", "80", "-h", "/web"]

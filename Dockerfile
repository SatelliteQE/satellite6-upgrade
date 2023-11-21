FROM quay.io/fedora/python-311:latest
MAINTAINER https://github.com/SatelliteQE

COPY --chown=1001:0 / /satellite6-upgrade/
WORKDIR /satellite6-upgrade

ENV PYCURL_SSL_LIBRARY=openssl
RUN pip install -r requirements.txt

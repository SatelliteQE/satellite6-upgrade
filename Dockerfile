FROM fedora:38
MAINTAINER https://github.com/SatelliteQE

RUN dnf install -y gcc git make cmake libffi-devel openssl-devel python3-devel \
    python3-pip redhat-rpm-config which libcurl-devel libxml2-devel

COPY / /satellite6-upgrade/
WORKDIR /satellite6-upgrade

ENV PYCURL_SSL_LIBRARY=openssl
RUN pip install -r requirements.txt

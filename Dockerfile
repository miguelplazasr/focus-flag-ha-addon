ARG BUILD_FROM=ghcr.io/hassio-addons/base-python:16.0.1
FROM ${BUILD_FROM}

USER root

ENV TZ=America/New_York

# Install Python, pip and dependencies
RUN apk update && \
    apk upgrade && \
    apk add --no-cache \
        python3 \
        py3-pip \
        libusb \
        libusb-dev \
        gcc \
        libffi-dev \
        linux-headers \
        eudev-dev \
        glib-dev \
        pkgconfig \
        curl \
        tzdata && \
    pip3 install --no-cache-dir --root-user-action=ignore \
        flask pyluxafor hidapi pyusb gunicorn requests && \
    apk del gcc libffi-dev linux-headers glib-dev pkgconfig eudev-dev


COPY focusflag_api.py .
COPY run.sh /

RUN chmod a+x /run.sh

CMD [ "/run.sh" ]

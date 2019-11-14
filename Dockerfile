FROM python:3.7.1-alpine3.8

RUN apk add --update bash less

# The following build tools are for paramiko and numbpy. numpy is requied for
# afscripting > afdatetime > timezonefinder / pytz. Note that using
# afscripting results in an extra >100MB in docker image size
RUN apk --update add --no-cache --virtual .build-deps \
        make automake gcc g++ \
    && apk --update add --no-cache \
        musl-dev libffi-dev openssl-dev python3-dev

RUN apk add --update vim curl

WORKDIR /tmp/
COPY requirements.txt /tmp/requirements.txt
RUN pip3 install --no-binary gdal -r requirements.txt

# The following is supposed to decrease the size of the image,
# but doesn't seem to have any effect
RUN apk del --purge .build-deps

RUN mkdir /aws/
WORKDIR /aws/
ENV PATH="/aws/bin/:${PATH}"
ENV PYTHONPATH="/aws/:${PYTHONPATH}"
COPY bin/ /aws/bin/
COPY aws/ /aws/aws/

CMD ec2-launch -h

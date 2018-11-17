FROM python:3.6-slim

################################################################################
## setup container
################################################################################

################################################################################
## install app
## copy files one by one and split commands to use docker cache
################################################################################

RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc  python-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /code

COPY ./conf/pip /code/conf/pip

RUN pip3 install -f /code/conf/pip/dependencies -r /code/conf/pip/requirements.txt

RUN apt-get purge -y --auto-remove gcc python-dev

COPY ./ /code

################################################################################
## last setup steps
################################################################################

# create user to run container (avoid root user)
RUN useradd -ms /bin/false aether
RUN chown -R aether: /code

ENTRYPOINT ["/code/entrypoint.sh"]

FROM eu.gcr.io/finngen-refinery-dev/tomahawk:beta-0.7.1-dirty-fg-v1-ubuntu18

LABEL maintainer="jkarjala@broadinstitute.org"

ENV LC_ALL C.UTF-8
ENV LANG C.UTF-8

RUN apt update -y && apt install -y python3-pip libffi6 libffi-dev && pip3 install cython
ADD requirements.txt /opt/ld_server/
RUN pip3 install -r /opt/ld_server/requirements.txt

ADD run.py ld_server.py /opt/ld_server/

EXPOSE 8080

WORKDIR /mnt/ld
CMD /opt/ld_server/run.py --port 8080

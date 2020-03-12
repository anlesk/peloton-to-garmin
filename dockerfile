FROM python:3.7-slim

ENV NUM_ACTIVITIES=5
ENV OUTPUT_DIRECTORY="/output"

WORKDIR /usr/local/bin

COPY . /opt/app
WORKDIR /opt/app
RUN pip install -r requirements.txt

EXPOSE 8080
CMD python webServer.py
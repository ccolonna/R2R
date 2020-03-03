FROM python:2.7

# Coping source in current directory into the image
# python:2.7 expects the source in /usr/src/rst-service-api
COPY . /usr/src/rst-service-api

RUN apt-get update && apt-get install -y graphviz-dev
RUN pip install -r ./usr/src/rst-service-api/requirements.txt
RUN python -m nltk.downloader punkt
# commands in a list
CMD ["python", "./usr/src/rst-service-api/rst-service.py"]

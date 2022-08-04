# docker build -f docker/Dockerfile -t alcaval_app .
# docker run -it -p 8080:8080 alcaval_app

FROM pkalbhor/ubuntu-with-python:latest
USER root
RUN apt-get update -y
RUN apt-get upgrade -y

USER pritam
COPY . ${HOME}
RUN pip install -r requirements.txt

EXPOSE 8080
ENTRYPOINT ["tini", "-g", "--"]
CMD [ "waitress-serve", "--port=8080", "run:app"]
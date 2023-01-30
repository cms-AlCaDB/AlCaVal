# docker build -f docker/Dockerfile -t alcaval_app .
# docker run -it -p 8080:8080 alcaval_app

FROM pkalbhor/ubuntu-with-python:latest
USER root
RUN apt-get update -y
RUN apt-get upgrade -y
RUN curl -fsSL https://deb.nodesource.com/setup_16.x | sudo -E bash - &&\
sudo apt-get install -y nodejs

USER pritam
COPY . ${HOME}
RUN pip install -r requirements.txt
RUN cd react_fronend/ && npm i && npm run build && cd ../

EXPOSE 8080
ENTRYPOINT ["tini", "-g", "--"]
CMD [ "waitress-serve", "--port=8080", "run:app"]
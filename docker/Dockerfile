# docker build -f docker/Dockerfile -t alcaval_app .
# docker run -it -p 8080:8080 alcaval_app

FROM pkalbhor/ubuntu-with-python:latest
COPY . ${HOME}
RUN pip install -r requirements.txt

EXPOSE 8080
CMD [ "waitress-serve", "--port=8080", "run:app"]
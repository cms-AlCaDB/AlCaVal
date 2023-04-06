FROM python:3.8

WORKDIR /usr/src/app

# Installing krb5 client
ENV DEBIAN_FRONTEND noninteractive
COPY docker/krb5.conf /etc/krb5.conf
RUN apt-get update -y && apt upgrade -y
RUN apt-get install -y gcc krb5-user libkrb5-dev

COPY requirements.txt ./
RUN /usr/local/bin/python -m pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

ENV NODE_VERSION=16.19.1
ENV NVM_DIR=/root/.nvm
RUN curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.3/install.sh | bash
RUN . "$NVM_DIR/nvm.sh" && nvm install ${NODE_VERSION}
RUN . "$NVM_DIR/nvm.sh" && nvm use v${NODE_VERSION}
RUN . "$NVM_DIR/nvm.sh" && nvm alias default v${NODE_VERSION}
ENV PATH="/root/.nvm/versions/node/v${NODE_VERSION}/bin/:${PATH}"
RUN node --version
RUN npm --version

COPY . .

# Making sure node.js do not use lot of memory during install/build
RUN cd react_frontend/ && npm install && cd ../
RUN cd react_frontend/ && npm run build && cd ../

EXPOSE 8080
# ENTRYPOINT ["tini", "-g", "--"]
CMD [ "waitress-serve", "--port=8080", "run:app"]

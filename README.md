# AlCaVal: [Relval](https://github.com/cms-PdmV/RelVal) submision tool for AlCa
Documentation: [Wiki](https://github.com/cms-AlCaDB/AlCaVal/wiki)

## Development
### Prerequisites
Make sure following files are present before starting the application.
1. `secrets/client_secrets.json`
Put appropriate values for `client_id` and `client_secret`. If you do not have them, you can register new application at [application portal](https://application-portal.web.cern.ch/)
```json
{
  "web": {
    "client_id": "<oidc client id here>",
    "client_secret": "<oidc client secret here>"
  }
}

```
2. `secrets/environs.txt`
```env
# Required variables for AlCaVal application 
FLASK_SECRET_KEY='SOME random secret string for Flask'
DATABASE_USER=root
DATABASE_PASSWORD=example
INSTANCE=dev

# MongoDB container variables
MONGO_INITDB_ROOT_USERNAME=${DATABASE_USER}
MONGO_INITDB_ROOT_PASSWORD=${DATABASE_PASSWORD}

# Mongo-Express container variables
ME_CONFIG_BASICAUTH_USERNAME=alcauser-me-user
ME_CONFIG_BASICAUTH_PASSWORD=alcauser-me-pass
ME_CONFIG_MONGODB_AUTH_USERNAME=${DATABASE_USER}
ME_CONFIG_MONGODB_AUTH_PASSWORD=${DATABASE_PASSWORD}
```
3. `secrets/jira_credentials.cfg`
```json
{
    "username": "<jira-username>",
    "password": "<jira-password>"
}
```
4. `secrets/ssh_credentials.cfg`
```json
{
    "username": "<lxplus-username>",
    "password": "<lxplus-password>"
}
```
5. `secrets/userkey.pem`
GRID user-key to be used for accessing cmsweb services
6. `secrets/usercert.pem`
GRID user-certificate to be used for accessing cmsweb services

### Launching the application
Install docker in case it is not installed in your machine. Follow [Install Docker Engine](https://docs.docker.com/engine/install/) and [Install Docker Compose](https://docs.docker.com/compose/install/).

#### Installing Docker Engine
##### 1) Install required packages
```
sudo apt-get install apt-transport-https ca-certificates curl software-properties-common
```
##### 2) Add Docker's official GPG key
```
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
```
##### 3) Set up the Docker stable repository
```
sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"
```

#### 4) Update the package database
```
sudo apt-get update
```

#### 5) Install Docker
```
sudo apt-get install docker-ce
```

#### 6) Verify Docker installation
```
sudo docker --version
```

### Installing Docker Compose

#### 1) Download Docker Compose
```
sudo curl -L "https://github.com/docker/compose/releases/download/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
```
Note: Replace 1.29.2 with the latest version of Docker Compose.

#### 2) Apply executable permissions
```
sudo chmod +x /usr/local/bin/docker-compose
```
#### 3) Verify Docker Compose installation
```
docker-compose --version
```

Then launch application using:

```docker-compose up app```

Application is accesible at http://localhost:8080 and database can be accessed from http://localhost:8081.


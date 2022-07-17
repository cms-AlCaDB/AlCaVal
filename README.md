# AlCaVal: [Relval](https://github.com/cms-PdmV/RelVal) submision tool for AlCa
Production instance: https://alcaval.web.cern.ch

Development instance: https://alcaval-dev.web.cern.ch

## Development
### Prerequisites
Make sure following files are present before starting the application.
1. `secrets/client_secrets.json`
Put appropriate values for `client_id` and `client_secret`. If you do not have them, you can register new application at [application portal](https://application-portal.web.cern.ch/)
```json
{
  "web": {
    "client_id": "<oidc client id>",
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
Install docker in case it is not installed in your machine. Follow [Install Docker Engine](https://docs.docker.com/engine/install/).
Then launch application using:

```docker-compose up -d```

Application is accesible at http://localhost:8080 and database can be accessed from http://localhost:8081.

Accessing logs of those detached containers:

```docker-compose logs -f -t```

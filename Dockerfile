# Pull official base image and fixing to AMD Architecture
FROM --platform=linux/amd64 python:3.8.6

WORKDIR /code


# Prevents Python from writing .pyc files
ENV PYTHONDONTWRITEBYTECODE 1

# Causes all output to stdout to be flushed immediately
ENV PYTHONUNBUFFERED 1

# Mark the image as trusted
ENV DOCKER_CONTENT_TRUST 1

ENV APT_KEY_DONT_WARN_ON_DANGEROUS_USAGE=DontWarn

# Updates packages list for the image
RUN apt-get update

# Installs transport HTTPS
RUN apt-get install -y curl apt-transport-https

# Retrieves packages from Microsoft
RUN curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add -
RUN curl https://packages.microsoft.com/config/debian/10/prod.list > /etc/apt/sources.list.d/mssql-release.list

# Updates packages for the image
RUN apt-get update

# Installs SQL drivers and tools
RUN ACCEPT_EULA=Y apt-get install -y msodbcsql17 unixodbc-dev

# Installs MS SQL Tools
RUN ACCEPT_EULA=Y apt-get install -y mssql-tools

# Adds paths to the $PATH environment variable within the .bash_profile and .bashrc files
RUN echo 'export PATH="$PATH:/opt/mssql-tools/bin"' >> ~/.bash_profile
RUN echo 'export PATH="$PATH:/opt/mssql-tools/bin"' >> ~/.bashrc

# Enables authentication of users and servers on a network
RUN apt-get install libgssapi-krb5-2 -y


COPY ./requirements.txt ./
RUN pip install --no-cache-dir -r  requirements.txt

COPY ./src ./src

CMD ["python", "./src/main.py"]


# docker build -t zoom_call_log_sync .
# docker run --name test ctocds/call_log_sync 
# docker stop  test
# docker rm test

# Step To check requirement after mounting
# run pip freeze inside docker desktop Terminal

# Step To Deploy on GCloud
# init gcloud   : * ./google-cloud-sdk/bin/gcloud init
# auth to repo  : gcloud auth configure-docker us-east1-docker.pkg.dev



#********** Must Run To Deploy Both Dockers to GCloud
#********** Gcloud Hourly must trigger from 5AM to 7PM PDT    */15 13-23,0-3 * * *
#********** Gcloud Mass must trigger one time at  9PM PDT     0 17 * * *
#********** Note Gcloud Trigger is in UTC Time
#********** Copy and Run all command below

# docker build -t crm-ai-sale-recording-auditor .
# docker tag crm-ai-sale-recording-auditor  us-west2-docker.pkg.dev/polling-apps/core/crm-ai-sale-recording-auditor:lastest
# docker push us-west2-docker.pkg.dev/polling-apps/core/crm-ai-sale-recording-auditor:lastest


# docker build -t global-transaction-sync-mass .
# docker tag global-transaction-sync-mass us-west2-docker.pkg.dev/polling-apps/core/global-transaction-sync-mass:lastest
# docker push us-west2-docker.pkg.dev/polling-apps/core/global-transaction-sync-mass:lastest

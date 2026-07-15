# Pull official base image (Python 3.12 on Debian 12 "Bookworm"), fixed to AMD64
# so the image runs on GCloud regardless of the machine it is built on.
FROM --platform=linux/amd64 python:3.12-slim-bookworm

WORKDIR /code

# Prevents Python from writing .pyc files
ENV PYTHONDONTWRITEBYTECODE=1

# Causes all output to stdout to be flushed immediately (real-time docker logs)
ENV PYTHONUNBUFFERED=1

# Install system dependencies and the Microsoft ODBC Driver 18 for SQL Server.
# The official packages-microsoft-prod.deb registers the repo and GPG key the
# modern way (signed-by keyring) — no deprecated apt-key, no archive workaround.
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
        curl gnupg apt-transport-https ca-certificates \
 && curl -sSL -O https://packages.microsoft.com/config/debian/12/packages-microsoft-prod.deb \
 && dpkg -i packages-microsoft-prod.deb \
 && rm packages-microsoft-prod.deb \
 && apt-get update \
 && ACCEPT_EULA=Y apt-get install -y --no-install-recommends \
        msodbcsql18 mssql-tools18 unixodbc-dev libgssapi-krb5-2 \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

# Make the SQL command-line tools available on PATH
ENV PATH="$PATH:/opt/mssql-tools18/bin"

COPY ./requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY ./src ./src

CMD ["python", "./src/main.py"]


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

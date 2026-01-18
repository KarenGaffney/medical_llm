# Setup Instructions for the medical_llm app

## Prerequisites
Git
Docker Desktop
(Optional) VS Code + MSSQL extension (to create tables / seed data)
(Optional) Postman (to test backend endpoints)

## 1) Clone the Repo
>git clone https://github.com/KarenGaffney/medical_llm.git
>
>cd medical_llm
## 2) Create the .env file with the following parameters (same level as docker-compose.yml)
>##Azure OpenAI
>AZURE_OPENAI_ENDPOINT=
>
>AZURE_OPENAI_API_KEY=
>
>AZURE_OPENAI_DEPLOYMENT=
>
>API_VERSION=
>
>##Microsoft Entra / Microsoft Graph
>TENANT_ID=
>
>CLIENT_ID=
>
>CLIENT_SECRET=
>
>GRAPH_SCOPES=Calendars.ReadWrite User.Read
>
>REDIRECT_URI=http://localhost:5000/auth/callback
>
>OBJECT_ID=
>
>##Azure SQL Database
>AZURE_SQL_SERVER=
>
>AZURE_SQL_DB=
>
>AZURE_SQL_USER=
>
>AZURE_SQL_PASSWORD=

## 5) Azure OpenAI setup
Create an Azure OpenAI resource.

Deploy a chat model (example: gpt-5-mini, gpt-4.1-mini, etc.).

Populate the parameters in .env under ## Azure OpenAI
## 7) Microsoft Graph setup

Regiser the App

Go to
1. Azure Portal
2. Microsoft Entra ID
3. App registrations
4. New registration

Create a client secret
1. App registration
2. Certificates & secrets
3. New client secret

Add API permissions 
1. App registration
2. API permissions
3. Add a permission
4. Microsoft Graph
5. Application permissions:
  Calendars.ReadWrite
  User.Read.All
6. Then click Grant admin consent.

Populate the parameters in .env under ## Microsoft Entra / Microsoft Graph

Identify the mailbox user

You need a user with an Exchange mailbox (ex: MeredithGrey@...onmicrosoft.com) and a M365 license assigned.

Copy the Object ID and add it to the OBJECT_ID in the .env file

## 9) AzureSQL setup
   
Create SQL Server + Database
1. Azure Portal
2. Create a new SQL server
3. SQL databases
4. Create

Add the server name (___.database.windows.net), database name, sql user and password to the .env file under ## Azure SQL Database

Networking / firewall
1. Azure Portal
2. SQL Server
3. Networking
4. add your current client IPv4

!!!If you change networks: you will need to update this IP when it changes!!!

## 11) Run the App
In the same level as docker-compose.yaml, run 
>docker compose build
>
>docker compose up

Navigate to localhost:3000 

# Happy Scheduling!


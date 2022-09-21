
## Greengrass Labs PostgreSQL Component - `aws.greengrass.labs.database.PostgreSQL`

## Overview
This AWS IoT Greengrass component allows you to provision and manage a PostgreSQL database on your device. It is currently only released for Linux based distributions.

At a high level, this component will do the following:
1. Pull down the official PostgreSQL alpine linux image (`docker:postgres:alpine3.16`), a lightweight PostgreSQL image, from Dockerhub.
2. Retrieve a pre-configured secret containing a username and password from AWS Secrets Manager via the `aws.greengrass.SecretManager` Greengrass component. The retrieved secret is used to setup the PostgreSQL database as the superuser.
3. Manage the lifecycle of a PostgreSQL server via starting and stopping the docker container. When the component is started, it initializes the docker container and mounts it to a location of your choice. When the component is removed, it stops the docker container and removes it.
4. Validates that the PostgreSQL server is online and forwards the container logs to the Greengrass logs.

## Configuration
The `aws.greengrass.labs.database.PostgreSQL` component supports the following configuration options. All values are required with provided default values, except the `PostgreSQLContainerConfig/Volume` configuration which may be removed.

* `ContainerMapping` (_optional_) - Set of configuration values related to the Docker PostgreSQL container
    * HostPort: The port of GG core device where the docker container postgresql server port is published. 
      * (`string`)
      * default: `5432`
    * ContainerName (_optional_) : The name of the Docker container
      * (`string`)
      * default: `greengrass_postgresql`
    * HostVolume (_optional_) : The location to mount the docker volume to. This directory is used for postresql data storage. If left blank (as per default), the component will mount the volume to the component's work folder
      * (`string`)
      * default: `<greengrass-home>/work/aws.greengrass.labs.database.PostgreSQL/postgresql`

* `DBCredentialSecret` (_required_) - The ARN of the AWS Secret Manager secret containing your desired PostgreSQL username/password. You must configure and deploy this secret with the [Secret manager component](https://docs.aws.amazon.com/greengrass/v2/developerguide/secret-manager-component.html), and you must specify this secret in the `accessControl` configuration parameter to allow this component to use it.
    * (`string`)
    * default: `arn:aws:secretsmanager:<region>:<account>:secret:<name>`

* `ConfigurationFiles` - Set of configuration files used by postgresql server.
    * postgresql.conf (_optional_) : Absolute file path of the custom postgresql configuration file on the GG core device.
      * (`string`)
      * default: `<postgresql-data-volume>/postgresql.conf`
    * pg_hba.conf (_optional_) : Absolute file path of the custom host-based authentication file on the GG core device.
      * (`string`)
      * default: `<postgresql-data-volume>/pg_hba.conf`
    * pg_ident.conf (_optional_) : Absolute file path of the custom ident map file on the GG core device.
      * (`string`)
      * default: `<postgresql-data-volume>/pg_ident.conf`
* `accessControl` (_required_):  [Greengrass Access Control Policy](https://docs.aws.amazon.com/greengrass/v2/developerguide/interprocess-communication.html#ipc-authorization-policies), required for secret retrieval

    This component's default accessControl policy allows GetSecretValue access to the secret arn resource for retrieving a secret, which you will need to configure. This secret arn should be same as the one specified in `DBCredentialSecret`. 


## Setup

### Prerequisites

**The following steps are for a fresh AL2 EC2 instance, but will likely be similar across Linux distributions.**

1. Install dependencies on the host machine:

```
sudo yum update
sudo python3 -m pip install awsiotsdk docker
sudo yum install -y docker
sudo service docker start
```

2. Setup AWS IoT Greengrass on the host machine [according to the installation instructions](https://docs.aws.amazon.com/greengrass/v2/developerguide/install-greengrass-core-v2.html):

3. Log in as superuser with `sudo su` and then allow `ggc_user:ggc_group` to use Docker, [as per the Docker documentation](https://docs.docker.com/engine/install/linux-postinstall/):
``` 
sudo usermod -aG docker ggc_user; newgrp docker 
```
   Test your access with first `sudo su` and then `su - ggc_user -c "docker ps"`

### Component Setup
1. Install [the Greengrass Development Kit CLI](https://docs.aws.amazon.com/greengrass/v2/developerguide/install-greengrass-development-kit-cli.html) in your local workspace.
    1. Run `python3 -m pip install git+https://github.com/aws-greengrass/aws-greengrass-gdk-cli.git`
2. Pull down the component in a new directory using the GDK CLI.

  ```
   gdk component init --repository aws-greengrass-labs-database-postgresql -n aws-greengrass-labs-database-postgresql
   ```
3. Create an AWS Secrets Manager Secret to store your PostgreSQL username/password.
    1. Go to [AWS Secrets Manager](https://console.aws.amazon.com/secretsmanager/home?region=us-east-1#!/listSecrets):
    2. Create new secret → Other type of Secret → Plaintext. The secret you use should be in the following format (with your own username and password):
    ```
    {
    "POSTGRES_USER": "PostgreSQLUsername",
    "POSTGRES_PASSWORD": "PostgreSQLpass123!"
    }
    ```

   Note down the ARN of the secrets you just made.

4. Authorize Greengrass to retrieve this secret using IAM:
    1. Follow [the Greengrass documentation](:https://docs.aws.amazon.com/greengrass/v2/developerguide/device-service-role.html) to add authorization
    2. See the [`aws.greengrass.SecretManager` documentation for more information.](https://docs.aws.amazon.com/greengrass/v2/developerguide/secret-manager-component.html)
    3. Your policy should include `secretsmanager:GetSecretValue` for the secret you just created:
    ```
        {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "VisualEditor1",
                "Effect": "Allow",
                "Action": "secretsmanager:GetSecretValue",
                "Resource": [
                    "<PostgreSQL secret arn>"
                ]
            }
        ]
    }
    ```

5. Configure and build the component:
   - Modify the `aws.greengrass.labs.database.PostgreSQL` recipe at `recipe.yaml`.
     - Replace the two occurrences of `'arn:aws:secretsmanager:region:account:secret:name'` with your created secret ARN, including in the `accessControl` policy.
     - Modify any other configurations you wish to change (see above)
   - Modify the values in `gdk-config.json` for GDK use:
     - Specify the S3 bucket name you want to use to store the component artifacts. GDK will create a new bucket if it doesn't exist. 
       - Ensure that the Greengrass IAM role (usually `GreengrassV2TokenExchangeRole`) has read access to the chosen S3 bucket
     - Specify the AWS region in which you want to create and deploy the component. 
     - Refer to the [GDK docs](https://docs.aws.amazon.com/greengrass/v2/developerguide/gdk-cli-configuration-file.html) to see examples of this file and what values are supported by the configuration
   - Build the component using the GDK:
     - Use the [GDK CLI](https://docs.aws.amazon.com/greengrass/v2/developerguide/greengrass-development-kit-cli.html) to build the component to prepare for publishing.
        ```
        gdk component build
        ```
     - Use the [GDK CLI](https://docs.aws.amazon.com/greengrass/v2/developerguide/greengrass-development-kit-cli.html) to create a private component.
        ```
        gdk component publish
        ```

6. Create deployment via the AWS CLI or AWS Console, from [Greengrass documentation](https://docs.aws.amazon.com/greengrass/v2/developerguide/create-deployments.html). The following components should be configured in your deployment:
   - `aws.greengrass.SecretManager`:
      ```
      "cloudSecrets": [
      {
      "arn": "<PostgreSQL secret arn>"
      }
      ]
      ```

## Verify Component is Running Properly
To verify that the component has deployed successfully, you can view the component logs at `/greengrass/v2/logs/aws.greengrass.labs.database.PostgreSQL.log`, replacing `/greengrass/v2/` with your Greengrass install directory. If correctly set up, you will see the message `LOG:  database system is ready to accept connections.` and see logs from PostgreSQL as it runs.

You may also manually use the created PostgreSQL database as you normally would. For example, if you wish to use `psql` to interact with your database with default database name `postgres`, you may use:
```
docker exec -it greengrass_postgresql bash
psql -U <PostgreSQL username> -d postgres
```

## Component Lifecycle Management
Because the PostgreSQL Docker container is mounted to a location of your choice, database information is persisted between component startups. When this component is deployed, the PostgreSQL server will be available for connections. On component removal, the server will be stopped and removed, but data will still persist if the component is to be started again with.

Changing the mount location (volume) in configuration will create new data at the new mount location. Going back to a previous mount location will continue using the PostgreSQL data from that location.

## Resources
* [AWS IoT Greengrass V2 Developer Guide](https://docs.aws.amazon.com/greengrass/v2/developerguide/what-is-iot-greengrass.html)
* [AWS IoT Greengrass V2 Community Components](https://docs.aws.amazon.com/greengrass/v2/developerguide/greengrass-software-catalog.html)
* [AWS IoT Greengrass Development Kit CLI](https://docs.aws.amazon.com/greengrass/v2/developerguide/greengrass-development-kit-cli.html)
* [PostgreSQL Dockerhub ](https://hub.docker.com/_/postgres)
* [PostgreSQL Documentation](https://www.postgresql.org/docs/)

## Container Security
* Greengrass does not manage or distribute the PostgreSQL Alpine Linux Docker image referenced in this Greengrass component. You are responsible for securing Docker containers on your device and ensuring it does not contain vulnerabilities or security risks.

## Troubleshooting

- `ModuleNotFoundError: No module named 'docker'`
  - Make sure to install docker (or awsiotsdk if that's what the error is for) when installing python dependencies:
  - `sudo python3 -m pip install docker`

- `Got permission denied while trying to connect to the Docker daemon socket`
  - Allow `ggc_user:ggc_group` to use Docker:
  - `sudo usermod -aG docker ggc_user; newgrp docker `

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This project is licensed under the Apache-2.0 License.

This project also uses but does not distribute the postgres:alpine3.16 Docker image from Dockerhub, which is under the [MIT License](https://github.com/docker-library/postgres/blob/master/LICENSE). You can view the PostgreSQL license [here](https://www.postgresql.org/about/licence/).  
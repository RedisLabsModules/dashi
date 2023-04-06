# CI Dashboard for Redis projects

## Prerequisites

- Docker installed on your machine
- Docker Compose installed on your machine

## Getting Started

1. Clone the repository:

   ```bash
   git clone https://github.com/RedisLabsModules/dashi
   cd dashi

2. Create a .env file in the project root directory with the necessary environment variables. Here's an example:

    ```ini
    DB_USER=postgres
    DB_PASSWORD=password
    DB_HOST=db
    DB_PORT=5432
    DB_NAME=dashi
    ```

3. Build and run the dashi using Docker Compose:

    ```bash
    docker-compose up --build
    ```

    This command will build the Docker images and start the containers specified in the docker-compose.yml file.

4. Access the dashi in your browser:

    Open your browser and navigate to `http://localhost:5001`. You should now see the dashboard running locally.

5. Stopping the dashi
    To stop the dashi and clean up the containers, run the following command:

    ```bash
    docker-compose down
    ```

    For more information and advanced usage, please refer to the official [Docker Compose documentation](https://docs.docker.com/compose/).

## Additional information

As part of the environment setup, the app will begin pulling information from the repositories specified in the `main.yaml` file. Additionally, it will retrieve information from CircleCI pipelines, if any are specified. Some of the repositories and CircleCI pipelines may be protected; therefore, to access this information, you need to provide GitHub `GH_TOKEN` and CircleCI `CIRCLE_CI_TOKEN` access tokens in the `.env` file.

## Deployment

This example demonstrates how to deploy dashi using the AWS Cloud Development Kit (CDK) written in Python.

### CDK Prerequisites

- AWS account with appropriate permissions
- AWS CLI configured on your machine
- Python 3.6 or later installed on your machine
- Node.js 10.x or later installed on your machine

## Setting up CDK

1. Install AWS CDK:

    ```bash
    npm install -g aws-cdk
    ```

2. Create a virtual environment for Python and activate it:

    ```bash
    cd dashi/cdk
    python3 -m venv .venv
    source .venv/bin/activate
    ```

3. Install the required Python packages:

    ```bash
    pip install -r requirements.txt
    ```

4. Synthesize the CloudFormation template:

    ```bash
    cdk synth
    ```

    This command will generate a CloudFormation template based on dashi's CDK code.

5. Deploy the app using AWS CDK:

    ```bash
    cdk deploy
    ```

    This command will deploy the dashi using the generated CloudFormation template.

6. Cleaning Up
    To delete the deployed resources and clean up the AWS environment, run the following command:

    ```bash
    cdk destroy
    ```

# FaaS-TradeOff

This repository contains the code and documentation for a benchmarking tool designed to explore the trade-off between accuracy and duration in serverless function performance testing. The tool focuses on identifying performance regressions in serverless functions deployed on AWS Lambda and Google Cloud Functions (GCF).

## Project Overview

This tool aims to address the challenges of efficiently and accurately identifying performance regressions in serverless functions. Traditional benchmarking approaches often involve extensive testing, which can be time-consuming and resource-intensive. This tool introduces a novel approach that allows for a trade-off between the duration of the benchmarking process and the accuracy of regression detection.

The tool utilizes four different constraints to control the benchmarking process:

* **Accuracy-Limited:** Stops the benchmark when a predefined accuracy threshold is reached.
* **Call-Limited:** Limits the number of function invocations.
* **Budget-Limited:** Limits the total cost incurred during benchmarking.
* **Time-Limited:** Limits the total duration of the benchmarking process.

By employing these constraints, the tool enables a more flexible and efficient approach to benchmarking, allowing users to tailor the process to their specific needs and priorities.

## Prerequisites

Before running experiments, ensure you have the following:

### Cloud Accounts and Permissions

* **Active Cloud Accounts:**
    * An active Google Cloud Project with billing enabled.
    * An active AWS account with necessary permissions for Lambda function management.
* **Credentials:**
    * A service account key file (`service_account.json`) for your Google Cloud Project with appropriate permissions (e.g., Cloud Functions Admin, Cloud Logging Viewer).
    * Your AWS Access Key ID and Secret Access Key.
* **Environment Variables:**
    * Set the following environment variables:
        * `GOOGLE_APPLICATION_CREDENTIALS`: Path to your `service_account.json` file.
        * `AWS_ACCESS_KEY_ID`: Your AWS Access Key ID.
        * `AWS_SECRET_ACCESS_KEY`: Your AWS Secret Access Key.

### Software and Tools

* **SDKs and CLIs:**
    * Google Cloud SDK installed and configured (`gcloud`). You can find installation instructions at: [https://cloud.google.com/sdk/docs/install](https://cloud.google.com/sdk/docs/install)
    * AWS CLI installed and configured (`aws`). You can find installation instructions at: [https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)
* **Python:** Python 3.9 or higher.
* **Terraform:** Install Terraform by following the instructions at: [https://learn.hashicorp.com/tutorials/terraform/install-cli](https://learn.hashicorp.com/tutorials/terraform/install-cli)
* **Artillery:** Install Artillery using npm:
    ```bash
    npm install -g artillery@latest
    ```
* **Dependencies:** Install the required Python packages:
    ```bash
    pip install -r requirements.txt
    ```


## Running Experiments

### 1. Deploying the Functions

1. Depending on which Function you want to deploy, move to either or both folders:

    - Monte Carlo:
        ```
        cd src\monte-carlo\deployment
        ```
    - Sieve of Eratosthenes:
        ```
        cd src\sieve\deployment
        ```
2. Move into both AWS and GCP folders and check the `variables.tf` file, in case some adjustments are needed.
3. Deploy the functions using Terraform:
    ```
    terraform init
    terraform plan
    terraform apply
    ```

### 2. Configuration

Move to configurations folder:
```
cd Benchmark-Limitations\configurations
```

* **`yaml Files`:** Modify the `yaml` file to specify the desired configuration for your benchmark experiments. The following parameters can be configured:
    * **`target`:** change the `HTTP URL` trigger for both `aws` and `gcp`.
    * **`benchmark`:** The name of the function to deploy and benchmark.
    * **`batch_duration`:** The duration of the batch run.
    * **`arrival_count\arrival_rate`:** The number of simulated users.
    * **`region`:** The cloud region for deployment.
    * **`loggroup\projectid`:** The name of the log group (AWS) or the project id (GCP).
    * **`threshold`:** The accuracy threshold for the `Accuracy` constraint.
    * **`max_budget`:** The maximum budget in USD for the `Budget` constraint.

### 3. Benchmarking

* Run the `run-AB-Experiments.sh` script to execute the benchmark experiments:

    ```bash
    cd Benchmark-Limitations
    find . -type f \( -name "*.py" -o -name "*.sh" \) -exec chmod +x {} \;
    ./run-AB-Experiments.sh
    ```

    This script will:
    * Invoke the deployed function with different input parameters.
    * Collect performance metrics (execution time, cost, etc.).
    * Analyze the results based on the defined constraints.
    * Generate log files and store them in the `logs` directory.
    * Analyze the log files and calculate the bootstrapped 95% percentile confidence interval 

aws_region  = "us-east-1"
project_name = "dashboard"
environment  = "dev"
db_name      = "dashboard"
db_username  = "postgres"
# Do not store actual password in this file
# db_password will be provided via environment variable TF_VAR_db_password
# or via GitHub Actions secrets
ssh_key_name = "ssh-key" # Replace with your SSH key name

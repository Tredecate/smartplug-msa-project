#!/bin/bash
set -e

# Run terraform destroy
cd terraform
terraform destroy -auto-approve -var-file="../.key_files/ssh_key_path.tfvars"

# Remove generated files
rm -rf ../.key_files
rm -f ../ansible/inventory.ini

# Finish
echo "Deployment destroyed successfully."

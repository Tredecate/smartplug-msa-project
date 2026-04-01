#!/bin/bash
set -e


#####################
### SSH KEY SETUP ###
#####################

mkdir -p ./.key_files
key_path="./.key_files/smartplug-msa-key"

# If no key exists at default path, ask user if they want to generate one
if [[ ! -f "$key_path" ]]; then
    echo "No SSH key found for this deployment. Would you like to generate one? (y/n)"
    read response
    if [[ "$response" == "y" ]]; then
    # If user wants to generate a key, create it
        ssh-keygen -q -t ed25519 -f "$key_path" -N "" -C "ec2-user key for $(basename "$(dirname "$(pwd)")") terraform deployment" && \
        echo "SSH key generated successfully at $key_path."

    else
        echo "SSH key is required for deployment. Would you like to provide an existing key path? (y/n)"
        read provide_key
        if [[ "$provide_key" == "y" ]]; then
            echo "Please enter the path to your existing SSH private key:"
            read -e existing_key_path
            existing_key_path="${existing_key_path/#\~/$HOME}"

            # If the user's key exists, use it
            if [[ -f "$existing_key_path" ]]; then
                echo "Using existing SSH key at $existing_key_path."
                key_path="$existing_key_path"

            else # If the user's key doesn't exist, exit with error
                echo "The provided key path does not exist. Exiting deployment."
                exit 1
            fi

        else
            # If the user doesn't want to generate a key or use an existing one, exit with error
            echo "SSH key is required for deployment. Exiting."
            exit 1
        fi
    fi
fi

# Save the absolute path to the SSH key in a tfvars file for Terraform
key_path="$(realpath "$key_path")"
echo "ssh_key_path = \"$key_path\"" > ./.key_files/ssh_key_path.tfvars

echo "SSH key path saved."


############################
### TERRAFORM DEPLOYMENT ###
############################

# Run Terraform stuff
cd terraform
terraform init
terraform apply -auto-approve -var-file="../.key_files/ssh_key_path.tfvars"

# Write instance IP to Ansible inventory
terraform output -raw instance_ip > ../ansible/inventory.ini

echo "Terraform deployment complete."


############################
### ANSIBLE PROVISIONING ###
############################

# Run Ansible playbook
cd ../ansible
ansible-playbook playbook.yml --private-key="$key_path"

# Print application dashboard URL
echo "Deployment complete. You can access the application at http://$(cat inventory.ini):8000"

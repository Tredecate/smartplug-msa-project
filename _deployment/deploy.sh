#!/bin/bash
set -e

#################
##### UTILS #####
#################

# Check for auto mode
if [[ "$1" == "--auto" || "$1" == "-y" ]]; then
    echo "Auto mode enabled. Generating SSH key and skipping prompts."
    auto=true
else
    auto=false
fi

# Function to get yes/no response
function get_yes_no() {
    printf "$1: " >&2
    if [[ "$auto" == true ]]; then
        echo "y (auto)" >&2
        echo "y"
    else
        read response
        echo "${response:-y}"
    fi
}

# Function to get confirmation to continue
function get_confirmation() {
    printf "Press enter to continue with $1... " >&2
    if [[ "$auto" == true ]]; then
        echo "(auto)"
    else
        read
    fi
}


#####################
### SSH KEY SETUP ###
#####################

mkdir -p ./.key_files
key_path="./.key_files/smartplug-msa-key"

# If no key exists at default path, ask user if they want to generate one
if [[ ! -f "$key_path" ]]; then
    echo "No SSH key found for this deployment. Would you like to generate one?"
    response=$(get_yes_no "Generate SSH key? (Y/n)")

    # If user wants to generate a key, create it
    if [[ "$response" =~ ^[Yy]$ ]]; then
        ssh-keygen -q -t ed25519 -f "$key_path" -N "" -C "ec2-user key for $(basename "$(dirname "$(pwd)")") terraform deployment" && \
        echo "SSH key generated successfully at $key_path."

    else # If user doesn't want to generate a key, ask if they want to use an existing key
        echo "SSH key is required for deployment. Would you like to provide an existing key path?"
        provide_key=$(get_yes_no "Provide existing SSH key? (Y/n)")

        # If user wants to use an existing key, ask for the path and validate it
        if [[ "$provide_key" =~ ^[Yy]$ ]]; then
            echo "Please enter the path to your existing SSH private key."
            read -p "Existing SSH key path: " -i "~/.ssh/" -e existing_key_path
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

# Wait for confirmation to continue
get_confirmation "Terraform deployment"
echo "Continuing with Terraform deployment..."

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

# Wait for confirmation to continue
get_confirmation "Ansible provisioning"
echo "Continuing with Ansible provisioning..."

# Run Ansible playbook
cd ../ansible
ansible-playbook playbook.yml --private-key="$key_path"

# Print application dashboard URL
echo "Deployment complete. You can access the application at http://$(cat inventory.ini):8000"

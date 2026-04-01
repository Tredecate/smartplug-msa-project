#!/bin/bash
key_path="./keys/smartplug-msa-key"

if [[ ! -f "$key_path" ]]; then
    echo "No SSH key found for this deployment. Would you like to generate one? (y/n)"
    read response
    if [[ "$response" == "y" ]]; then
        ssh-keygen -q -t ed25519 -f "$key_path" -N "" -C "ec2-user key for $(basename "$(pwd)") terraform deployment" && \
        echo "SSH key generated successfully at $key_path."
    else
        echo "SSH key is required for deployment. Would you like to provide an existing key path? (y/n)"
        read provide_key
        if [[ "$provide_key" == "y" ]]; then
            echo "Please enter the path to your existing SSH private key:"
            read existing_key_path
            if [[ -f "$existing_key_path" ]]; then
                echo "Using existing SSH key at $existing_key_path."
                key_path="$existing_key_path"
            else
                echo "The provided key path does not exist. Exiting deployment."
                exit 1
            fi
        else
            echo "SSH key is required for deployment. Exiting."
            exit 1
        fi
    fi
fi

key_path="$(realpath "$key_path")"

cd terraform
terraform init
terraform apply -auto-approve -var="ssh_key_path=$key_path"
terraform output -raw instance_ip > ../ansible/inventory.ini

cd ../ansible
ansible-playbook playbook.yml --private-key="$key_path"

echo "Deployment complete. You can access the application at http://$(cat inventory.ini):8000"
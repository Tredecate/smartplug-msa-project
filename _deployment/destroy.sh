set -e
cd terraform
terraform destroy -auto-approve -var-file="../.key_files/ssh_key_path.tfvars"
rm -rf ../.key_files
rm -f ../ansible/inventory.ini
echo "Deployment destroyed successfully."
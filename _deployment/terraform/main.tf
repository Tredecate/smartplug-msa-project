terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

variable "ssh_key_path" {
  default = "../.key_files/smartplug-msa-key"
}

provider "aws" {
  region = "us-west-2"
}

data "aws_ami" "amazon_linux" {
  most_recent = true
  owners      = ["amazon"]
  filter {
    name   = "name"
    values = ["al2023-ami-2023.*-kernel-6.18-x86_64"]
  }
}

data "aws_vpc" "default" {
  default = true
}

data "aws_subnet" "default" {
  vpc_id            = data.aws_vpc.default.id
  default_for_az    = true
  availability_zone = "us-west-2a"
}

resource "aws_security_group" "allow_ports" {
  name        = "allow_smartplug_msa_ports"
  description = "Allow 8000, 8080, 8100, 8110, and 22"
  vpc_id      = data.aws_vpc.default.id
}

resource "aws_vpc_security_group_ingress_rule" "allow_8000" {
  security_group_id = aws_security_group.allow_ports.id

  cidr_ipv4   = "0.0.0.0/0"
  from_port   = 8000
  to_port     = 8000
  ip_protocol = "tcp"
}

resource "aws_vpc_security_group_ingress_rule" "allow_8080" {
  security_group_id = aws_security_group.allow_ports.id

  cidr_ipv4   = "0.0.0.0/0"
  from_port   = 8080
  to_port     = 8080
  ip_protocol = "tcp"
}

resource "aws_vpc_security_group_ingress_rule" "allow_8100" {
  security_group_id = aws_security_group.allow_ports.id

  cidr_ipv4   = "0.0.0.0/0"
  from_port   = 8100
  to_port     = 8100
  ip_protocol = "tcp"
}

resource "aws_vpc_security_group_ingress_rule" "allow_8110" {
  security_group_id = aws_security_group.allow_ports.id

  cidr_ipv4   = "0.0.0.0/0"
  from_port   = 8110
  to_port     = 8110
  ip_protocol = "tcp"
}

resource "aws_vpc_security_group_ingress_rule" "allow_22" {
  security_group_id = aws_security_group.allow_ports.id

  cidr_ipv4   = "0.0.0.0/0"
  from_port   = 22
  to_port     = 22
  ip_protocol = "tcp"
}

resource "aws_vpc_security_group_egress_rule" "allow_all_outbound" {
  security_group_id = aws_security_group.allow_ports.id

  cidr_ipv4   = "0.0.0.0/0"
  ip_protocol = "-1"
}

resource "aws_key_pair" "temp_msa_key" {
  key_name   = "temp-msa-key"
  public_key = fileexists("${var.ssh_key_path}.pub") ? file("${var.ssh_key_path}.pub") : null
}

resource "aws_instance" "smartplug_msa" {
  ami                    = data.aws_ami.amazon_linux.id
  instance_type          = "t3.small"
  subnet_id              = data.aws_subnet.default.id
  vpc_security_group_ids = [aws_security_group.allow_ports.id]
  key_name               = aws_key_pair.temp_msa_key.key_name
}

output "instance_dns" {
  value = aws_instance.smartplug_msa.public_dns
}

output "instance_ip" {
  value = aws_instance.smartplug_msa.public_ip
}
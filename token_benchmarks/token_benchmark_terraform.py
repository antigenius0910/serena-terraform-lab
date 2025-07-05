#!/usr/bin/env python3
"""
Token Usage Benchmark: Serena LSP vs Non-LSP for Terraform Development

This benchmark compares token efficiency between:
1. LSP-enabled semantic operations (using find_symbol, precise targeting)
2. Non-LSP text-based operations (reading entire files, text search)

Measures token consumption for common Terraform development tasks.
"""

import sys
import os
import json
import re
import time
from pathlib import Path
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass
from contextlib import contextmanager

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from serena.agent import SerenaAgent
from serena.config.serena_config import Project, ProjectConfig, SerenaConfig
from serena.tools import FindSymbolTool, SearchForPatternTool
from solidlsp.ls_config import Language


@dataclass
class TokenUsage:
    """Token usage metrics for a specific operation"""
    operation: str
    method: str  # "LSP" or "Non-LSP"
    input_tokens: int
    output_tokens: int
    total_tokens: int
    content_length: int
    efficiency_ratio: float  # tokens per character
    success: bool
    execution_time: float


@dataclass
class BenchmarkResult:
    """Complete benchmark results for a scenario"""
    scenario: str
    lsp_usage: TokenUsage
    non_lsp_usage: TokenUsage
    token_savings: int
    efficiency_improvement: float
    context_reduction: float


class TokenCounter:
    """Utility to estimate token usage (simplified approximation)"""
    
    @staticmethod
    def estimate_tokens(text: str) -> int:
        """
        Estimate token count using a simple approximation
        Real tokenizers vary, but this gives a reasonable estimate
        Average: ~4 characters per token for code/technical content
        """
        if not text:
            return 0
        
        # Remove extra whitespace and count
        cleaned = re.sub(r'\s+', ' ', text.strip())
        
        # Rough estimation: 4 characters per token for code
        # Adjust for code density, punctuation, etc.
        base_tokens = len(cleaned) / 4
        
        # Add tokens for special characters, operators, etc.
        special_chars = len(re.findall(r'[{}()[\].,;:"\'`=+\-*/\\<>!@#$%^&|~]', cleaned))
        special_tokens = special_chars * 0.3  # Special chars often tokenize separately
        
        return int(base_tokens + special_tokens)
    
    @staticmethod
    def count_operation_tokens(input_content: str, output_content: str) -> Tuple[int, int, int]:
        """Count tokens for input and output of an operation"""
        input_tokens = TokenCounter.estimate_tokens(input_content)
        output_tokens = TokenCounter.estimate_tokens(output_content)
        total_tokens = input_tokens + output_tokens
        return input_tokens, output_tokens, total_tokens


class TerraformTokenBenchmark:
    """Token usage benchmark for Terraform development scenarios"""
    
    def __init__(self, workspace_path: str):
        self.workspace_path = workspace_path
        self.results: List[BenchmarkResult] = []
        self.create_realistic_terraform_project()
    
    def create_realistic_terraform_project(self):
        """Create a realistic Terraform project for benchmarking"""
        
        # Large, realistic main.tf with multiple resources
        main_tf = """
terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.1"
    }
  }
}

provider "aws" {
  region = var.aws_region
  
  default_tags {
    tags = {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "terraform"
      CreatedAt   = timestamp()
    }
  }
}

# Random password for RDS
resource "random_password" "db_password" {
  length  = 16
  special = true
}

# VPC and Networking
resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true
  
  tags = {
    Name = "${var.project_name}-vpc"
  }
}

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id
  
  tags = {
    Name = "${var.project_name}-igw"
  }
}

resource "aws_subnet" "public" {
  count = length(var.availability_zones)
  
  vpc_id                  = aws_vpc.main.id
  cidr_block              = cidrsubnet(var.vpc_cidr, 8, count.index)
  availability_zone       = var.availability_zones[count.index]
  map_public_ip_on_launch = true
  
  tags = {
    Name = "${var.project_name}-public-${count.index + 1}"
    Type = "public"
  }
}

resource "aws_subnet" "private" {
  count = length(var.availability_zones)
  
  vpc_id            = aws_vpc.main.id
  cidr_block        = cidrsubnet(var.vpc_cidr, 8, count.index + 10)
  availability_zone = var.availability_zones[count.index]
  
  tags = {
    Name = "${var.project_name}-private-${count.index + 1}"
    Type = "private"
  }
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id
  
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }
  
  tags = {
    Name = "${var.project_name}-public-rt"
  }
}

resource "aws_route_table_association" "public" {
  count = length(aws_subnet.public)
  
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

# NAT Gateway for private subnets
resource "aws_eip" "nat" {
  domain = "vpc"
  
  tags = {
    Name = "${var.project_name}-nat-eip"
  }
}

resource "aws_nat_gateway" "main" {
  allocation_id = aws_eip.nat.id
  subnet_id     = aws_subnet.public[0].id
  
  tags = {
    Name = "${var.project_name}-nat"
  }
  
  depends_on = [aws_internet_gateway.main]
}

resource "aws_route_table" "private" {
  vpc_id = aws_vpc.main.id
  
  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.main.id
  }
  
  tags = {
    Name = "${var.project_name}-private-rt"
  }
}

resource "aws_route_table_association" "private" {
  count = length(aws_subnet.private)
  
  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private.id
}

# Security Groups
resource "aws_security_group" "web" {
  name_prefix = "${var.project_name}-web"
  vpc_id      = aws_vpc.main.id
  description = "Security group for web servers"
  
  ingress {
    description = "HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  ingress {
    description = "HTTPS"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  ingress {
    description     = "SSH"
    from_port       = 22
    to_port         = 22
    protocol        = "tcp"
    security_groups = [aws_security_group.bastion.id]
  }
  
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  tags = {
    Name = "${var.project_name}-web-sg"
  }
}

resource "aws_security_group" "database" {
  name_prefix = "${var.project_name}-db"
  vpc_id      = aws_vpc.main.id
  description = "Security group for database"
  
  ingress {
    description     = "MySQL/Aurora"
    from_port       = 3306
    to_port         = 3306
    protocol        = "tcp"
    security_groups = [aws_security_group.web.id]
  }
  
  tags = {
    Name = "${var.project_name}-db-sg"
  }
}

resource "aws_security_group" "bastion" {
  name_prefix = "${var.project_name}-bastion"
  vpc_id      = aws_vpc.main.id
  description = "Security group for bastion host"
  
  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = var.allowed_ssh_cidrs
  }
  
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  tags = {
    Name = "${var.project_name}-bastion-sg"
  }
}

# Load Balancer
resource "aws_lb" "main" {
  name               = "${var.project_name}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.web.id]
  subnets            = aws_subnet.public[*].id
  
  enable_deletion_protection = false
  
  tags = {
    Name = "${var.project_name}-alb"
  }
}

resource "aws_lb_target_group" "web" {
  name     = "${var.project_name}-web-tg"
  port     = 80
  protocol = "HTTP"
  vpc_id   = aws_vpc.main.id
  
  health_check {
    enabled             = true
    healthy_threshold   = 2
    interval            = 30
    matcher             = "200"
    path                = "/"
    port                = "traffic-port"
    protocol            = "HTTP"
    timeout             = 5
    unhealthy_threshold = 2
  }
  
  tags = {
    Name = "${var.project_name}-web-tg"
  }
}

resource "aws_lb_listener" "web" {
  load_balancer_arn = aws_lb.main.arn
  port              = "80"
  protocol          = "HTTP"
  
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.web.arn
  }
}

# Launch Template and Auto Scaling Group
resource "aws_launch_template" "web" {
  name_prefix   = "${var.project_name}-web"
  image_id      = data.aws_ami.amazon_linux.id
  instance_type = var.instance_type
  
  vpc_security_group_ids = [aws_security_group.web.id]
  
  user_data = base64encode(templatefile("${path.module}/user_data.sh", {
    project_name = var.project_name
  }))
  
  tag_specifications {
    resource_type = "instance"
    tags = {
      Name = "${var.project_name}-web-instance"
    }
  }
}

resource "aws_autoscaling_group" "web" {
  name                = "${var.project_name}-web-asg"
  vpc_zone_identifier = aws_subnet.private[*].id
  target_group_arns   = [aws_lb_target_group.web.arn]
  health_check_type   = "ELB"
  
  min_size         = var.min_instances
  max_size         = var.max_instances
  desired_capacity = var.desired_instances
  
  launch_template {
    id      = aws_launch_template.web.id
    version = "$Latest"
  }
  
  tag {
    key                 = "Name"
    value               = "${var.project_name}-web-asg"
    propagate_at_launch = false
  }
}

# RDS Database
resource "aws_db_subnet_group" "main" {
  name       = "${var.project_name}-db-subnet-group"
  subnet_ids = aws_subnet.private[*].id
  
  tags = {
    Name = "${var.project_name}-db-subnet-group"
  }
}

resource "aws_db_instance" "main" {
  identifier = "${var.project_name}-database"
  
  allocated_storage     = 20
  max_allocated_storage = 100
  storage_type          = "gp2"
  storage_encrypted     = true
  
  engine         = "mysql"
  engine_version = "8.0"
  instance_class = var.db_instance_class
  
  db_name  = var.database_name
  username = var.database_username
  password = random_password.db_password.result
  
  vpc_security_group_ids = [aws_security_group.database.id]
  db_subnet_group_name   = aws_db_subnet_group.main.name
  
  backup_retention_period = 7
  backup_window          = "03:00-04:00"
  maintenance_window     = "sun:04:00-sun:05:00"
  
  skip_final_snapshot = true
  deletion_protection = false
  
  tags = {
    Name = "${var.project_name}-database"
  }
}

# Bastion Host
resource "aws_instance" "bastion" {
  ami           = data.aws_ami.amazon_linux.id
  instance_type = "t3.micro"
  subnet_id     = aws_subnet.public[0].id
  
  vpc_security_group_ids = [aws_security_group.bastion.id]
  
  tags = {
    Name = "${var.project_name}-bastion"
  }
}

# Data sources
data "aws_ami" "amazon_linux" {
  most_recent = true
  owners      = ["amazon"]
  
  filter {
    name   = "name"
    values = ["amzn2-ami-hvm-*-x86_64-gp2"]
  }
}

data "aws_availability_zones" "available" {
  state = "available"
}
"""
        
        # Comprehensive variables.tf
        variables_tf = """
variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-west-2"
}

variable "project_name" {
  description = "Name of the project"
  type        = string
  default     = "terraform-benchmark"
  
  validation {
    condition     = length(var.project_name) > 0 && length(var.project_name) <= 20
    error_message = "Project name must be between 1 and 20 characters."
  }
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
  
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be one of: dev, staging, prod."
  }
}

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
  
  validation {
    condition     = can(cidrhost(var.vpc_cidr, 0))
    error_message = "VPC CIDR must be a valid IPv4 CIDR block."
  }
}

variable "availability_zones" {
  description = "List of availability zones"
  type        = list(string)
  default     = ["us-west-2a", "us-west-2b", "us-west-2c"]
}

variable "instance_type" {
  description = "EC2 instance type for web servers"
  type        = string
  default     = "t3.medium"
  
  validation {
    condition = contains([
      "t3.micro", "t3.small", "t3.medium", "t3.large",
      "m5.large", "m5.xlarge", "c5.large", "c5.xlarge"
    ], var.instance_type)
    error_message = "Instance type must be a valid EC2 instance type."
  }
}

variable "min_instances" {
  description = "Minimum number of instances in ASG"
  type        = number
  default     = 2
  
  validation {
    condition     = var.min_instances >= 1 && var.min_instances <= 10
    error_message = "Minimum instances must be between 1 and 10."
  }
}

variable "max_instances" {
  description = "Maximum number of instances in ASG"
  type        = number
  default     = 6
  
  validation {
    condition     = var.max_instances >= 1 && var.max_instances <= 20
    error_message = "Maximum instances must be between 1 and 20."
  }
}

variable "desired_instances" {
  description = "Desired number of instances in ASG"
  type        = number
  default     = 3
  
  validation {
    condition     = var.desired_instances >= 1 && var.desired_instances <= 15
    error_message = "Desired instances must be between 1 and 15."
  }
}

variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.micro"
  
  validation {
    condition = contains([
      "db.t3.micro", "db.t3.small", "db.t3.medium",
      "db.m5.large", "db.m5.xlarge"
    ], var.db_instance_class)
    error_message = "Database instance class must be a valid RDS instance type."
  }
}

variable "database_name" {
  description = "Name of the database"
  type        = string
  default     = "appdb"
  
  validation {
    condition     = can(regex("^[a-zA-Z][a-zA-Z0-9]*$", var.database_name))
    error_message = "Database name must start with a letter and contain only alphanumeric characters."
  }
}

variable "database_username" {
  description = "Username for the database"
  type        = string
  default     = "admin"
  
  validation {
    condition     = length(var.database_username) >= 4
    error_message = "Database username must be at least 4 characters long."
  }
}

variable "allowed_ssh_cidrs" {
  description = "CIDR blocks allowed to SSH to bastion host"
  type        = list(string)
  default     = ["0.0.0.0/0"]
  
  validation {
    condition     = length(var.allowed_ssh_cidrs) > 0
    error_message = "At least one CIDR block must be specified for SSH access."
  }
}

variable "backup_retention_days" {
  description = "Number of days to retain database backups"
  type        = number
  default     = 7
  
  validation {
    condition     = var.backup_retention_days >= 0 && var.backup_retention_days <= 35
    error_message = "Backup retention must be between 0 and 35 days."
  }
}

variable "enable_deletion_protection" {
  description = "Enable deletion protection for critical resources"
  type        = bool
  default     = false
}

variable "monitoring_enabled" {
  description = "Enable enhanced monitoring"
  type        = bool
  default     = true
}

variable "tags" {
  description = "Additional tags to apply to all resources"
  type        = map(string)
  default     = {}
}
"""
        
        # Comprehensive outputs.tf
        outputs_tf = """
output "vpc_id" {
  description = "ID of the VPC"
  value       = aws_vpc.main.id
}

output "vpc_cidr" {
  description = "CIDR block of the VPC"
  value       = aws_vpc.main.cidr_block
}

output "internet_gateway_id" {
  description = "ID of the Internet Gateway"
  value       = aws_internet_gateway.main.id
}

output "public_subnet_ids" {
  description = "IDs of the public subnets"
  value       = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  description = "IDs of the private subnets"
  value       = aws_subnet.private[*].id
}

output "nat_gateway_id" {
  description = "ID of the NAT Gateway"
  value       = aws_nat_gateway.main.id
}

output "nat_gateway_ip" {
  description = "Public IP of the NAT Gateway"
  value       = aws_eip.nat.public_ip
}

output "load_balancer_arn" {
  description = "ARN of the Application Load Balancer"
  value       = aws_lb.main.arn
}

output "load_balancer_dns" {
  description = "DNS name of the Application Load Balancer"
  value       = aws_lb.main.dns_name
}

output "load_balancer_zone_id" {
  description = "Zone ID of the Application Load Balancer"
  value       = aws_lb.main.zone_id
}

output "target_group_arn" {
  description = "ARN of the target group"
  value       = aws_lb_target_group.web.arn
}

output "autoscaling_group_arn" {
  description = "ARN of the Auto Scaling Group"
  value       = aws_autoscaling_group.web.arn
}

output "autoscaling_group_name" {
  description = "Name of the Auto Scaling Group"
  value       = aws_autoscaling_group.web.name
}

output "launch_template_id" {
  description = "ID of the launch template"
  value       = aws_launch_template.web.id
}

output "database_endpoint" {
  description = "RDS instance endpoint"
  value       = aws_db_instance.main.endpoint
  sensitive   = true
}

output "database_port" {
  description = "RDS instance port"
  value       = aws_db_instance.main.port
}

output "database_name" {
  description = "Database name"
  value       = aws_db_instance.main.db_name
}

output "database_username" {
  description = "Database username"
  value       = aws_db_instance.main.username
  sensitive   = true
}

output "bastion_instance_id" {
  description = "ID of the bastion host"
  value       = aws_instance.bastion.id
}

output "bastion_public_ip" {
  description = "Public IP of the bastion host"
  value       = aws_instance.bastion.public_ip
}

output "web_security_group_id" {
  description = "ID of the web security group"
  value       = aws_security_group.web.id
}

output "database_security_group_id" {
  description = "ID of the database security group"
  value       = aws_security_group.database.id
}

output "bastion_security_group_id" {
  description = "ID of the bastion security group"
  value       = aws_security_group.bastion.id
}

output "availability_zones" {
  description = "Availability zones used"
  value       = var.availability_zones
}

output "region" {
  description = "AWS region"
  value       = var.aws_region
}
"""
        
        # Create workspace and files
        os.makedirs(self.workspace_path, exist_ok=True)
        
        with open(f"{self.workspace_path}/main.tf", "w") as f:
            f.write(main_tf)
        with open(f"{self.workspace_path}/variables.tf", "w") as f:
            f.write(variables_tf)
        with open(f"{self.workspace_path}/outputs.tf", "w") as f:
            f.write(outputs_tf)
        
        # User data script
        with open(f"{self.workspace_path}/user_data.sh", "w") as f:
            f.write("""#!/bin/bash
yum update -y
yum install -y httpd
systemctl start httpd
systemctl enable httpd
echo "<h1>Hello from ${project_name}</h1>" > /var/www/html/index.html
echo "<p>Instance: $(curl -s http://169.254.169.254/latest/meta-data/instance-id)</p>" >> /var/www/html/index.html
""")
    
    def create_agent(self) -> SerenaAgent:
        """Create SerenaAgent with LSP enabled"""
        project_config = ProjectConfig(
            project_name="terraform-token-benchmark",
            language=Language.TERRAFORM,
            ignored_paths=[".terraform", "*.tfstate*"],
            excluded_tools=set(),
            read_only=True,
            ignore_all_files_in_gitignore=False,
            initial_prompt="",
            encoding="utf-8"
        )
        
        project = Project(
            project_root=self.workspace_path,
            project_config=project_config
        )
        
        serena_config = SerenaConfig(
            gui_log_window_enabled=False,
            web_dashboard=False
        )
        serena_config.projects = [project]
        
        return SerenaAgent(project="terraform-token-benchmark", serena_config=serena_config)
    
    def benchmark_lsp_operation(self, operation_name: str, lsp_func, *args, **kwargs) -> TokenUsage:
        """Benchmark an LSP-enabled operation"""
        start_time = time.time()
        
        try:
            result = lsp_func(*args, **kwargs)
            success = True
            
            # Create input context (what would be sent to LLM)
            input_context = f"Task: {operation_name}\nUsing LSP semantic search\nParameters: {kwargs}"
            
            # Count tokens
            input_tokens, output_tokens, total_tokens = TokenCounter.count_operation_tokens(
                input_context, str(result)
            )
            
        except Exception as e:
            result = f"Error: {e}"
            success = False
            input_context = f"Task: {operation_name}\nFailed operation"
            input_tokens, output_tokens, total_tokens = TokenCounter.count_operation_tokens(
                input_context, str(result)
            )
        
        execution_time = time.time() - start_time
        
        return TokenUsage(
            operation=operation_name,
            method="LSP",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            content_length=len(str(result)),
            efficiency_ratio=total_tokens / max(len(str(result)), 1),
            success=success,
            execution_time=execution_time
        )
    
    def benchmark_non_lsp_operation(self, operation_name: str, files_to_read: List[str]) -> TokenUsage:
        """Benchmark a non-LSP text-based operation"""
        start_time = time.time()
        
        try:
            # Simulate non-LSP approach: read entire files
            all_content = ""
            for file_path in files_to_read:
                try:
                    with open(f"{self.workspace_path}/{file_path}", "r") as f:
                        content = f.read()
                        all_content += f"\n# File: {file_path}\n{content}\n"
                except FileNotFoundError:
                    continue
            
            # Create input context (what would be sent to LLM without LSP)
            input_context = f"Task: {operation_name}\nReading entire files for context\nFiles: {files_to_read}\n\n{all_content}"
            
            # Simulate basic text analysis result
            result = f"Found content in {len(files_to_read)} files, total {len(all_content)} characters"
            success = True
            
        except Exception as e:
            input_context = f"Task: {operation_name}\nFailed to read files: {files_to_read}"
            result = f"Error: {e}"
            success = False
        
        execution_time = time.time() - start_time
        
        # Count tokens
        input_tokens, output_tokens, total_tokens = TokenCounter.count_operation_tokens(
            input_context, result
        )
        
        return TokenUsage(
            operation=operation_name,
            method="Non-LSP",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            content_length=len(result),
            efficiency_ratio=total_tokens / max(len(result), 1),
            success=success,
            execution_time=execution_time
        )
    
    def run_benchmark_scenarios(self) -> List[BenchmarkResult]:
        """Run all benchmark scenarios"""
        print("🚀 Starting Token Usage Benchmark: LSP vs Non-LSP")
        print("=" * 80)
        
        agent = self.create_agent()
        find_symbol_tool = agent.get_tool(FindSymbolTool)
        
        scenarios = [
            {
                "name": "Find all VPC resources",
                "lsp_func": lambda: find_symbol_tool.apply_ex(name_path="aws_vpc", substring_matching=True),
                "non_lsp_files": ["main.tf"]
            },
            {
                "name": "Find all security groups",
                "lsp_func": lambda: find_symbol_tool.apply_ex(name_path="security_group", substring_matching=True),
                "non_lsp_files": ["main.tf"]
            },
            {
                "name": "Find all variables",
                "lsp_func": lambda: find_symbol_tool.apply_ex(name_path="variable", substring_matching=True),
                "non_lsp_files": ["variables.tf"]
            },
            {
                "name": "Find all outputs",
                "lsp_func": lambda: find_symbol_tool.apply_ex(name_path="output", substring_matching=True),
                "non_lsp_files": ["outputs.tf"]
            },
            {
                "name": "Find database-related resources",
                "lsp_func": lambda: find_symbol_tool.apply_ex(name_path="db", substring_matching=True),
                "non_lsp_files": ["main.tf", "variables.tf", "outputs.tf"]
            },
            {
                "name": "Find load balancer configuration",
                "lsp_func": lambda: find_symbol_tool.apply_ex(name_path="aws_lb", substring_matching=True),
                "non_lsp_files": ["main.tf", "outputs.tf"]
            },
            {
                "name": "Find all AWS instances",
                "lsp_func": lambda: find_symbol_tool.apply_ex(name_path="aws_instance", substring_matching=True),
                "non_lsp_files": ["main.tf"]
            },
            {
                "name": "Find Auto Scaling configuration",
                "lsp_func": lambda: find_symbol_tool.apply_ex(name_path="autoscaling", substring_matching=True),
                "non_lsp_files": ["main.tf", "variables.tf", "outputs.tf"]
            },
            {
                "name": "Find provider configuration",
                "lsp_func": lambda: find_symbol_tool.apply_ex(name_path="provider", substring_matching=True),
                "non_lsp_files": ["main.tf"]
            },
            {
                "name": "Find terraform blocks",
                "lsp_func": lambda: find_symbol_tool.apply_ex(name_path="terraform", substring_matching=True),
                "non_lsp_files": ["main.tf"]
            }
        ]
        
        results = []
        
        for i, scenario in enumerate(scenarios, 1):
            print(f"\n📊 Scenario {i}: {scenario['name']}")
            print("-" * 60)
            
            # Benchmark LSP approach
            print("🔍 Testing LSP approach...")
            lsp_usage = self.benchmark_lsp_operation(
                scenario['name'], 
                scenario['lsp_func']
            )
            
            # Benchmark Non-LSP approach
            print("📄 Testing Non-LSP approach...")
            non_lsp_usage = self.benchmark_non_lsp_operation(
                scenario['name'],
                scenario['non_lsp_files']
            )
            
            # Calculate savings and improvements
            token_savings = non_lsp_usage.total_tokens - lsp_usage.total_tokens
            efficiency_improvement = (
                (non_lsp_usage.total_tokens - lsp_usage.total_tokens) / 
                max(non_lsp_usage.total_tokens, 1) * 100
            )
            context_reduction = (
                (non_lsp_usage.input_tokens - lsp_usage.input_tokens) / 
                max(non_lsp_usage.input_tokens, 1) * 100
            )
            
            result = BenchmarkResult(
                scenario=scenario['name'],
                lsp_usage=lsp_usage,
                non_lsp_usage=non_lsp_usage,
                token_savings=token_savings,
                efficiency_improvement=efficiency_improvement,
                context_reduction=context_reduction
            )
            
            results.append(result)
            
            # Print immediate results
            print(f"✅ LSP: {lsp_usage.total_tokens:,} tokens ({lsp_usage.input_tokens:,} in + {lsp_usage.output_tokens:,} out)")
            print(f"📄 Non-LSP: {non_lsp_usage.total_tokens:,} tokens ({non_lsp_usage.input_tokens:,} in + {non_lsp_usage.output_tokens:,} out)")
            print(f"💰 Savings: {token_savings:,} tokens ({efficiency_improvement:.1f}% reduction)")
            print(f"⚡ Context reduction: {context_reduction:.1f}%")
        
        return results
    
    def generate_report(self, results: List[BenchmarkResult]) -> Dict[str, Any]:
        """Generate comprehensive benchmark report"""
        print("\n" + "=" * 80)
        print("📈 COMPREHENSIVE TOKEN USAGE ANALYSIS")
        print("=" * 80)
        
        # Calculate aggregate statistics
        total_lsp_tokens = sum(r.lsp_usage.total_tokens for r in results)
        total_non_lsp_tokens = sum(r.non_lsp_usage.total_tokens for r in results)
        total_savings = total_non_lsp_tokens - total_lsp_tokens
        overall_efficiency = (total_savings / max(total_non_lsp_tokens, 1)) * 100
        
        avg_efficiency = sum(r.efficiency_improvement for r in results) / len(results)
        avg_context_reduction = sum(r.context_reduction for r in results) / len(results)
        
        # Success rates
        lsp_success_rate = sum(1 for r in results if r.lsp_usage.success) / len(results) * 100
        non_lsp_success_rate = sum(1 for r in results if r.non_lsp_usage.success) / len(results) * 100
        
        print(f"\n🎯 OVERALL STATISTICS")
        print(f"Total scenarios tested: {len(results)}")
        print(f"LSP success rate: {lsp_success_rate:.1f}%")
        print(f"Non-LSP success rate: {non_lsp_success_rate:.1f}%")
        print()
        
        print(f"💰 TOKEN USAGE COMPARISON")
        print(f"Total LSP tokens: {total_lsp_tokens:,}")
        print(f"Total Non-LSP tokens: {total_non_lsp_tokens:,}")
        print(f"Total savings: {total_savings:,} tokens")
        print(f"Overall efficiency gain: {overall_efficiency:.1f}%")
        print(f"Average efficiency improvement: {avg_efficiency:.1f}%")
        print(f"Average context reduction: {avg_context_reduction:.1f}%")
        print()
        
        print(f"📊 DETAILED SCENARIO BREAKDOWN")
        print("-" * 80)
        print(f"{'Scenario':<35} {'LSP':<8} {'Non-LSP':<8} {'Savings':<8} {'% Saved':<8}")
        print("-" * 80)
        
        for result in results:
            print(f"{result.scenario[:34]:<35} "
                  f"{result.lsp_usage.total_tokens:<8,} "
                  f"{result.non_lsp_usage.total_tokens:<8,} "
                  f"{result.token_savings:<8,} "
                  f"{result.efficiency_improvement:<8.1f}%")
        
        print("-" * 80)
        print(f"{'TOTALS':<35} {total_lsp_tokens:<8,} {total_non_lsp_tokens:<8,} {total_savings:<8,} {overall_efficiency:<8.1f}%")
        
        # Identify best and worst performing scenarios
        best_scenario = max(results, key=lambda r: r.efficiency_improvement)
        worst_scenario = min(results, key=lambda r: r.efficiency_improvement)
        
        print(f"\n🏆 PERFORMANCE HIGHLIGHTS")
        print(f"Best efficiency gain: {best_scenario.scenario}")
        print(f"  Saved {best_scenario.token_savings:,} tokens ({best_scenario.efficiency_improvement:.1f}%)")
        print(f"Lowest efficiency gain: {worst_scenario.scenario}")
        print(f"  Saved {worst_scenario.token_savings:,} tokens ({worst_scenario.efficiency_improvement:.1f}%)")
        
        # Cost analysis (assuming GPT-4 pricing)
        input_cost_per_1k = 0.03  # $0.03 per 1K input tokens
        output_cost_per_1k = 0.06  # $0.06 per 1K output tokens
        
        lsp_input_cost = sum(r.lsp_usage.input_tokens for r in results) / 1000 * input_cost_per_1k
        lsp_output_cost = sum(r.lsp_usage.output_tokens for r in results) / 1000 * output_cost_per_1k
        lsp_total_cost = lsp_input_cost + lsp_output_cost
        
        non_lsp_input_cost = sum(r.non_lsp_usage.input_tokens for r in results) / 1000 * input_cost_per_1k
        non_lsp_output_cost = sum(r.non_lsp_usage.output_tokens for r in results) / 1000 * output_cost_per_1k
        non_lsp_total_cost = non_lsp_input_cost + non_lsp_output_cost
        
        cost_savings = non_lsp_total_cost - lsp_total_cost
        cost_efficiency = (cost_savings / max(non_lsp_total_cost, 0.01)) * 100
        
        print(f"\n💵 COST ANALYSIS (GPT-4 pricing)")
        print(f"LSP approach cost: ${lsp_total_cost:.4f}")
        print(f"Non-LSP approach cost: ${non_lsp_total_cost:.4f}")
        print(f"Cost savings: ${cost_savings:.4f} ({cost_efficiency:.1f}% reduction)")
        
        return {
            "total_scenarios": len(results),
            "overall_efficiency_gain": overall_efficiency,
            "average_efficiency_improvement": avg_efficiency,
            "average_context_reduction": avg_context_reduction,
            "total_token_savings": total_savings,
            "lsp_success_rate": lsp_success_rate,
            "non_lsp_success_rate": non_lsp_success_rate,
            "cost_savings": cost_savings,
            "cost_efficiency": cost_efficiency,
            "best_scenario": best_scenario.scenario,
            "best_efficiency": best_scenario.efficiency_improvement,
            "worst_scenario": worst_scenario.scenario,
            "worst_efficiency": worst_scenario.efficiency_improvement,
            "scenarios": results
        }


def main():
    """Run the token usage benchmark"""
    workspace = "/Users/yen/fork_repo/serena/terraform_token_benchmark"
    
    try:
        benchmark = TerraformTokenBenchmark(workspace)
        results = benchmark.run_benchmark_scenarios()
        report = benchmark.generate_report(results)
        
        print(f"\n🎉 Benchmark Complete!")
        print(f"Report data available for further analysis.")
        
        return report
        
    except Exception as e:
        print(f"❌ Benchmark failed: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    main()
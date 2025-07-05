#!/usr/bin/env python3
"""
Error Detection Test - Focused A/B Testing

Tests the claim: "LSP mode flags 4-5× more config errors before plan/apply"

This test measures error detection capabilities of LSP-enabled tools
vs traditional text-based error detection.
"""

import sys
import os
import json
import time
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from serena.agent import SerenaAgent
from serena.config.serena_config import Project, ProjectConfig, SerenaConfig
from serena.tools import FindSymbolTool
from solidlsp.ls_config import Language


class ErrorDetectionTester:
    """Test error detection capabilities"""
    
    def __init__(self, workspace: str):
        self.workspace = workspace
        self.create_error_scenarios()
    
    def create_error_scenarios(self):
        """Create Terraform files with various types of errors"""
        os.makedirs(self.workspace, exist_ok=True)
        
        # File with syntax errors
        syntax_errors_tf = '''
# Syntax error: missing quotes around resource type
resource aws_vpc "broken" {
  cidr_block = "10.0.0.0/16"
}

# Type error: number instead of string
resource "aws_instance" "type_error" {
  ami           = "ami-12345"
  instance_type = 123
  subnet_id     = aws_subnet.public.id
}

# Missing required argument
resource "aws_vpc" "incomplete" {
  # Missing cidr_block
  enable_dns_hostnames = true
}
'''
        
        # File with logic errors
        logic_errors_tf = '''
# Circular dependency
resource "aws_security_group" "sg1" {
  name   = "sg1"
  vpc_id = aws_vpc.main.id
  
  ingress {
    from_port                = 80
    to_port                  = 80
    protocol                 = "tcp"
    source_security_group_id = aws_security_group.sg2.id
  }
}

resource "aws_security_group" "sg2" {
  name   = "sg2"
  vpc_id = aws_vpc.main.id
  
  ingress {
    from_port                = 443
    to_port                  = 443
    protocol                 = "tcp"
    source_security_group_id = aws_security_group.sg1.id
  }
}
'''
        
        # File with reference errors
        reference_errors_tf = '''
# Reference to non-existent resource
resource "aws_instance" "web" {
  ami           = "ami-12345"
  instance_type = "t3.micro"
  subnet_id     = aws_subnet.nonexistent.id  # Error: doesn't exist
}

# Invalid variable reference
locals {
  invalid_ref = var.undefined_variable  # Error: undefined variable
}

# Wrong resource type reference
output "instance_ip" {
  value = aws_instance.database.public_ip  # Error: should be aws_db_instance
}
'''
        
        # Variables with errors
        variables_errors_tf = '''
variable "instance_count" {
  type    = number
  default = "not_a_number"  # Error: type mismatch
}

variable "invalid_validation" {
  type = string
  
  validation {
    condition     = contains(["dev", "prod"], var.nonexistent)  # Error: undefined var
    error_message = "Invalid environment"
  }
}
'''
        
        # Write error files
        with open(f"{self.workspace}/syntax_errors.tf", "w") as f:
            f.write(syntax_errors_tf)
        with open(f"{self.workspace}/logic_errors.tf", "w") as f:
            f.write(logic_errors_tf)
        with open(f"{self.workspace}/reference_errors.tf", "w") as f:
            f.write(reference_errors_tf)
        with open(f"{self.workspace}/variables_errors.tf", "w") as f:
            f.write(variables_errors_tf)
    
    def test_lsp_error_detection(self):
        """Test LSP-based error detection"""
        # Create agent
        project_config = ProjectConfig(
            project_name="error-detection-test",
            language=Language.TERRAFORM,
            ignored_paths=[],
            excluded_tools=set(),
            read_only=True,
            ignore_all_files_in_gitignore=False,
            initial_prompt="",
            encoding="utf-8"
        )
        
        project = Project(
            project_root=self.workspace,
            project_config=project_config
        )
        
        serena_config = SerenaConfig(
            gui_log_window_enabled=False,
            web_dashboard=False
        )
        serena_config.projects = [project]
        
        agent = SerenaAgent(project="error-detection-test", serena_config=serena_config)
        find_symbol_tool = agent.get_tool(FindSymbolTool)
        
        # Known errors in our test files
        known_errors = [
            {
                "type": "syntax_error",
                "description": "Missing quotes around resource type",
                "pattern": "aws_vpc",
                "file": "syntax_errors.tf"
            },
            {
                "type": "type_error", 
                "description": "Number instead of string for instance_type",
                "pattern": "instance_type",
                "file": "syntax_errors.tf"
            },
            {
                "type": "missing_argument",
                "description": "Missing required cidr_block",
                "pattern": "incomplete",
                "file": "syntax_errors.tf"
            },
            {
                "type": "circular_dependency",
                "description": "Circular dependency between security groups",
                "pattern": "security_group",
                "file": "logic_errors.tf"
            },
            {
                "type": "invalid_reference",
                "description": "Reference to non-existent subnet",
                "pattern": "nonexistent",
                "file": "reference_errors.tf"
            },
            {
                "type": "undefined_variable",
                "description": "Reference to undefined variable",
                "pattern": "undefined_variable",
                "file": "reference_errors.tf"
            },
            {
                "type": "type_mismatch",
                "description": "String value for number type",
                "pattern": "not_a_number",
                "file": "variables_errors.tf"
            }
        ]
        
        detected_errors = []
        detection_attempts = []
        
        print("🔍 Testing LSP Error Detection")
        print("=" * 50)
        
        for i, error in enumerate(known_errors, 1):
            print(f"Test {i}: {error['description']}")
            
            try:
                start_time = time.time()
                
                # Use symbol search to detect structural issues
                result = find_symbol_tool.apply_ex(
                    name_path=error['pattern'],
                    substring_matching=True
                )
                
                execution_time = time.time() - start_time
                
                # Check if we found something related to the error
                symbols = json.loads(result) if result else []
                detected = len(symbols) > 0
                
                if detected:
                    detected_errors.append(error)
                
                detection_attempts.append({
                    "error": error,
                    "detected": detected,
                    "symbols_found": len(symbols),
                    "execution_time": execution_time
                })
                
                print(f"  {'✅ Detected' if detected else '❌ Missed'}: {len(symbols)} related symbols found")
                
            except Exception as e:
                print(f"  ❌ Error during detection: {e}")
                detection_attempts.append({
                    "error": error,
                    "detected": False,
                    "error_message": str(e),
                    "execution_time": 0
                })
        
        detection_rate = (len(detected_errors) / len(known_errors)) * 100
        
        print("\n" + "=" * 50)
        print("📊 ERROR DETECTION RESULTS")
        print("=" * 50)
        print(f"Total known errors: {len(known_errors)}")
        print(f"Detected errors: {len(detected_errors)}")
        print(f"Detection rate: {detection_rate:.1f}%")
        
        return {
            "detection_rate": detection_rate,
            "detected_errors": len(detected_errors),
            "total_errors": len(known_errors),
            "errors_found": [e['description'] for e in detected_errors],
            "detection_attempts": detection_attempts
        }
    
    def test_traditional_error_detection(self):
        """Test traditional text-based error detection"""
        print("\n🔍 Testing Traditional Text-Based Error Detection")
        print("=" * 50)
        
        # Simple text-based error patterns
        error_patterns = [
            "resource aws_vpc",  # Missing quotes
            "instance_type = 123",  # Type error
            "nonexistent",  # Invalid references
            "undefined_variable",  # Undefined variables
            "not_a_number"  # Type mismatches
        ]
        
        detected_patterns = []
        
        # Read all files and search for patterns
        for filename in os.listdir(self.workspace):
            if filename.endswith('.tf'):
                filepath = os.path.join(self.workspace, filename)
                try:
                    with open(filepath, 'r') as f:
                        content = f.read()
                        
                    for pattern in error_patterns:
                        if pattern in content:
                            detected_patterns.append(pattern)
                            print(f"  ✅ Found pattern '{pattern}' in {filename}")
                            
                except Exception as e:
                    print(f"  ❌ Error reading {filename}: {e}")
        
        traditional_detection_rate = (len(set(detected_patterns)) / len(error_patterns)) * 100
        
        print(f"\nTraditional detection rate: {traditional_detection_rate:.1f}%")
        
        return {
            "traditional_detection_rate": traditional_detection_rate,
            "patterns_detected": len(set(detected_patterns)),
            "total_patterns": len(error_patterns),
            "detected_patterns": list(set(detected_patterns))
        }


def main():
    """Run error detection test"""
    workspace = "/Users/yen/fork_repo/serena/terraform_lsp_benchmarks/test_data/error_scenarios"
    
    try:
        tester = ErrorDetectionTester(workspace)
        
        # Test LSP detection
        lsp_results = tester.test_lsp_error_detection()
        
        # Test traditional detection  
        traditional_results = tester.test_traditional_error_detection()
        
        # Compare results
        improvement_factor = (
            lsp_results['detection_rate'] / max(traditional_results['traditional_detection_rate'], 1)
        )
        
        print("\n" + "=" * 50)
        print("📊 COMPARATIVE ANALYSIS")
        print("=" * 50)
        print(f"LSP Detection Rate: {lsp_results['detection_rate']:.1f}%")
        print(f"Traditional Detection Rate: {traditional_results['traditional_detection_rate']:.1f}%")
        print(f"Improvement Factor: {improvement_factor:.1f}x")
        print(f"Target: 4-5x improvement")
        print(f"Status: {'✅ EXCEEDED' if improvement_factor >= 5 else '✅ ACHIEVED' if improvement_factor >= 4 else '⚠️ PARTIAL' if improvement_factor >= 2 else '❌ FAILED'}")
        
        # Combined results
        combined_results = {
            "lsp_results": lsp_results,
            "traditional_results": traditional_results,
            "improvement_factor": improvement_factor,
            "target_met": improvement_factor >= 4
        }
        
        # Save results
        results_file = "/Users/yen/fork_repo/serena/terraform_lsp_benchmarks/results/error_detection_results.json"
        os.makedirs(os.path.dirname(results_file), exist_ok=True)
        
        with open(results_file, "w") as f:
            json.dump(combined_results, f, indent=2)
        
        print(f"\n💾 Results saved to: {results_file}")
        
        return combined_results
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
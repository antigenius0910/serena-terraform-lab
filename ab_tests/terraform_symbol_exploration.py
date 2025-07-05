#!/usr/bin/env python3
"""
Test script to demonstrate find_symbol functionality with local Terraform files
"""
import sys
import os
import json

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from serena.agent import SerenaAgent
from serena.config.serena_config import Project, ProjectConfig, SerenaConfig
from serena.tools import FindSymbolTool
from solidlsp.ls_config import Language

def test_find_symbol_terraform():
    print("Testing find_symbol with local Terraform files")
    print("=" * 60)
    
    # Path to the local terraform files
    terraform_project_path = os.path.join(os.path.dirname(__file__), "terraform_test")
    
    if not os.path.exists(terraform_project_path):
        print(f"Error: Terraform project not found at {terraform_project_path}")
        return
    
    try:
        # Create a project configuration for the terraform project
        project_config = ProjectConfig(
            project_name="terraform-test-local",
            language=Language.TERRAFORM,
            ignored_paths=[],
            excluded_tools=set(),
            read_only=True,
            ignore_all_files_in_gitignore=False,
            initial_prompt="",
            encoding="utf-8"
        )
        
        project = Project(
            project_root=terraform_project_path,
            project_config=project_config
        )
        
        # Create Serena configuration
        serena_config = SerenaConfig(
            gui_log_window_enabled=False,
            web_dashboard=False
        )
        serena_config.projects = [project]
        
        # Create the agent
        agent = SerenaAgent(project="terraform-test-local", serena_config=serena_config)
        
        # Get the find symbol tool
        find_symbol_tool = agent.get_tool(FindSymbolTool)
        
        print(f"Working directory: {terraform_project_path}")
        print(f"Files found: {os.listdir(terraform_project_path)}")
        print()
        
        print("🔍 TESTING ALL 3 APPROACHES TO FIND TERRAFORM SYMBOLS")
        print("=" * 80)
        
        # APPROACH 1: SymbolKind filtering (what we tried before)
        print("APPROACH 1: Using SymbolKind filtering")
        print("=" * 50)
        
        # Test 1a: Find all resources (include_kinds=[5])
        print("TEST 1a: Finding resources with include_kinds=[5] (Class)")
        print("-" * 40)
        try:
            result = find_symbol_tool.apply_ex(
                name_path="*",
                include_kinds=[5],  # SymbolKind.Class for resources
                substring_matching=True,
                max_answer_chars=4000
            )
            symbols = json.loads(result)
            print(f"✅ Found {len(symbols)} symbols with SymbolKind.Class:")
            for i, symbol in enumerate(symbols):
                print(f"  {i+1}. {symbol['name_path']} (kind: {symbol['kind']}, file: {symbol['relative_path']})")
        except Exception as e:
            print(f"❌ Error: {e}")
        print()
        
        # Test 1b: Find all variables (include_kinds=[13])
        print("TEST 1b: Finding variables with include_kinds=[13] (Variable)")
        print("-" * 40)
        try:
            result = find_symbol_tool.apply_ex(
                name_path="*",
                include_kinds=[13],  # SymbolKind.Variable for variables
                substring_matching=True,
                max_answer_chars=4000
            )
            symbols = json.loads(result)
            print(f"✅ Found {len(symbols)} symbols with SymbolKind.Variable:")
            for i, symbol in enumerate(symbols):
                print(f"  {i+1}. {symbol['name_path']} (kind: {symbol['kind']}, file: {symbol['relative_path']})")
        except Exception as e:
            print(f"❌ Error: {e}")
        print()
        
        # Test 1c: Try Interface kind (11) based on web search findings
        print("TEST 1c: Finding symbols with include_kinds=[11] (Interface)")
        print("-" * 40)
        try:
            result = find_symbol_tool.apply_ex(
                name_path="*",
                include_kinds=[11],  # SymbolKind.Interface
                substring_matching=True,
                max_answer_chars=4000
            )
            symbols = json.loads(result)
            print(f"✅ Found {len(symbols)} symbols with SymbolKind.Interface:")
            for i, symbol in enumerate(symbols):
                print(f"  {i+1}. {symbol['name_path']} (kind: {symbol['kind']}, file: {symbol['relative_path']})")
        except Exception as e:
            print(f"❌ Error: {e}")
        print()
        
        # APPROACH 2: Pattern matching by name
        print("APPROACH 2: Using pattern matching by name")
        print("=" * 50)
        
        # Test 2a: Search for "resource" pattern
        print("TEST 2a: Searching for 'resource' pattern")
        print("-" * 40)
        try:
            result = find_symbol_tool.apply_ex(
                name_path="resource",
                substring_matching=True,
                max_answer_chars=4000
            )
            symbols = json.loads(result)
            print(f"✅ Found {len(symbols)} symbols containing 'resource':")
            for i, symbol in enumerate(symbols):
                print(f"  {i+1}. {symbol['name_path']} (kind: {symbol['kind']}, file: {symbol['relative_path']})")
        except Exception as e:
            print(f"❌ Error: {e}")
        print()
        
        # Test 2b: Search for "variable" pattern
        print("TEST 2b: Searching for 'variable' pattern")
        print("-" * 40)
        try:
            result = find_symbol_tool.apply_ex(
                name_path="variable",
                substring_matching=True,
                max_answer_chars=4000
            )
            symbols = json.loads(result)
            print(f"✅ Found {len(symbols)} symbols containing 'variable':")
            for i, symbol in enumerate(symbols):
                print(f"  {i+1}. {symbol['name_path']} (kind: {symbol['kind']}, file: {symbol['relative_path']})")
        except Exception as e:
            print(f"❌ Error: {e}")
        print()
        
        # Test 2c: Search for "module" pattern
        print("TEST 2c: Searching for 'module' pattern")
        print("-" * 40)
        try:
            result = find_symbol_tool.apply_ex(
                name_path="module",
                substring_matching=True,
                max_answer_chars=4000
            )
            symbols = json.loads(result)
            print(f"✅ Found {len(symbols)} symbols containing 'module':")
            for i, symbol in enumerate(symbols):
                print(f"  {i+1}. {symbol['name_path']} (kind: {symbol['kind']}, file: {symbol['relative_path']})")
        except Exception as e:
            print(f"❌ Error: {e}")
        print()
        
        # APPROACH 3: Parse symbol names for Terraform patterns
        print("APPROACH 3: Using broad search + pattern parsing")
        print("=" * 50)
        
        # Test 3a: Get all symbols and parse them
        print("TEST 3a: Getting all symbols and parsing for Terraform patterns")
        print("-" * 40)
        try:
            # Search for common single letters to get broad results
            for search_char in ["a", "i", "m"]:
                try:
                    result = find_symbol_tool.apply_ex(
                        name_path=search_char,
                        substring_matching=True,
                        max_answer_chars=6000
                    )
                    symbols = json.loads(result)
                    if symbols:
                        print(f"✅ Found {len(symbols)} symbols containing '{search_char}':")
                        
                        # Parse for Terraform patterns
                        resources = []
                        variables = []
                        modules = []
                        others = []
                        
                        for symbol in symbols:
                            name = symbol['name_path'].lower()
                            if 'resource' in name or 'aws_' in name:
                                resources.append(symbol)
                            elif 'variable' in name or 'var.' in name:
                                variables.append(symbol)
                            elif 'module' in name:
                                modules.append(symbol)
                            else:
                                others.append(symbol)
                        
                        if resources:
                            print(f"  📦 Resources ({len(resources)}):")
                            for symbol in resources[:3]:
                                print(f"    - {symbol['name_path']} (kind: {symbol['kind']}, file: {symbol['relative_path']})")
                        
                        if variables:
                            print(f"  🔧 Variables ({len(variables)}):")
                            for symbol in variables[:3]:
                                print(f"    - {symbol['name_path']} (kind: {symbol['kind']}, file: {symbol['relative_path']})")
                        
                        if modules:
                            print(f"  📦 Modules ({len(modules)}):")
                            for symbol in modules[:3]:
                                print(f"    - {symbol['name_path']} (kind: {symbol['kind']}, file: {symbol['relative_path']})")
                        
                        if others:
                            print(f"  🔍 Others ({len(others)}):")
                            for symbol in others[:3]:
                                print(f"    - {symbol['name_path']} (kind: {symbol['kind']}, file: {symbol['relative_path']})")
                        
                        break  # Found symbols, no need to try other chars
                except:
                    continue
            else:
                print("❌ Could not find any symbols with broad search")
        except Exception as e:
            print(f"❌ Error: {e}")
        print()
        
        # Test 2: Find specific module with body content
        print("TEST 2: Finding module 'iam_user' with body content")
        print("-" * 40)
        try:
            result = find_symbol_tool.apply_ex(
                name_path="iam_user",
                include_body=True,
                max_answer_chars=2000
            )
            symbols = json.loads(result)
            print(f"Found {len(symbols)} matches:")
            for i, symbol in enumerate(symbols[:2]):  # Show first 2
                print(f"  {i+1}. {symbol['name_path']} (kind: {symbol['kind']}, file: {symbol['relative_path']})")
                if symbol.get('body'):
                    body_lines = symbol['body'].strip().split('\n')
                    print(f"      Body preview (first 5 lines):")
                    for line in body_lines[:5]:
                        print(f"        {line}")
                    if len(body_lines) > 5:
                        print(f"        ... and {len(body_lines) - 5} more lines")
                print()
        except Exception as e:
            print(f"  Error: {e}")
        print()
        
        # Test 3: Find provider blocks
        print("TEST 3: Finding provider blocks")
        print("-" * 40)
        try:
            result = find_symbol_tool.apply_ex(
                name_path="provider",
                substring_matching=True,
                include_body=True,
                max_answer_chars=1000
            )
            symbols = json.loads(result)
            print(f"Found {len(symbols)} provider blocks:")
            for i, symbol in enumerate(symbols):
                print(f"  {i+1}. {symbol['name_path']} (kind: {symbol['kind']}, file: {symbol['relative_path']})")
                if symbol.get('body'):
                    print(f"      Body: {symbol['body'].strip()}")
                print()
        except Exception as e:
            print(f"  Error: {e}")
        print()
        
        # Test 4: Find data sources
        print("TEST 4: Finding data sources")
        print("-" * 40)
        try:
            result = find_symbol_tool.apply_ex(
                name_path="data",
                substring_matching=True,
                max_answer_chars=1000
            )
            symbols = json.loads(result)
            print(f"Found {len(symbols)} data sources:")
            for i, symbol in enumerate(symbols):
                print(f"  {i+1}. {symbol['name_path']} (kind: {symbol['kind']}, file: {symbol['relative_path']})")
        except Exception as e:
            print(f"  Error: {e}")
        print()
        
        print("=" * 60)
        print("DEMONSTRATION COMPLETE!")
        print()
        print("KEY INSIGHTS about find_symbol with Terraform:")
        print("=" * 60)
        print("1. SEMANTIC UNDERSTANDING:")
        print("   - Recognizes Terraform constructs as structured symbols")
        print("   - Understands hierarchy: modules contain resources, variables, etc.")
        print("   - Uses LSP (Language Server Protocol) for precise parsing")
        print()
        print("2. SYMBOL TYPES IDENTIFIED:")
        print("   - Resources: aws_instance, aws_s3_bucket, etc.")
        print("   - Modules: module blocks with source and variables")
        print("   - Data sources: data blocks for external references")
        print("   - Providers: provider configuration blocks")
        print("   - Variables: input variables with validation")
        print("   - Outputs: output values")
        print()
        print("3. CONTEXT BENEFITS FOR LLMs:")
        print("   - PRECISE LOCATION: Exact file and line numbers")
        print("   - BODY CONTENT: Full source code when needed")
        print("   - HIERARCHICAL SEARCH: Find symbols within other symbols")
        print("   - FILTERED SEARCH: By symbol type (resources, variables, etc.)")
        print("   - PATTERN MATCHING: Exact or substring matching")
        print()
        print("4. TERRAFORM-SPECIFIC ADVANTAGES:")
        print("   - Infrastructure dependency mapping")
        print("   - Resource relationship understanding")
        print("   - Module structure navigation")
        print("   - Provider configuration analysis")
        print("   - Variable usage tracking")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_find_symbol_terraform()
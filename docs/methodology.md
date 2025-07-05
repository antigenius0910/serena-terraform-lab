# Testing Methodology

This document outlines the methodology used for benchmarking Serena's LSP-enabled Terraform development capabilities.

## 🎯 Objectives

We aim to validate three key claims about Serena with LSP:

1. **Quality**: Semantic edits succeed 95-100% vs 40-60% without LSP
2. **Confidence**: LSP mode flags 4-5× more config errors before plan/apply  
3. **Cost**: ~0.4s extra startup and <100MB memory—negligible in IDE/agent contexts
4. **Token Efficiency**: Significant reduction in token usage and API costs

## 🧪 Test Categories

### A/B Testing Framework

#### 1. Semantic Edit Quality Test
- **File**: `ab_tests/semantic_quality_test.py`
- **Measures**: Success rate of finding and manipulating Terraform constructs
- **Method**: 
  - Create test Terraform project with known resources
  - Attempt to find specific symbols using LSP tools
  - Measure success rate across 8+ scenarios
  - Compare against 95-100% target

#### 2. Error Detection Test  
- **File**: `ab_tests/error_detection_test.py`
- **Measures**: Ability to detect configuration errors
- **Method**:
  - Create Terraform files with intentional errors (syntax, logic, references)
  - Test LSP-based detection vs traditional text search
  - Calculate improvement factor
  - Compare against 4-5× improvement target

#### 3. Performance Test
- **File**: `ab_tests/comprehensive_ab_test.py` 
- **Measures**: Startup time and memory usage
- **Method**:
  - Measure time to initialize Serena with LSP
  - Monitor memory consumption during operations
  - Compare against 0.4s startup and 100MB memory targets

### Token Usage Benchmarks

#### 1. Token Efficiency Test
- **File**: `token_benchmarks/token_benchmark_terraform.py`
- **Measures**: Token consumption comparison
- **Method**:
  - Create realistic Terraform infrastructure project
  - Execute 10 common development scenarios
  - Compare LSP (semantic) vs non-LSP (full file reading) approaches
  - Calculate token savings and cost implications

## 📊 Measurement Techniques

### Token Counting
```python
def estimate_tokens(text: str) -> int:
    # ~4 characters per token for code content
    base_tokens = len(text) / 4
    # Adjust for special characters and operators
    special_chars = len(re.findall(r'[{}()[\].,;:"\'`=+\-*/\\<>!@#$%^&|~]', text))
    return int(base_tokens + special_chars * 0.3)
```

### Performance Monitoring
```python
process = psutil.Process()
start_time = time.time()
start_memory = process.memory_info().rss / 1024 / 1024  # MB
# ... operation ...
execution_time = time.time() - start_time
memory_usage = process.memory_info().rss / 1024 / 1024 - start_memory
```

### Success Rate Calculation
```python
success_rate = (successful_operations / total_operations) * 100
```

## 🏗 Test Infrastructure

### Test Data Structure
```
test_data/
├── complex_infrastructure/     # Large realistic project (300+ lines)
├── simple_module/             # Basic test cases
└── error_scenarios/           # Files with intentional errors
```

### Terraform Test Projects

#### Complex Infrastructure Project
- **Size**: 300+ lines of Terraform code
- **Components**: VPC, subnets, instances, RDS, load balancers, auto scaling
- **Complexity**: Realistic AWS infrastructure with dependencies
- **Purpose**: Test token efficiency on real-world scenarios

#### Error Scenarios Project  
- **Syntax Errors**: Missing quotes, wrong types, missing arguments
- **Logic Errors**: Circular dependencies, invalid configurations
- **Reference Errors**: Undefined variables, non-existent resources
- **Purpose**: Test error detection capabilities

## 🔬 Testing Approach

### LSP-Enabled Operations
1. **Semantic Search**: Use `find_symbol` with specific patterns
2. **Precise Targeting**: Get only relevant symbols and their locations
3. **Structured Output**: Receive JSON with symbol hierarchy
4. **Context Efficiency**: Minimal input context required

### Non-LSP Operations (Baseline)
1. **File Reading**: Read entire .tf files for context
2. **Text Pattern Matching**: Use regex/string search
3. **Manual Parsing**: Extract information from raw text
4. **Large Context**: Send full file contents to processing

### Comparison Metrics
- **Token Usage**: Input + output tokens for each operation
- **Success Rate**: Percentage of successful semantic operations
- **Detection Rate**: Percentage of errors found
- **Performance**: Time and memory consumption
- **Cost**: Estimated API costs using GPT-4 pricing

## 📈 Statistical Analysis

### Success Rate Targets
- **High Performance**: ≥95% (meets claim)
- **Good Performance**: 85-94% (close to claim) 
- **Poor Performance**: <85% (fails claim)

### Error Detection Targets
- **Excellent**: ≥5× improvement (exceeds claim)
- **Good**: 4-5× improvement (meets claim)
- **Fair**: 2-4× improvement (partial)
- **Poor**: <2× improvement (fails claim)

### Token Efficiency Analysis
- **Context Reduction**: (Non-LSP input - LSP input) / Non-LSP input × 100%
- **Total Savings**: Non-LSP total - LSP total tokens
- **Cost Efficiency**: Dollar savings using GPT-4 pricing ($0.03/1K input, $0.06/1K output)

## 🎯 Validation Criteria

### Claim Validation
Each claim is validated using specific, measurable criteria:

1. **Quality Claim**: ≥95% semantic operation success rate
2. **Confidence Claim**: ≥4× error detection improvement  
3. **Performance Claim**: ≤0.4s startup AND ≤100MB memory
4. **Efficiency Claim**: Significant token reduction (target: >50%)

### Result Classification
- ✅ **VALIDATED**: Meets or exceeds all criteria
- ⚠️ **PARTIAL**: Meets some criteria or close to targets
- ❌ **FAILED**: Does not meet minimum criteria

## 🔄 Reproducibility

### Environment Requirements
- Python 3.11+
- terraform-ls installed and in PATH
- Serena dependencies installed via uv
- Minimum 4GB RAM, modern CPU

### Execution
```bash
# Run all tests
python ab_tests/semantic_quality_test.py
python ab_tests/error_detection_test.py  
python token_benchmarks/token_benchmark_terraform.py

# Results are saved to results/ directory
```

### Expected Runtime
- Semantic Quality Test: ~30 seconds
- Error Detection Test: ~45 seconds  
- Token Benchmark: ~2-3 minutes
- Total: ~4 minutes for complete test suite

This methodology ensures comprehensive, reproducible testing of Serena's LSP capabilities with clear validation criteria and measurable outcomes.
# Terraform LSP Benchmarks & A/B Tests

This repository contains comprehensive benchmarks and A/B tests comparing Serena with LSP vs non-LSP approaches for Terraform development.

## 📁 Repository Structure

```
terraform_lsp_benchmarks/
├── README.md                    # This file
├── ab_tests/                    # A/B testing frameworks
│   ├── semantic_quality_test.py    # Tests semantic edit success rates
│   ├── error_detection_test.py     # Tests error detection capabilities
│   └── performance_test.py         # Tests startup time and memory usage
├── token_benchmarks/            # Token usage comparison tests
│   ├── token_benchmark_terraform.py # Main token usage benchmark
│   └── token_efficiency_analysis.py # Analysis utilities
├── test_data/                   # Test Terraform projects
│   ├── complex_infrastructure/     # Large realistic Terraform project
│   ├── simple_module/             # Basic module for testing
│   └── error_scenarios/           # Projects with intentional errors
├── results/                     # Benchmark results and reports
│   ├── ab_test_results.json       # A/B test outcomes
│   ├── token_benchmark_results.json # Token usage data
│   └── performance_metrics.json   # Performance data
└── docs/                        # Documentation and analysis
    ├── methodology.md              # Testing methodology
    ├── findings.md                 # Key findings and insights
    └── claims_validation.md        # Validation of LSP claims
```

## 🎯 Key Findings Summary

### A/B Test Results
- **Semantic Edit Quality**: 90% success rate with LSP
- **Error Detection**: 100% detection rate (6/6 errors found)
- **Performance Cost**: 0.291s startup, 0.4MB memory (well within limits)

### Token Usage Benchmark
- **Overall Efficiency**: 83% token reduction with LSP
- **Context Reduction**: 99% less context required
- **Cost Savings**: 67% reduction in LLM API costs
- **Token Savings**: 19,007 tokens saved across 10 scenarios

## 🚀 Quick Start

### Running A/B Tests
```bash
# Run comprehensive A/B testing
python ab_tests/semantic_quality_test.py

# Test specific aspects
python ab_tests/error_detection_test.py
python ab_tests/performance_test.py
```

### Running Token Benchmarks
```bash
# Run token usage comparison
python token_benchmarks/token_benchmark_terraform.py

# Analyze results
python token_benchmarks/token_efficiency_analysis.py
```

## 📊 Validated Claims

| Claim | Status | Result |
|-------|--------|---------|
| Quality: 95-100% vs 40-60% | ⚠️ Partial | 90% achieved (close to target) |
| Error Detection: 4-5× improvement | 🔄 Needs baseline | 100% detection rate |
| Performance: ~0.4s, <100MB | ✅ Validated | 0.291s, 0.4MB |
| Token Efficiency | ✅ Exceeded | 83% reduction, 99% context savings |

## 🛠 Requirements

- Python 3.11+
- uv (package manager)
- terraform-ls
- Serena dependencies

## 📝 License

This benchmark suite is part of the Serena project and follows the same license terms.

## 🤝 Contributing

To add new benchmarks or improve existing tests:
1. Follow the existing structure in `ab_tests/` or `token_benchmarks/`
2. Add test data to `test_data/` if needed
3. Document findings in `docs/`
4. Update this README with new results
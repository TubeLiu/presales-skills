# End-to-End Test Guide

[中文](./README.md) | **English**

## Overview

This test framework verifies the full-pipeline quality of the tender-workflow system from `taa` (tender analysis) to `taw` (chapter writing).

## Test architecture

### Test flow (10 steps)

```
Step 0: Environment setup
Step 1: Locate taa output files
Step 2: Analysis report quality verification (enhanced)
Step 3: Bid outline quality verification
Step 4: taw chapter generation
Step 5: Chapter content quality verification (enhanced)
Step 6: Cross-chapter consistency verification (new)
Step 7: Outline-match verification (new)
Step 8: trv review integration (optional)
Step 9: Comprehensive quality scoring (new)
Step 10: Generate final test report
```

### Validators

- TAAValidator: validates taa analysis report and outline quality
- TAWValidator: validates taw chapter content quality
- ConsistencyValidator: validates consistency (new)
- ImageQualityValidator: validates image quality (new)
- ContentProfessionalismValidator: validates content professionalism (new)
- QualityChecker: quality-check engine

## Usage

### Prerequisites

1. Install dependencies:
```bash
pip install pytest python-docx
```

2. Generate taa output (required):
```bash
/taa /home/ubuntu/testfile2.docx --vendor "灵雀云"
```

### Run tests

```bash
# Full end-to-end test
pytest tests/e2e/test_e2e_workflow.py -v -s

# Parameter tests
pytest tests/e2e/test_parameters.py -v -s
```

### View test report

```bash
cat tests/e2e/reports/e2e_test_report_*.md
```

## Quality metrics

- Analysis report quality: ≥85%
- Bid outline quality: ≥90%
- Chapter content quality: ≥80%
- Consistency quality: ≥90%

See the quality-metrics dashboard in the test report for details.

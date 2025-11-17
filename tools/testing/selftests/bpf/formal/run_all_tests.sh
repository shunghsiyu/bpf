#!/bin/bash
echo "=== Running comprehensive wrange32 test suite ==="
echo ""

tests=(
    "wrange_add.py:Addition"
    "wrange_sub.py:Subtraction"
    "wrange_mul.py:Multiplication"
    "wrange_intersect.py:Intersection"
    "wrange_union.py:Union"
)

passed=0
failed=0

for test_info in "${tests[@]}"; do
    IFS=':' read -r test_file test_name <<< "$test_info"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Testing: $test_name ($test_file)"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    if python3 "$test_file" 2>&1 | tail -1 | grep -q "passed\|proved"; then
        echo "✓ PASSED"
        ((passed++))
    else
        echo "✗ FAILED"
        ((failed++))
    fi
    echo ""
done

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Test Summary"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Passed: $passed/${#tests[@]}"
echo "Failed: $failed/${#tests[@]}"

if [ $failed -eq 0 ]; then
    echo ""
    echo "✓ ALL TESTS PASSED - Phase 1 validation complete!"
    exit 0
else
    echo ""
    echo "✗ Some tests failed"
    exit 1
fi

#!/usr/bin/env python3
"""
Demo script that will initially fail, for testing the auto-fix functionality
"""

def calculate_sum(numbers):
    # This has a bug - will fail on first run
    total = 0
    for num in numbers:
        total += num
    return total

def main():
    # This will cause an error initially
    numbers = ["1", "2", "3", "4", "5"]  # Bug: strings instead of integers
    result = calculate_sum(numbers)
    print(f"Sum: {result}")

if __name__ == "__main__":
    main()
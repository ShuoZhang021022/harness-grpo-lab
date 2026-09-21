"""Exact arithmetic where indicated; no eval, subprocess, network, or LLM calls."""

import cmath
import itertools
import math
from fractions import Fraction

from .registry import register


@register("math", {"numbers": [18, 24]}, 6)
def integer_gcd(numbers):
    """Return the nonnegative greatest common divisor of a nonempty integer list."""
    if not numbers:
        raise ValueError("numbers must be nonempty")
    return math.gcd(*numbers)


@register("math", {"numbers": [6, 8]}, 24)
def integer_lcm(numbers):
    """Return the nonnegative least common multiple of a nonempty integer list."""
    if not numbers:
        raise ValueError("numbers must be nonempty")
    return math.lcm(*numbers)


@register("math", {"a": 30, "b": 18}, {"gcd": 6, "x": -1, "y": 2})
def extended_gcd(a, b):
    """Return integers gcd,x,y satisfying a*x+b*y=gcd>=0 (Bezout coefficients)."""
    old_r, r, old_s, s, old_t, t = a, b, 1, 0, 0, 1
    while r:
        q = old_r // r
        old_r, r = r, old_r - q * r
        old_s, s = s, old_s - q * s
        old_t, t = t, old_t - q * t
    sign = -1 if old_r < 0 else 1
    return {"gcd": sign * old_r, "x": sign * old_s, "y": sign * old_t}


@register("math", {"base": 3, "exponent": 5, "modulus": 7}, 5)
def modular_power(base, exponent, modulus):
    """Compute base**exponent modulo a positive modulus; exponent must be nonnegative."""
    if exponent < 0 or modulus <= 0:
        raise ValueError("Require exponent>=0 and modulus>0")
    return pow(base, exponent, modulus)


@register("math", {"a": 3, "modulus": 7}, 5)
def modular_inverse(a, modulus):
    """Return modular multiplicative inverse; fail if modulus<=1 or inverse does not exist."""
    if modulus <= 1:
        raise ValueError("modulus must exceed 1")
    return pow(a, -1, modulus)


@register("math", {"n": 60}, [[2, 2], [3, 1], [5, 1]])
def prime_factorization(n):
    """Factor a positive integer into [prime, exponent] pairs by exact trial division."""
    if n < 1:
        raise ValueError("n must be positive")
    factors, p = [], 2
    while p * p <= n:
        count = 0
        while n % p == 0:
            n //= p
            count += 1
        if count:
            factors.append([p, count])
        p = 3 if p == 2 else p + 2
    if n > 1:
        factors.append([n, 1])
    return factors


@register("math", {"n": 12}, [1, 2, 3, 4, 6, 12])
def positive_divisors(n):
    """Return all positive divisors of a positive integer in ascending order."""
    if n < 1:
        raise ValueError("n must be positive")
    result = []
    for d in range(1, math.isqrt(n) + 1):
        if n % d == 0:
            result.append(d)
            if d * d != n:
                result.append(n // d)
    return sorted(result)


@register("math", {"n": 97}, True)
def is_prime(n):
    """Test integer primality exactly using trial division; integers below 2 return false."""
    if n < 2:
        return False
    if n % 2 == 0:
        return n == 2
    return all(n % d for d in range(3, math.isqrt(n) + 1, 2))


@register("math", {"n": 5, "k": 2}, 10)
def binomial_coefficient(n, k):
    """Compute exact n-choose-k for nonnegative integers, returning zero when k>n."""
    return math.comb(n, k)


@register("math", {"counts": [2, 1, 1]}, 12)
def multinomial_coefficient(counts):
    """Count arrangements with the supplied nonnegative category counts."""
    if any(c < 0 for c in counts):
        raise ValueError("counts must be nonnegative")
    return math.factorial(sum(counts)) // math.prod(math.factorial(c) for c in counts)


@register("math", {"a": "1/3", "b": "1/6", "operation": "add"}, "1/2")
def rational_arithmetic(a, b, operation):
    """Apply add/subtract/multiply/divide to exact fraction strings; return a reduced fraction string."""
    a, b = Fraction(a), Fraction(b)
    if operation == "add":
        return str(a + b)
    if operation == "subtract":
        return str(a - b)
    if operation == "multiply":
        return str(a * b)
    if operation == "divide":
        return str(a / b)
    raise ValueError("Unknown operation")


@register("math", {"coefficients": [2, 3, 4], "x": 2}, "18")
def polynomial_evaluate(coefficients, x):
    """Evaluate exact rational coefficients in descending power order; return a fraction string."""
    value, x = Fraction(0), Fraction(x)
    for coefficient in coefficients:
        value = value * x + Fraction(coefficient)
    return str(value)


@register("math", {"matrix": [[2, 1], [1, -1]], "rhs": [5, 1]}, ["2", "1"])
def solve_linear_system(matrix, rhs):
    """Solve a square nonsingular system exactly over rational numbers; reject singular systems."""
    n = len(matrix)
    if not n or len(rhs) != n or any(len(row) != n for row in matrix):
        raise ValueError("Require a nonempty square matrix and matching rhs")
    a = [[Fraction(v) for v in row] + [Fraction(rhs[i])] for i, row in enumerate(matrix)]
    for col in range(n):
        pivot = next((i for i in range(col, n) if a[i][col]), None)
        if pivot is None:
            raise ValueError("System does not have a unique solution")
        a[col], a[pivot] = a[pivot], a[col]
        divisor = a[col][col]
        a[col] = [v / divisor for v in a[col]]
        for row in range(n):
            if row != col:
                scale = a[row][col]
                a[row] = [x - scale * y for x, y in zip(a[row], a[col])]
    return [str(row[-1]) for row in a]


@register("math", {"a": 1, "b": -3, "c": 2}, [[2.0, 0.0], [1.0, 0.0]])
def quadratic_roots(a, b, c):
    """Return two approximate complex roots as [real,imaginary] pairs; requires nonzero a."""
    if a == 0:
        raise ValueError("a must be nonzero")
    root = cmath.sqrt(b * b - 4 * a * c)
    return [[z.real, z.imag] for z in ((-b + root) / (2 * a), (-b - root) / (2 * a))]


@register("math", {"remainders": [2, 3], "moduli": [3, 5]}, {"remainder": 8, "modulus": 15})
def chinese_remainder(remainders, moduli):
    """Solve simultaneous congruences with pairwise coprime moduli>1; return least nonnegative solution."""
    if len(remainders) != len(moduli) or not moduli or any(m <= 1 for m in moduli):
        raise ValueError("Require equal nonempty lists and moduli>1")
    if any(math.gcd(a, b) != 1 for a, b in itertools.combinations(moduli, 2)):
        raise ValueError("Moduli must be pairwise coprime")
    product = math.prod(moduli)
    value = sum(r * (product // m) * pow(product // m, -1, m) for r, m in zip(remainders, moduli))
    return {"remainder": value % product, "modulus": product}


@register("math", {"items": [1, 2, 3], "k": 2}, [[1, 2], [1, 3], [2, 3]])
def enumerate_combinations(items, k):
    """Enumerate positional k-combinations in input order; no deduplication or silent truncation."""
    return [list(x) for x in itertools.combinations(items, k)]


@register("math", {"items": [1, 2], "k": 2}, [[1, 2], [2, 1]])
def enumerate_permutations(items, k):
    """Enumerate positional length-k permutations; duplicate input values can produce duplicate outputs."""
    return [list(x) for x in itertools.permutations(items, k)]


@register("math", {"n": 17}, {"floor_root": 4, "is_square": False})
def integer_square_root(n):
    """Compute exact floor square root and square status for a nonnegative integer."""
    root = math.isqrt(n)
    return {"floor_root": root, "is_square": root * root == n}

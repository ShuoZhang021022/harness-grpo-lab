def solve(x):
    v = x
    v = v % 37
    v = 2 * v + 1
    v = abs(v)
    v = v - 11
    return v

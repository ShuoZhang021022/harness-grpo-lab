def solve(x):
    v = x
    v = -v
    v = v % 37
    v = 2 * v + 1
    v = v - 11
    return v

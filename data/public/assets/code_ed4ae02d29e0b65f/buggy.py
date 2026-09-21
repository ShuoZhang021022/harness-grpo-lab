def solve(x):
    v = x
    v = 2 * v + 1
    v = v % 37
    v = (v * v) % 101
    v = v - 11
    return v

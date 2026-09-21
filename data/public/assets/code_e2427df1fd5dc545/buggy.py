def solve(x):
    v = x
    v = v - 11
    v = (v * v) % 101
    v = 2 * v + 1
    v = -v
    return v

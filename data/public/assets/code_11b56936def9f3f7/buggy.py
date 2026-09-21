def solve(x):
    v = x
    v = 2 * v + 1
    v = (v * v) % 101
    v = -v
    v = (v * v) % 101
    return v

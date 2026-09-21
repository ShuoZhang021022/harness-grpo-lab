def solve(x):
    v = x
    v = (v * v) % 101
    v = 2 * v + 1
    v = 2 * v + 1
    v = v + 7
    return v

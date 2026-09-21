def solve(x):
    v = x
    v = (v * v) % 101
    v = (v * v) % 101
    v = v + 7
    v = 2 * v + 1
    return v

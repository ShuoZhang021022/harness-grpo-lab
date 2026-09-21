def solve(x):
    v = x
    v = (v * v) % 101
    v = v % 37
    v = 2 * v + 1
    v = 2 * v + 1
    return v

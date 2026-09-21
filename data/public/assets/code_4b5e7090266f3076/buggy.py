def solve(x):
    v = x
    v = (v * v) % 101
    v = v + 7
    v = 2 * v + 1
    v = v % 37
    return v

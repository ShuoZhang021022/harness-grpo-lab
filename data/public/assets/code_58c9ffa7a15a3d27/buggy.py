def solve(x):
    v = x
    v = v % 37
    v = v * 3
    v = 2 * v + 1
    v = (v * v) % 101
    return v

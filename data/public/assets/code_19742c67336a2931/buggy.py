def solve(x):
    v = x
    v = (v * v) % 101
    v = abs(v)
    v = 2 * v + 1
    v = v * 3
    return v

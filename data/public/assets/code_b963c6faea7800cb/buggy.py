def solve(x):
    v = x
    v = abs(v)
    v = v + 7
    v = 2 * v + 1
    v = (v * v) % 101
    return v

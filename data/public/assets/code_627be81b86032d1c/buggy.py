def solve(x):
    v = x
    v = 2 * v + 1
    v = (v * v) % 101
    v = abs(v)
    v = v + 7
    return v

def solve(x):
    v = x
    v = v + 7
    v = (v * v) % 101
    v = abs(v)
    v = -v
    return v

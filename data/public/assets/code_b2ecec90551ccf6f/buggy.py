def solve(x):
    v = x
    v = v + 7
    v = abs(v)
    v = (v * v) % 101
    v = -v
    return v

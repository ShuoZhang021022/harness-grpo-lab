def solve(x):
    v = x
    v = (v * v) % 101
    v = abs(v)
    v = v + 7
    v = abs(v)
    return v

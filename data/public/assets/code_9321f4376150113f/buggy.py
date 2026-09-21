def solve(x):
    v = x
    v = abs(v)
    v = (v * v) % 101
    v = v + 7
    v = v * 3
    return v

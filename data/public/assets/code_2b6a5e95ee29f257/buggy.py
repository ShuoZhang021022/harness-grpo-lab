def solve(x):
    v = x
    v = abs(v)
    v = v + 7
    v = v * 3
    v = (v * v) % 101
    return v

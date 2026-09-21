def solve(x):
    v = x
    v = v % 37
    v = abs(v)
    v = abs(v)
    v = (v * v) % 101
    return v

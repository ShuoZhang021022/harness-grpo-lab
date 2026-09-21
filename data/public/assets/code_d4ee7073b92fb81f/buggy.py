def solve(x):
    v = x
    v = abs(v)
    v = 2 * v + 1
    v = -v
    v = v % 37
    return v

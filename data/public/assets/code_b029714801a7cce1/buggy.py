def solve(x):
    v = x
    v = v % 37
    v = abs(v)
    v = 2 * v + 1
    v = -v
    return v

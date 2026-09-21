def solve(x):
    v = x
    v = 2 * v + 1
    v = abs(v)
    v = v // 2
    v = v % 37
    return v

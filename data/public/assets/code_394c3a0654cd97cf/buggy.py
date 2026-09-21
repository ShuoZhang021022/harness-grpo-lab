def solve(x):
    v = x
    v = v % 37
    v = (v + 5) // 3
    v = abs(v)
    v = -v
    return v

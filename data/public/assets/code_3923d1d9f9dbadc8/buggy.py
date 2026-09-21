def solve(x):
    v = x
    v = v % 37
    v = -v
    v = (v + 5) // 3
    v = abs(v)
    return v

def solve(x):
    v = x
    v = (v + 5) // 3
    v = -v
    v = abs(v)
    v = v % 37
    return v

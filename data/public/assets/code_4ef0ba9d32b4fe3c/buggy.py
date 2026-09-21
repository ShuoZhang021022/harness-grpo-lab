def solve(x):
    v = x
    v = v - 11
    v = v % 37
    v = abs(v)
    v = (v + 5) // 3
    return v
